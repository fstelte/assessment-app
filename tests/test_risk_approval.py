"""Risk owner approval (design Part 2, decisions 20261118-1038 to -1058)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from scaffold.apps.risk.models import (
    Risk,
    RiskApprovalStatus,
    RiskChance,
    RiskImpact,
    RiskTreatmentOption,
)

# The app fixture imports every model so the mappers configure.
pytestmark = pytest.mark.usefixtures("app")


def _risk(**kwargs) -> Risk:
    values = {
        "title": "R",
        "description": "R",
        "impact": RiskImpact.MAJOR,
        "chance": RiskChance.LIKELY,
        "treatment": RiskTreatmentOption.MITIGATE,
        "treatment_owner_id": 7,
    }
    values.update(kwargs)
    return Risk(**values)


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"treatment_owner_id": None}, "no_owner"),
        ({"treatment_owner_id": None, "approval_status": RiskApprovalStatus.APPROVED}, "no_owner"),
        ({}, "awaiting"),
        ({"approval_status": RiskApprovalStatus.APPROVED}, "approved"),
        ({"approval_status": RiskApprovalStatus.REJECTED}, "rejected"),
    ],
)
def test_approval_state(kwargs, expected):
    assert _risk(**kwargs).approval_state == expected


def test_fingerprint_ignores_non_material_fields():
    base = _risk().approval_fingerprint()

    assert _risk(title="Other", description="Other", ticket_url="https://x").approval_fingerprint() == base


@pytest.mark.parametrize(
    "change",
    [
        {"chance": RiskChance.RARE},
        {"impact": RiskImpact.MINOR},
        {"treatment": RiskTreatmentOption.ACCEPT},
        {"residual_chance": RiskChance.RARE},
        {"residual_impact": RiskImpact.MINOR},
        {"treatment_owner_id": 8},
        {"mitigated_at": datetime.now(UTC)},
    ],
)
def test_fingerprint_changes_with_material_fields(change):
    assert _risk(**change).approval_fingerprint() != _risk().approval_fingerprint()


def test_fingerprint_ignores_mitigated_timestamp_value():
    earlier = _risk(mitigated_at=datetime(2026, 1, 1, tzinfo=UTC))
    later = _risk(mitigated_at=datetime(2026, 6, 1, tzinfo=UTC))

    assert earlier.approval_fingerprint() == later.approval_fingerprint()
