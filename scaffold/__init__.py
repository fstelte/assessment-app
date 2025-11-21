"""Scaffold application package.

Provides the Flask application factory and shared setup routines that layer
bia_app and csa_app domains while remaining extensible for future modules.
"""

from __future__ import annotations

import os
import atexit
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any
import threading
from logging.handlers import RotatingFileHandler
from datetime import datetime, UTC

import tomllib

import click
from flask import Flask, g, render_template, request, send_file, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.routing import BuildError
from flask_login import current_user
from sqlalchemy.exc import OperationalError, ProgrammingError
from werkzeug.exceptions import Forbidden
from jinja2 import TemplateError

from .config import Settings
from .core.audit import init_auto_audit
from .core.registry import AppRegistry
from .core.security import init_session_security
from .core.security_headers import init_security_headers
from .templates.navigation import build_navigation
from .core.i18n import (
    TranslationManager,
    get_locale,
    session_storage_key,
    set_locale,
)
from .extensions import db, login_manager, migrate
from .apps.identity.models import ROLE_ADMIN, ensure_default_roles


def create_app(settings: Settings | None = None) -> Flask:
    """Create an instance of the scaffold Flask application."""

    app = Flask(__name__.split(".")[0])
    app_settings = settings or Settings.from_env()
    app.config.update(app_settings.flask_config())
    if app_settings.proxy_fix_enabled:
        app.wsgi_app = ProxyFix(  # type: ignore[assignment]
            app.wsgi_app,
            x_for=app_settings.proxy_fix_x_for,
            x_proto=app_settings.proxy_fix_x_proto,
            x_host=app_settings.proxy_fix_x_host,
            x_port=app_settings.proxy_fix_x_port,
            x_prefix=app_settings.proxy_fix_x_prefix,
        )
    _ensure_instance_folder(app)
    _ensure_sqlite_uri(app)

    _init_extensions(app)
    from . import models as _models  # noqa: F401 - ensure models are imported for metadata registration
    _configure_logging(app)
    init_session_security(app)
    init_security_headers(app)
    _register_apps(app, app_settings)
    _register_cli_commands(app)
    translations_path = Path(app.root_path) / "translations"
    i18n_manager = TranslationManager(translations_path)
    app.extensions["i18n"] = i18n_manager
    app.jinja_env.globals.setdefault("_", lambda key, **kwargs: i18n_manager.translate(key, locale=get_locale(), **kwargs))

    @app.before_request
    def _determine_locale() -> None:
        requested = (request.args.get("lang") or "").strip()
        stored = session.get(session_storage_key())
        user_locale = None
        if current_user.is_authenticated:
            user_locale = getattr(current_user, "locale_preference", None)

        available_locales = i18n_manager.available_locales()
        if not available_locales:
            available_locales = [i18n_manager.default_locale]
        available_set = set(available_locales)

        candidates = [requested, user_locale, stored if isinstance(stored, str) else None, i18n_manager.default_locale]
        target_locale = next((loc for loc in candidates if loc and loc in available_set), i18n_manager.default_locale)

        set_locale(target_locale)
        session[session_storage_key()] = get_locale()

    @app.context_processor
    def inject_template_helpers() -> dict[str, Any]:
        metadata = dict(_load_app_metadata())
        try:
            metadata["changelog"] = url_for("pages.changelog")
        except (RuntimeError, BuildError):
            # Fallback in scenarios where the route is not available yet (e.g. migrations)
            metadata.setdefault("changelog", "#")
        return {
            "nav_entries": lambda: build_navigation(app),
            "app_meta": metadata,
            "current_locale": get_locale(),
            "available_locales": i18n_manager.available_locales(),
            "csp_nonce": getattr(g, "csp_nonce", ""),
        }

    def _contact_details() -> dict[str, str]:
        email = os.getenv("MAINTENANCE_CONTACT_EMAIL", "support@example.com")
        label = os.getenv("MAINTENANCE_CONTACT_LABEL", email)
        link = os.getenv("MAINTENANCE_CONTACT_LINK") or f"mailto:{email}"
        return {
            "contact_email": email,
            "contact_label": label,
            "contact_link": link,
        }

    @app.errorhandler(OperationalError)
    def maintenance_mode(exc: OperationalError):  # type: ignore[misc]
        app.logger.warning("database unavailable; serving maintenance page", exc_info=app.debug)
        shared_path = Path(os.getenv("MAINTENANCE_SHARED_OUTPUT", "/maintenance/maintenance.html"))
        if shared_path.exists():
            response = send_file(shared_path)
            response.status_code = 503
            response.headers.setdefault("Cache-Control", "no-store")
            return response
        response = app.send_static_file("maintenance.html")
        response.status_code = 503
        return response

    @app.errorhandler(Forbidden)
    def forbidden(exc: Forbidden):  # type: ignore[misc]
        app.logger.info("forbidden access attempt", extra={"path": request.path})
        response = app.make_response(
            render_template("errors/forbidden.html", **_contact_details())
        )
        response.status_code = 403
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.errorhandler(TemplateError)
    def template_failure(exc: TemplateError):  # type: ignore[misc]
        if app.debug:
            raise exc
        app.logger.exception("template rendering failed", exc_info=True)
        response = app.make_response(render_template("errors/server_error.html", **_contact_details()))
        response.status_code = 500
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    with app.app_context():
        try:
            ensure_default_roles()
        except (OperationalError, ProgrammingError):  # pragma: no cover - happens before migrations
            app.logger.debug("Default role provisioning skipped; tables not ready yet.", exc_info=True)
        init_auto_audit(app)

    _start_export_cleanup_worker(app)
    _start_audit_cleanup_worker(app)

    return app


