"""Risk domain package."""

from ...templates.navigation import NavEntry
from .models import (
    Risk,
    RiskChance,
    RiskImpact,
    RiskImpactArea,
    RiskImpactAreaLink,
    RiskSeverity,
    RiskSeverityThreshold,
    RiskTreatmentOption,
)
from .routes import bp

__all__ = [
    "Risk",
    "RiskChance",
    "RiskImpact",
    "RiskImpactArea",
    "RiskImpactAreaLink",
    "RiskSeverity",
    "RiskSeverityThreshold",
    "RiskTreatmentOption",
    "NAVIGATION",
    "register",
]

NAVIGATION = [
    NavEntry(endpoint="risk.dashboard", label="app.navigation.risk", order=40),
]


def register(app):
    """Register the risk blueprint with the core app."""

    app.register_blueprint(bp)
    app.logger.info("Risk UI module registered.")
