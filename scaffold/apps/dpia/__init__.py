"""Data Protection Impact Assessment / FRIA module bootstrap."""

from __future__ import annotations

from flask import Flask

from ...templates.navigation import NavEntry


def register(app: Flask) -> None:
    """Hook called by the registry to bind the DPIA blueprint."""

    from .routes import blueprint  # Local import to avoid circular dependencies

    app.register_blueprint(blueprint)
    app.logger.info("DPIA module registered")


NAVIGATION = [
    NavEntry(endpoint="dpia.dashboard", label="dpia.navigation.dashboard", order=30),
]
