import pytest
from flask import g

from scaffold.apps.bia.models import (
    AvailabilityRequirements,
    BiaTier,
    Component,
    ContextScope,
    format_duration_seconds,
)
from scaffold.core.i18n import set_locale
from scaffold.apps.identity.models import User
from scaffold.extensions import db, login_manager


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


# --- Task 2: tier field on the component routes ---------------------------------
# Local accounts are redirected to MFA enrolment by /auth/login, so the shared
# `login` fixture no longer yields an authenticated client. Set the Flask-Login
# session directly instead.


@pytest.fixture
def logged_in(app, client, active_user, monkeypatch):
    monkeypatch.setattr(login_manager, "session_protection", None)
    user_id = User.find_by_email("user@example.com").id
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def _request(client, method, url, **kwargs):
    # Requests reuse the test's app context, and audit listeners fired by the
    # test's own commits cache an anonymous user on `g`; drop it so Flask-Login
    # loads the user from the session.
    g.pop("_login_user", None)
    return getattr(client, method)(url, **kwargs)


def _component_form_data(**overrides):
    data = {"name": "Portal", "info_owner": "", "user_type": "", "description": ""}
    for idx, env in enumerate(("development", "test", "acceptance", "production")):
        data[f"environments-{idx}-environment_type"] = env
        data[f"environments-{idx}-authentication_method"] = ""
    data.update(overrides)
    return data


def _owned_context(tier=None):
    context = ContextScope(name="Owned", author=User.find_by_email("user@example.com"), tier=tier)
    db.session.add(context)
    db.session.commit()
    return context


def test_add_component_saves_tier_or_inherits(app, client, logged_in):
    tier = _tier(1)
    context = _owned_context()
    context_id, tier_id = context.id, tier.id

    with_tier = _request(client, "post", "/bia/add_component", data=_component_form_data(bia_id=str(context_id), tier=str(tier_id)))
    inherit = _request(client, "post", "/bia/add_component", data=_component_form_data(bia_id=str(context_id), name="Other", tier=""))

    assert with_tier.status_code == 200 and inherit.status_code == 200
    assert Component.query.filter_by(name="Portal").one().tier_id == tier_id
    assert Component.query.filter_by(name="Other").one().tier_id is None


def test_edit_component_sets_and_clears_tier(app, client, logged_in):
    tier = _tier(1)
    context = _owned_context(tier=_tier(2))
    component = Component(name="Portal", context_scope=context)
    db.session.add(component)
    db.session.commit()
    component_id, context_id, tier_id = component.id, context.id, tier.id
    url = f"/bia/component/{component_id}/edit"

    assert _request(client, "post", url, data=_component_form_data(bia_id=str(context_id), tier=str(tier_id))).status_code == 302
    assert db.session.get(Component, component_id).tier_id == tier_id

    assert _request(client, "post", url, data=_component_form_data(bia_id=str(context_id), tier="")).status_code == 302
    db.session.expire_all()
    assert db.session.get(Component, component_id).tier_id is None


def test_edit_component_page_labels_inherit_option_with_bia_tier(app, client, logged_in):
    context = _owned_context(tier=_tier(2))
    component = Component(name="Portal", context_scope=context)
    db.session.add(component)
    db.session.commit()

    body = _request(client, "get", f"/bia/component/{component.id}/edit").data.decode()

    assert "Inherit from BIA (TIER 2" in body


def test_get_component_json_reports_effective_tier(app, client, logged_in):
    context = _owned_context(tier=_tier(2))
    inheriting = Component(name="A", context_scope=context)
    own = Component(name="B", context_scope=context, tier=_tier(1))
    db.session.add_all([inheriting, own])
    db.session.commit()

    a = _request(client, "get", f"/bia/get_component/{inheriting.id}").get_json()
    b = _request(client, "get", f"/bia/get_component/{own.id}").get_json()

    assert a["tier"].startswith("TIER 2") and a["tier_inherited"] is True
    assert b["tier"].startswith("TIER 1") and b["tier_inherited"] is False
