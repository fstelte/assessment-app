"""Self-assessment blueprint."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("assessments", __name__, url_prefix="/assessments")

from . import routes  # noqa: E402,F401
