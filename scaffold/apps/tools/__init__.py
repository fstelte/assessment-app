"""Security and assessment tools module."""

from __future__ import annotations

from .routes import bp

__all__ = ["bp", "register"]


def register(app):
    """Register the tools blueprint with the application."""

    app.register_blueprint(bp)
    app.logger.info("Tools module registered.")
