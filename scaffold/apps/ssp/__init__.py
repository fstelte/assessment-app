"""System Security Plan application initialization."""

from flask import Blueprint
from ...templates.navigation import NavEntry

bp = Blueprint(
    "ssp",
    __name__,
    template_folder="templates",
    url_prefix="/ssp",
)

NAVIGATION = [
    NavEntry(endpoint="ssp.index", label="ssp.navigation.label", icon="file-earmark-lock", order=55),
]


def register(app):
    """Register the blueprint and any other app-specific configuration."""
    from . import models  # noqa: F401
    from . import routes  # noqa: F401

    app.register_blueprint(bp)
