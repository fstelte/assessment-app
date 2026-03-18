"""Threat modeling domain package."""

from ...templates.navigation import NavEntry
from .models import (
    AssetType,
    RiskLevel,
    ScenarioStatus,
    StrideCategory,
    ThreatModel,
    ThreatModelAsset,
    ThreatScenario,
    TreatmentOption,
)
from .routes import bp

__all__ = [
    "ThreatModel",
    "ThreatModelAsset",
    "ThreatScenario",
    "AssetType",
    "StrideCategory",
    "TreatmentOption",
    "ScenarioStatus",
    "RiskLevel",
    "NAVIGATION",
    "register",
]

NAVIGATION = [
    NavEntry(endpoint="threat.dashboard", label="app.navigation.threat", order=50),
]


def register(app):
    """Register the threat modeling blueprint with the core app."""

    app.register_blueprint(bp)
    app.logger.info("Threat modeling module registered.")
