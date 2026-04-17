"""SCIM 2.0 provisioning module."""

from __future__ import annotations

from .routes import bp


def register(app):
    app.register_blueprint(bp)
    app.logger.info("SCIM module registered.")