def _init_extensions(app: Flask) -> None:
    """Initialise shared Flask extensions."""

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)


def _register_apps(app: Flask, settings: Settings) -> None:
    """Discover and register blueprints from packaged modules."""

    registry = AppRegistry(app)
    app.extensions["scaffold_registry"] = registry
    registry.discover(settings.app_modules)
    registry.register_all()


def _ensure_instance_folder(app: Flask) -> None:
    """Guarantee that the Flask instance directory exists."""

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)


def _ensure_sqlite_uri(app: Flask) -> None:
    """Normalise SQLite URLs to absolute paths and ensure directories exist."""

    raw_uri = app.config.get("SQLALCHEMY_DATABASE_URI")
    if not isinstance(raw_uri, str) or not raw_uri.startswith("sqlite:///"):
        return

    relative_path = raw_uri.replace("sqlite:///", "", 1)
    sqlite_path = Path(relative_path)
    if not sqlite_path.is_absolute():
        project_root = Path(app.root_path).parent
        sqlite_path = (project_root / sqlite_path).resolve()

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite_path.as_posix()}"


def _register_cli_commands(app: Flask) -> None:
    """Expose management commands on the Flask CLI."""

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--first-name", prompt="First name", default="", show_default=False)
    @click.option("--last-name", prompt="Last name", default="", show_default=False)
    def create_admin(email: str, password: str, first_name: str, last_name: str) -> None:
        """Create or update the primary administrator account."""

        from .extensions import db
        from .apps.identity.models import Role, User, UserStatus

        admin_role = Role.query.filter_by(name=ROLE_ADMIN).first()
        if admin_role is None:
            admin_role = Role(name=ROLE_ADMIN, description="Platform administrator")
            db.session.add(admin_role)
            db.session.commit()

        user = User.find_by_email(email)
        if user is None:
            user = User(
                email=email,
                first_name=first_name or None,
                last_name=last_name or None,
                status=UserStatus.ACTIVE,
            )
            user.set_password(password)
            db.session.add(user)
        else:
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name
            if user.status != UserStatus.ACTIVE:
                user.status = UserStatus.ACTIVE
            user.set_password(password)

        if admin_role not in user.roles:
            user.roles.append(admin_role)

        db.session.commit()
        click.echo("Administrator account created or updated.")

    @app.cli.command("audit-retention")
    @click.option("--retention-days", type=int, default=None, help="Override retention window in days.")
    @click.option(
        "--log-path",
        type=click.Path(path_type=str),
        default=None,
        help="Override audit log path.",
    )
    def audit_retention_command(retention_days: int | None, log_path: str | None) -> None:
        """Enforce audit log retention for database records and log files."""

        from .core.audit import enforce_audit_retention

        outcome = enforce_audit_retention(retention_days=retention_days, log_path=log_path)
        click.echo(
            f"Removed {outcome.get('db_deleted', 0)} audit log rows and {outcome.get('files_deleted', 0)} log files."
        )


@lru_cache(maxsize=1)
def _load_app_metadata() -> dict[str, str]:
    """Return cached project metadata for templates."""

    project_root = Path(__file__).resolve().parent.parent
    pyproject_path = project_root / "pyproject.toml"
    version = "0.0.0"
    author = "Unknown author"
    repo_url = "https://github.com/fstelte/assessment-app"
    changelog_url = f"{repo_url}/blob/main/docs/history.md"

    if pyproject_path.exists():
        try:
            data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
            poetry = data.get("tool", {}).get("poetry", {})
            version = poetry.get("version", version)
            authors = poetry.get("authors")
            if isinstance(authors, list) and authors:
                author = authors[0]
        except (tomllib.TOMLDecodeError, OSError):  # pragma: no cover - defensive
            pass

    return {
        "version": version,
        "author": author,
        "repository": repo_url,
        "changelog": changelog_url,
    }


