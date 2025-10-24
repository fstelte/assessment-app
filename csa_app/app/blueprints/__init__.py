"""Blueprint registration helpers."""

from __future__ import annotations

from flask import Flask

from .admin import bp as admin_bp
from .assessments import bp as assessments_bp
from .auth import bp as auth_bp
from .public import bp as public_bp


def register_blueprints(app: Flask) -> None:
    """Attach all blueprints to the Flask app."""
    for blueprint in (public_bp, auth_bp, admin_bp, assessments_bp):
        app.register_blueprint(blueprint)
