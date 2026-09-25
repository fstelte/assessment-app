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


# --- Task 3: tier goals in the availability form ----------------------------------


def _availability_component(tier, rto="old rto", rpo="old rpo"):
    context = _owned_context(tier=tier)
    component = Component(name="Portal", context_scope=context)
    component.availability_requirement = AvailabilityRequirements(mtd="old mtd", rto=rto, rpo=rpo, masl="old masl")
    db.session.add(component)
    db.session.commit()
    return component.id


AVAILABILITY_POST = {"mtd": "new mtd", "rto": "new rto", "rpo": "new rpo", "masl": "new masl"}


def _stored(component_id):
    db.session.expire_all()
    return AvailabilityRequirements.query.filter_by(component_id=component_id).one()


def test_availability_page_shows_goal_and_keeps_stored_text(app, client, logged_in):
    component_id = _availability_component(_tier(1, rto=14400, rpo=1800))
    url = f"/bia/component/{component_id}/availability"

    body = _request(client, "get", url).data.decode()
    assert "From TIER 1" in body and "4 h" in body and "30 min" in body
    assert "(inherited from BIA)" in body
    assert 'name="rto"' not in body and 'name="rpo"' not in body

    assert _request(client, "post", url, data=AVAILABILITY_POST).status_code == 302
    stored = _stored(component_id)
    assert (stored.rto, stored.rpo) == ("old rto", "old rpo")
    assert (stored.mtd, stored.masl) == ("new mtd", "new masl")


def test_availability_without_goal_saves_free_text(app, client, logged_in):
    component_id = _availability_component(_tier(1))
    url = f"/bia/component/{component_id}/availability"

    body = _request(client, "get", url).data.decode()
    assert 'name="rto"' in body and 'name="rpo"' in body

    assert _request(client, "post", url, data=AVAILABILITY_POST).status_code == 302
    stored = _stored(component_id)
    assert (stored.rto, stored.rpo) == ("new rto", "new rpo")


def test_availability_decides_rto_and_rpo_independently(app, client, logged_in):
    component_id = _availability_component(_tier(1, rto=3600))
    url = f"/bia/component/{component_id}/availability"

    body = _request(client, "get", url).data.decode()
    assert 'name="rto"' not in body and 'name="rpo"' in body

    _request(client, "post", url, data=AVAILABILITY_POST)
    stored = _stored(component_id)
    assert (stored.rto, stored.rpo) == ("old rto", "new rpo")


def test_update_availability_json_respects_tier_goal(app, client, logged_in):
    component_id = _availability_component(_tier(1, rto=3600))

    response = _request(client, "post", f"/bia/update_availability/{component_id}", data=AVAILABILITY_POST)

    assert response.get_json() == {"success": True}
    stored = _stored(component_id)
    assert (stored.rto, stored.rpo) == ("old rto", "new rpo")


# --- Task 4: effective values in views, exports and summary aggregation -----------


def _bia_with_component(bia_name, tier=None, **availability):
    context = ContextScope(name=bia_name, author=User.find_by_email("user@example.com"), tier=tier)
    component = Component(name=f"{bia_name} component", context_scope=context)
    if availability:
        component.availability_requirement = AvailabilityRequirements(**availability)
    db.session.add_all([context, component])
    db.session.commit()
    return context.id


def test_summary_export_uses_tier_goals_and_stored_text(app, client, logged_in, tmp_path, monkeypatch):
    monkeypatch.setattr("scaffold.apps.bia.routes.ensure_export_folder", lambda: tmp_path)
    # Tier goal, and no availability row at all.
    _bia_with_component("Tiered", tier=_tier(1, rto=3600, rpo=900))
    # No tier: stored text is used.
    _bia_with_component("Untiered", rto="2 hours", rpo="45 minutes")

    response = _request(client, "get", "/bia/export_availability_requirements?type=summary")
    body = response.data.decode()

    assert response.status_code == 200
    assert "1 h" in body and "15 min" in body
    assert "2 hours" in body and "45 minutes" in body


def test_summary_export_takes_lowest_of_tier_goal_and_stored_text(app, client, logged_in, tmp_path, monkeypatch):
    monkeypatch.setattr("scaffold.apps.bia.routes.ensure_export_folder", lambda: tmp_path)
    context = ContextScope(name="Mixed", author=User.find_by_email("user@example.com"))
    with_goal = Component(name="A", context_scope=context, tier=_tier(1, rto=600))
    stored_only = Component(name="B", context_scope=context, tier=_tier(2))
    stored_only.availability_requirement = AvailabilityRequirements(rto="30 minutes")
    db.session.add_all([context, with_goal, stored_only])
    db.session.commit()

    body = _request(client, "get", "/bia/export_availability_requirements?type=summary").data.decode()

    assert "10 min" in body and "30 minutes" not in body


def test_component_pages_show_tier_goal_without_availability_row(app, client, logged_in):
    context_id = _bia_with_component("Tiered", tier=_tier(1, rto=14400, rpo=1800))

    components_page = _request(client, "get", "/bia/components").data.decode()
    detail_page = _request(client, "get", f"/bia/item/{context_id}").data.decode()

    assert "RTO: 4 h" in components_page and "RPO: 30 min" in components_page
    assert "4 h" in detail_page and "30 min" in detail_page


def test_requirements_page_shows_tier_goal_instead_of_stored_text(app, client, logged_in):
    _bia_with_component("Tiered", tier=_tier(1, rto=14400), rto="stale text", rpo="kept text")

    body = _request(client, "get", "/bia/requirements").data.decode()

    assert "4 h" in body and "stale text" not in body
    assert "kept text" in body
