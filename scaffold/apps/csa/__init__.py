"""CSA domain integration package."""

from __future__ import annotations

from .routes import bp
from ...templates.navigation import NavEntry

NAVIGATION = [
    NavEntry(endpoint="csa.dashboard", label="CSA", order=30),
]


def register(app):
    """Register CSA blueprints and services with the scaffold app."""

    app.register_blueprint(bp)
    app.logger.info("CSA module registered.")
