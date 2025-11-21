"""Administrative views for managing users across domains."""

from __future__ import annotations

from .routes import bp


def register(app):
    app.register_blueprint(bp)
    app.logger.info("Admin module registered.")


NAVIGATION = [
    # Admin navigation removed from global menu; direct links live in admin views.
]
