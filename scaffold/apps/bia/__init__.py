"""BIA domain integration package."""

from __future__ import annotations

from .routes import bp
from ...templates.navigation import NavEntry

NAVIGATION = [
    NavEntry(endpoint="bia.dashboard", label="BIA", order=20),
]


def register(app):
    """Register BIA routes and services with the scaffold app."""

    app.register_blueprint(bp)
    app.logger.info("BIA module registered.")
