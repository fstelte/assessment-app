"""Scaffold application package.

Provides the Flask application factory and shared setup routines that layer
bia_app and csa_app domains while remaining extensible for future modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
from flask import Flask

from .config import Settings
from .core.registry import AppRegistry
from .core.security import init_session_security
from .core.security_headers import init_security_headers
from .templates.navigation import build_navigation
from .extensions import db, login_manager, migrate


def create_app(settings: Settings | None = None) -> Flask:
    """Create an instance of the scaffold Flask application."""

    app = Flask(__name__.split(".")[0])
    app_settings = settings or Settings.from_env()
    app.config.update(app_settings.flask_config())
    _ensure_instance_folder(app)
    _ensure_sqlite_uri(app)

    _init_extensions(app)
    init_session_security(app)
    init_security_headers(app)
    _register_apps(app, app_settings)
    _register_cli_commands(app)
    app.context_processor(lambda: {"nav_entries": lambda: build_navigation(app)})

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

        admin_role = Role.query.filter_by(name="admin").first()
        if admin_role is None:
            admin_role = Role(name="admin", description="Platform administrator")
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
