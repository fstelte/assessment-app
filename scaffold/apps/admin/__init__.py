"""Administrative views for managing users across domains."""

from __future__ import annotations

from .routes import bp
from ...templates.navigation import NavEntry


def register(app):
    app.register_blueprint(bp)
    app.logger.info("Admin module registered.")


NAVIGATION = [
    NavEntry(endpoint="admin.list_users", label="Admin", order=80),
]
