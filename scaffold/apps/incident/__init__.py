"""Incident Response Plan application initialization."""

from flask import Blueprint
from ...templates.navigation import NavEntry

bp = Blueprint(
    "incident",
    __name__,
    template_folder="templates",
    url_prefix="/incident",
)

NAVIGATION = [
    NavEntry(endpoint="incident.dashboard", label="incident.navigation.label", icon="shield-virus", order=50),
]

def register(app):
    """Register the blueprint and any other app-specific configuration."""
    from . import routes  # noqa: F401
    
    app.register_blueprint(bp)
