"""Tests for the control importer service."""

from __future__ import annotations

import pytest

from app.models import AssessmentTemplate, Control
from app.services import import_controls_from_mapping


def _payload(description_suffix: str = "") -> dict:
    return {
        "framework": "Unit Test Framework",
        "controls": [
            {
                "id": "TEST-FRAMEWORK 5.1",
                "section": f"Policies for information security - Baseline policy{description_suffix}",
                "domain": "5 Organisational Controls",
            }
        ],
    }


def test_import_creates_control(app):
    stats = import_controls_from_mapping(_payload())
    assert stats.created == 1
    assert stats.updated == 0
    assert not stats.errors

    control = Control.query.filter_by(domain="Policies for information security").one()
    assert control.description == "Baseline policy"
    assert control.section == "5.1"
    assert len(control.templates) == 1
    template = AssessmentTemplate.query.filter_by(control_id=control.id).one()
    assert template.question_set is not None


def test_import_updates_existing_control(app):
    import_controls_from_mapping(_payload())
    stats = import_controls_from_mapping(_payload(" (updated)"))

    assert stats.created == 0
    assert stats.updated == 1
    control = Control.query.filter_by(domain="Policies for information security").one()
    assert control.description.endswith("(updated)")


def test_import_rejects_missing_controls_key(app):
    with pytest.raises(ValueError):
        import_controls_from_mapping({})


def test_import_collects_errors_for_invalid_entry(app):
    stats = import_controls_from_mapping(
        {
            "framework": "Invalid",
            "controls": [
                {"clause": "1"},  # missing name/section triggers error capture
            ],
        }
    )
    assert stats.errors
    assert stats.created == 0
