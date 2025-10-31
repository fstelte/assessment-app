"""Application factory and project bootstrap."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from importlib import metadata
import tomllib

import click
from dotenv import load_dotenv
from flask import Flask, request, session

from . import models  # noqa: F401  # ensure models register with SQLAlchemy metadata
from .blueprints import register_blueprints
from .config import CONFIG_BY_NAME
from .extensions import csrf, db, login_manager, migrate, talisman
from .i18n import TranslationManager, get_locale, session_storage_key, set_locale

_PROJECT_VERSION: str | None = None
_PROJECT_LICENSE: tuple[str, str] | None = None
_PROJECT_METADATA: dict[str, str] | None = None

_LICENSE_URLS = {
    "MIT": "https://opensource.org/license/mit/",
}

# Zorg dat de gedeelde root .env geladen wordt zodat alle apps dezelfde waarden gebruiken
ROOT_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
if ROOT_ENV_PATH.exists():
    load_dotenv(ROOT_ENV_PATH, override=False)


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    config_key = _resolve_config_key(config_name)
    config_obj = CONFIG_BY_NAME.get(config_key, CONFIG_BY_NAME["development"])
    app.config.from_object(config_obj)

    _ensure_instance_folder(app)
    _register_extensions(app)
    register_blueprints(app)
    _register_cli_commands(app)
    _register_template_globals(app)
    _init_i18n(app)

    return app


def _resolve_config_key(explicit_key: str | None) -> str:
    """Determine which configuration the app should load."""
    env_key = explicit_key or os.getenv("APP_CONFIG") or os.getenv("FLASK_ENV")
    return (env_key or "development").lower()


def _ensure_instance_folder(app: Flask) -> None:
    """Create the instance folder when the project is bootstrapped."""
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)


def _register_extensions(app: Flask) -> None:
    """Initialise Flask extensions with the application context."""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    talisman.init_app(
        app,
        content_security_policy=app.config.get("CONTENT_SECURITY_POLICY"),
        force_https=app.config.get("TALISMAN_FORCE_HTTPS", False),
    )
    login_manager.login_view = "auth.login"


def _register_cli_commands(app: Flask) -> None:
    """Attach placeholder CLI commands as extension points."""

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--first-name", prompt="Voornaam", default="", show_default=False)
    @click.option("--last-name", prompt="Achternaam", default="", show_default=False)
    def create_admin(email: str, password: str, first_name: str, last_name: str) -> None:
        """Create or update the primary administrator account."""
        from .extensions import db
        from .models import Role, User, UserStatus

        admin_role = Role.query.filter_by(name="admin").first()
        if admin_role is None:
            admin_role = Role(name="admin", description="Applicatiebeheerder")
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
            user.status = UserStatus.ACTIVE
            user.set_password(password)

        if admin_role not in user.roles:
            user.roles.append(admin_role)

        db.session.commit()
        click.echo("Administrator account is aangemaakt of bijgewerkt.")

    @app.cli.command("assign-role")
    @click.argument("email")
    @click.argument("role")
    def assign_role(email: str, role: str) -> None:
        """Ken een rol toe aan een gebruiker (wordt aangemaakt indien nodig)."""
        from .extensions import db
        from .models import Role, User

        user = User.find_by_email(email)
        if user is None:
            click.echo(f"Geen gebruiker gevonden met e-mail {email}.")
            return

        role_name = role.strip().lower()
        role_obj = Role.query.filter_by(name=role_name).first()
        if role_obj is None:
            description = "Beheerder" if role_name == "admin" else "Assessment manager"
            role_obj = Role(name=role_name, description=description)
            db.session.add(role_obj)
            db.session.commit()
            click.echo(f"Rol '{role_name}' is aangemaakt.")

        if role_obj in user.roles:
            click.echo(f"Gebruiker {email} heeft de rol '{role_name}' al.")
            return

        user.roles.append(role_obj)
        db.session.commit()
        click.echo(f"Rol '{role_name}' is toegewezen aan {email}.")


def _register_template_globals(app: Flask) -> None:
    """Expose commonly used values to all templates."""

    @app.context_processor
    def inject_app_version() -> dict[str, object]:
        license_name, license_url = _resolve_project_license()
        return {
            "app_version": _resolve_project_version(),
            "current_year": datetime.now().year,
            "app_license": license_name,
            "app_license_url": license_url,
        }


def _init_i18n(app: Flask) -> None:
    """Initialise JSON-backed translations and locale detection."""

    translations_path = Path(app.root_path) / "translations"
    manager = TranslationManager(translations_path)
    app.extensions["i18n"] = manager

    app.jinja_env.globals.setdefault(
        "_",
        lambda key, **kwargs: manager.translate(key, locale=get_locale(), **kwargs),
    )

    @app.before_request
    def detect_locale() -> None:
        requested = (request.args.get("lang") or "").strip()
        stored = session.get(session_storage_key())
        available = manager.available_locales() or [manager.default_locale]
        available_set = set(available)

        candidates = [requested, stored, manager.default_locale]
        target = next((loc for loc in candidates if loc and loc in available_set), manager.default_locale)
        set_locale(target)
        session[session_storage_key()] = target

    @app.context_processor
    def inject_locale_helpers() -> dict[str, object]:
        return {
            "current_locale": get_locale() or manager.default_locale,
            "available_locales": manager.available_locales(),
        }


def _resolve_project_version() -> str:
    """Return the project version from installed metadata or pyproject."""

    global _PROJECT_VERSION
    if _PROJECT_VERSION:
        return _PROJECT_VERSION

    package_name = "control-self-assessment"
    try:
        _PROJECT_VERSION = metadata.version(package_name)
        return _PROJECT_VERSION
    except metadata.PackageNotFoundError:
        metadata_dict = _load_project_metadata()
        version = metadata_dict.get("version")
        _PROJECT_VERSION = version or "0.0.0"
        return _PROJECT_VERSION


def _resolve_project_license() -> tuple[str, str]:
    """Return the project license name and documentation link."""

    global _PROJECT_LICENSE
    if _PROJECT_LICENSE:
        return _PROJECT_LICENSE

    metadata_dict = _load_project_metadata()
    license_name = metadata_dict.get("license") or "Onbekend"
    license_key = license_name.strip().upper()
    license_url = _LICENSE_URLS.get(license_key, "")
    _PROJECT_LICENSE = (license_name, license_url)
    return _PROJECT_LICENSE


def _load_project_metadata() -> dict[str, str]:
    """Parse pyproject.toml to pull project metadata like version and license."""

    global _PROJECT_METADATA
    if _PROJECT_METADATA is not None:
        return _PROJECT_METADATA

    metadata_dict: dict[str, str] = {}
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if pyproject_path.exists():
        try:
            data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
            poetry_section = data.get("tool", {}).get("poetry", {})
            if isinstance(poetry_section, dict):
                version = poetry_section.get("version")
                license_name = poetry_section.get("license")
                if isinstance(version, str):
                    metadata_dict["version"] = version
                if isinstance(license_name, str):
                    metadata_dict["license"] = license_name
        except (OSError, tomllib.TOMLDecodeError):
            pass

    _PROJECT_METADATA = metadata_dict
    return _PROJECT_METADATA