def _start_export_cleanup_worker(app: Flask) -> None:
    if not app.config.get("EXPORT_CLEANUP_ENABLED"):
        return

    try:
        from .apps.bia.utils import cleanup_export_folder
    except Exception:  # pragma: no cover - BIA module unavailable
        app.logger.warning(
            "EXPORT_CLEANUP_ENABLED is true but the BIA module could not be loaded; skipping export cleanup worker."
        )
        return

    storage = app.extensions.setdefault("export_cleanup", {})
    if storage.get("thread"):
        return

    interval_minutes = max(1, int(app.config.get("EXPORT_CLEANUP_INTERVAL_MINUTES", 60)))
    max_age_days = max(1, int(app.config.get("EXPORT_CLEANUP_MAX_AGE_DAYS", 7)))

    if app.logger.getEffectiveLevel() > logging.INFO:
        app.logger.setLevel(logging.INFO)

    stop_event = threading.Event()
    storage["stop_event"] = stop_event

    def _run_cycle() -> None:
        removed, failed = cleanup_export_folder(max_age_days)
        if removed or failed:
            app.logger.info("Export cleanup removed %s artefacts (failed: %s)", removed, failed)
        else:
            app.logger.info("Export cleanup completed; no stale artefacts detected.")

    def _worker() -> None:
        with app.app_context():
            try:
                _run_cycle()
            except Exception:  # pragma: no cover - defensive logging
                app.logger.exception("Initial export cleanup run failed")

        interval_seconds = max(60, int(interval_minutes * 60))
        while not stop_event.wait(interval_seconds):
            with app.app_context():
                try:
                    _run_cycle()
                except Exception:  # pragma: no cover - defensive logging
                    app.logger.exception("Scheduled export cleanup run failed")

    worker = threading.Thread(target=_worker, name="export-cleanup", daemon=True)
    worker.start()
    storage["thread"] = worker

    atexit.register(stop_event.set)


def _configure_logging(app: Flask) -> None:
    if app.extensions.get("audit_log_handler"):
        return

    config = app.config
    if not config.get("AUDIT_LOG_ENABLED", True):
        return

    log_path = config.get("AUDIT_LOG_PATH")
    if not isinstance(log_path, str) or not log_path.strip():
        app.logger.warning("Audit log path is not configured; skipping rotating handler setup.")
        return

    try:
        target = Path(log_path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
    except Exception:  # pragma: no cover - guard against filesystem errors
        app.logger.exception("Failed to prepare audit log directory; audit log handler not configured.")
        return

    retention_days = int(config.get("AUDIT_LOG_RETENTION_DAYS", 0))
    backup_count = max(1, retention_days) if retention_days > 0 else 30

    formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s %(name)s %(message)s")
    formatter.converter = lambda *args: datetime.now(UTC).timetuple()  # type: ignore[assignment]

    handler = RotatingFileHandler(
        target,
        maxBytes=5 * 1024 * 1024,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)

    audit_logger = logging.getLogger("scaffold.audit")
    audit_logger.setLevel(logging.INFO)
    audit_logger.addHandler(handler)
    audit_logger.propagate = False

    app.extensions["audit_log_handler"] = handler

def _start_audit_cleanup_worker(app: Flask) -> None:
    if app.testing:
        return
    if not app.config.get("AUDIT_LOG_ENABLED"):
        return

    retention_days = int(app.config.get("AUDIT_LOG_RETENTION_DAYS", 0))
    if retention_days <= 0:
        return

    interval_hours = max(1, int(app.config.get("AUDIT_LOG_PRUNE_INTERVAL_HOURS", 24)))
    storage = app.extensions.setdefault("audit_logging", {})
    if storage.get("cleanup_thread"):
        return

    stop_event = threading.Event()
    storage["stop_event"] = stop_event

    def _run_cycle() -> None:
        from .core.audit import enforce_audit_retention

        outcome = enforce_audit_retention(retention_days=retention_days)
        removed_rows = outcome.get("db_deleted", 0)
        removed_files = outcome.get("files_deleted", 0)
        if removed_rows or removed_files:
            app.logger.info(
                "Audit retention removed %s database rows and %s log files",
                removed_rows,
                removed_files,
            )

    def _worker() -> None:
        with app.app_context():
            try:
                _run_cycle()
            except Exception:  # pragma: no cover - defensive logging
                app.logger.exception("Initial audit log pruning failed")

        interval_seconds = max(3600, int(interval_hours * 3600))
        while not stop_event.wait(interval_seconds):
            with app.app_context():
                try:
                    _run_cycle()
                except Exception:  # pragma: no cover - defensive logging
                    app.logger.exception("Scheduled audit log pruning failed")

    worker = threading.Thread(target=_worker, name="audit-prune", daemon=True)
    worker.start()
    storage["cleanup_thread"] = worker

    atexit.register(stop_event.set)
