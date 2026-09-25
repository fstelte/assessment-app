import pytest

from scaffold.apps.bia.models import (
    AvailabilityRequirements,
    BiaTier,
    Component,
    ContextScope,
    format_duration_seconds,
)
from scaffold.core.i18n import set_locale
from scaffold.extensions import db


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(14400, "4 h"), (5400, "90 min"), (90, "90 s"), (0, "0 s"), (172800, "2 d"), (None, None)],
)
def test_format_duration_seconds(app, seconds, expected):
    with app.test_request_context():
        assert format_duration_seconds(seconds) == expected


def test_format_duration_seconds_dutch_labels(app):
    with app.test_request_context():
        set_locale("nl")
        assert format_duration_seconds(7200) == "2 u"


def _tier(level, rto=None, rpo=None):
    tier = BiaTier(level=level, name_en=f"T{level}", name_nl=f"T{level}", rto_goal_seconds=rto, rpo_goal_seconds=rpo)
    db.session.add(tier)
    return tier


def _component(context_tier=None, own_tier=None, rto=None, rpo=None):
    context = ContextScope(name="Ctx", tier=context_tier)
    component = Component(name="Comp", context_scope=context, tier=own_tier)
    if rto or rpo:
        component.availability_requirement = AvailabilityRequirements(rto=rto, rpo=rpo)
    db.session.add_all([context, component])
    db.session.commit()
    return component


def test_effective_tier_prefers_own_then_bia_then_none(app):
    own, bia = _tier(1), _tier(2)
    assert _component(context_tier=bia, own_tier=own).effective_tier is own
    assert _component(context_tier=bia).effective_tier is bia
    assert _component().effective_tier is None


def test_effective_recovery_uses_tier_goal_over_stored_text(app):
    with app.test_request_context():
        component = _component(context_tier=_tier(1, rto=14400, rpo=1800), rto="8 hours", rpo="1 hour")
        assert component.effective_rto == "4 h"
        assert component.effective_rpo == "30 min"


def test_effective_recovery_falls_back_per_field(app):
    with app.test_request_context():
        component = _component(context_tier=_tier(1, rto=14400), rpo="1 hour")
        assert component.effective_rto == "4 h"
        assert component.effective_rpo == "1 hour"


def test_effective_recovery_without_tier_or_text_is_none(app):
    component = _component()
    assert component.effective_rto is None
    assert component.effective_rpo is None
