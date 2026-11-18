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


# ---------------------------------------------------------------------------
# Task 11: reset on material change (decisions 20261118-1039, -1057)
# ---------------------------------------------------------------------------

from datetime import date, timedelta  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from scaffold.apps.bia.models import Component, ContextScope  # noqa: E402
from scaffold.apps.csa.models import Control  # noqa: E402
from scaffold.apps.identity.models import ROLE_ADMIN, Role, User, UserStatus  # noqa: E402
from scaffold.apps.risk.models import RiskImpactArea  # noqa: E402
from scaffold.apps.risk.services import apply_payload_to_risk  # noqa: E402
from scaffold.apps.threat.services import publish_pasta_conclusion_to_risk  # noqa: E402
from scaffold.extensions import db  # noqa: E402
from scaffold.models.audit import AuditLog  # noqa: E402


def _user(email: str = "owner@example.com", *, admin: bool = False) -> User:
    user = User()
    user.email = email
    user.status = UserStatus.ACTIVE
    user.set_password("Password123!")
    if admin:
        role = Role.query.filter_by(name=ROLE_ADMIN).first() or Role(name=ROLE_ADMIN)
        user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user


def _sign_in(client, user: User) -> None:
    """Session login; the password login forces MFA enrolment."""
    with client.session_transaction() as sess:
        sess["_user_id"] = user.get_id()
        sess["_fresh"] = True
        sess["login_time"] = datetime.now(UTC).isoformat()


def _approved_risk(owner: User, **kwargs) -> Risk:
    scope = ContextScope(name="Core Service", risk_assessment_human=True)
    component = Component(name="Payroll Portal", context_scope=scope)
    control = Control()
    control.domain = "ISO-27002-5.7"
    control.section = "5"
    control.description = "Encrypt backups"
    risk = _risk(treatment_owner_id=owner.id, discovered_on=date.today(), **kwargs)
    risk.components = [component]
    risk.controls = [control]
    risk.approval_status = RiskApprovalStatus.APPROVED
    risk.approval_decided_at = datetime.now(UTC)
    risk.approval_decided_by_id = owner.id
    risk.approval_comment = "ok"
    db.session.add_all([scope, component, control, risk])
    db.session.commit()
    return risk


def _assert_reset(risk: Risk) -> None:
    db.session.refresh(risk)
    assert (
        risk.approval_status,
        risk.approval_decided_at,
        risk.approval_decided_by_id,
        risk.approval_comment,
    ) == (None, None, None, None)


def _assert_kept(risk: Risk) -> None:
    db.session.refresh(risk)
    assert risk.approval_status is RiskApprovalStatus.APPROVED
    assert risk.approval_comment == "ok"


def _form_payload(risk: Risk, **overrides) -> dict:
    payload = {
        "title": risk.title,
        "description": risk.description,
        "discovered_on": risk.discovered_on.isoformat(),
        "impact": risk.impact.value,
        "chance": risk.chance.value,
        "impact_areas": [RiskImpactArea.OPERATIONAL.value],
        "component_ids": [str(c.id) for c in risk.components],
        "treatment": risk.treatment.value,
        "treatment_plan": "Fix it",
        "treatment_owner_id": str(risk.treatment_owner_id),
        "csa_control_ids": [str(c.id) for c in risk.controls],
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "change",
    [
        {"chance": RiskChance.RARE},
        {"impact": RiskImpact.MINOR},
        {"treatment": RiskTreatmentOption.ACCEPT},
        {"residual_chance": RiskChance.RARE},
        {"residual_impact": RiskImpact.MINOR},
    ],
)
def test_material_change_resets_approval(change):
    risk = _approved_risk(_user())
    for key, value in change.items():
        setattr(risk, key, value)
    db.session.commit()

    _assert_reset(risk)


def test_owner_change_resets_approval():
    risk = _approved_risk(_user())
    risk.treatment_owner_id = _user("other@example.com").id
    db.session.commit()

    _assert_reset(risk)


def test_mitigated_flip_resets_approval_both_ways():
    owner = _user()
    risk = _approved_risk(owner)
    risk.mitigated_at = datetime.now(UTC)
    db.session.commit()
    _assert_reset(risk)

    risk.approval_status = RiskApprovalStatus.APPROVED
    db.session.commit()
    risk.mitigated_at = None
    db.session.commit()
    _assert_reset(risk)


@pytest.mark.parametrize(
    "change",
    [
        {"title": "Renamed"},
        {"description": "Reworded"},
        {"ticket_url": "https://jira.example.com/browse/X-1"},
        {"treatment_plan": "New plan"},
        {"treatment_due_date": date.today() + timedelta(days=30)},
        {"closed_at": datetime.now(UTC)},
        # Assigning the current value is not a change (the sync does this on every run).
        {"chance": RiskChance.LIKELY, "impact": RiskImpact.MAJOR},
    ],
)
def test_non_material_change_keeps_approval(change):
    risk = _approved_risk(_user())
    for key, value in change.items():
        setattr(risk, key, value)
    db.session.commit()

    _assert_kept(risk)


def test_new_mitigated_timestamp_keeps_approval():
    risk = _approved_risk(_user(), mitigated_at=datetime(2026, 1, 1, tzinfo=UTC))
    risk.mitigated_at = datetime(2026, 6, 1, tzinfo=UTC)
    db.session.commit()

    _assert_kept(risk)


def test_close_and_reopen_keep_approval():
    risk = _approved_risk(_user())
    risk.closed_at = datetime.now(UTC)
    db.session.commit()
    risk.closed_at = None
    db.session.commit()

    _assert_kept(risk)


def test_component_change_keeps_approval():
    risk = _approved_risk(_user())
    risk.components = [Component(name="Other", context_scope=risk.components[0].context_scope)]
    db.session.commit()

    _assert_kept(risk)


def test_reset_is_in_the_generic_audit_row():
    """Guards the listener order: the reset must run before the audit captures the diff."""
    risk = _approved_risk(_user())
    risk.chance = RiskChance.RARE
    db.session.commit()

    event = (
        AuditLog.query.filter_by(event_type="risk.updated", target_id=str(risk.id))
        .order_by(AuditLog.id.desc())
        .first()
    )
    changes = event.payload["changes"]
    assert changes["chance"]["new"] == "rare"
    assert changes["approval_status"] == {"old": "approved", "new": None}
    assert changes["approval_comment"]["new"] is None


# --- write paths -----------------------------------------------------------


def test_risk_form_edit_resets_on_material_change(client):
    owner = _user()
    risk = _approved_risk(owner)
    _sign_in(client, owner)

    client.post(f"/risk/{risk.id}/edit", data=_form_payload(risk, chance=RiskChance.RARE.value))

    db.session.refresh(risk)
    assert risk.chance is RiskChance.RARE
    _assert_reset(risk)


def test_risk_form_edit_of_text_keeps_approval(client):
    owner = _user()
    risk = _approved_risk(owner)
    _sign_in(client, owner)

    client.post(f"/risk/{risk.id}/edit", data=_form_payload(risk, title="Renamed"))

    db.session.refresh(risk)
    assert risk.title == "Renamed"
    _assert_kept(risk)


def test_admin_edit_resets_on_material_change(client):
    admin = _user("admin@example.com", admin=True)
    risk = _approved_risk(_user())
    _sign_in(client, admin)

    client.post(f"/admin/risks/{risk.id}", data=_form_payload(risk, impact=RiskImpact.MINOR.value))

    db.session.refresh(risk)
    assert risk.impact is RiskImpact.MINOR
    _assert_reset(risk)


def test_api_payload_resets_on_material_change():
    risk = _approved_risk(_user())
    payload = {
        "title": risk.title,
        "description": risk.description,
        "impact": risk.impact.value,
        "chance": RiskChance.RARE.value,
        "treatment": risk.treatment.value,
        "component_ids": [c.id for c in risk.components],
        "csa_control_ids": [c.id for c in risk.controls],
        "impact_areas": [RiskImpactArea.OPERATIONAL.value],
        "treatment_owner_id": risk.treatment_owner_id,
    }

    apply_payload_to_risk(risk, payload)
    db.session.commit()

    _assert_reset(risk)


def test_pasta_republish_resets_on_material_change():
    risk = _approved_risk(_user())
    conclusion = SimpleNamespace(
        is_publishable=True,
        likelihood_score=1,  # rare, was likely
        impact_score=4,
        treatment="mitigate",
        finding=SimpleNamespace(title=risk.title, description=risk.description),
        published_risk_id=risk.id,
    )

    publish_pasta_conclusion_to_risk(conclusion, None)
    db.session.commit()

    _assert_reset(risk)


def test_decision_in_same_flush_as_material_change_is_kept():
    owner = _user()
    risk = _approved_risk(owner)
    risk.approval_status = None
    db.session.commit()

    risk.treatment_owner_id = _user("new-owner@example.com").id
    risk.approval_status = RiskApprovalStatus.REJECTED
    db.session.commit()

    db.session.refresh(risk)
    assert risk.approval_status is RiskApprovalStatus.REJECTED


# ---------------------------------------------------------------------------
# Task 12: approve / reject routes (decisions 20261118-1046, -1058)
# ---------------------------------------------------------------------------


def _decision_events(risk: Risk, action: str) -> list[AuditLog]:
    return AuditLog.query.filter_by(event_type=action, target_id=str(risk.id)).order_by(AuditLog.id).all()


def _undecided_risk(owner: User) -> Risk:
    risk = _approved_risk(owner)
    risk.approval_status = None
    risk.approval_decided_at = None
    risk.approval_decided_by_id = None
    risk.approval_comment = None
    db.session.commit()
    return risk


def test_owner_approves(client):
    owner = _user()
    risk = _undecided_risk(owner)
    _sign_in(client, owner)

    resp = client.post(f"/risk/{risk.id}/approve", data={"fingerprint": risk.approval_fingerprint(), "comment": " fine "})

    assert resp.status_code == 302
    db.session.refresh(risk)
    assert risk.approval_state == "approved"
    assert risk.approval_decided_by_id == owner.id
    assert risk.approval_decided_at is not None
    assert risk.approval_comment == "fine"
    (event,) = _decision_events(risk, "risk_approved")
    assert event.actor_id == owner.id
    assert event.payload["decision"] == "approved"
    assert event.payload["chance"] == "likely"
    assert event.payload["actual_score"] == risk.actual_score()
    assert event.payload["fingerprint"] == risk.approval_fingerprint()


def test_owner_rejects_with_comment(client):
    owner = _user()
    risk = _undecided_risk(owner)
    _sign_in(client, owner)

    client.post(f"/risk/{risk.id}/reject", data={"fingerprint": risk.approval_fingerprint(), "comment": "Chance too low"})

    db.session.refresh(risk)
    assert risk.approval_state == "rejected"
    assert risk.approval_comment == "Chance too low"
    assert len(_decision_events(risk, "risk_rejected")) == 1


def test_reject_without_comment_changes_nothing(client):
    owner = _user()
    risk = _undecided_risk(owner)
    _sign_in(client, owner)

    client.post(f"/risk/{risk.id}/reject", data={"fingerprint": risk.approval_fingerprint(), "comment": "  "})

    db.session.refresh(risk)
    assert risk.approval_state == "awaiting"
    assert _decision_events(risk, "risk_rejected") == []


def test_stale_fingerprint_changes_nothing(client):
    owner = _user()
    risk = _undecided_risk(owner)
    stale = risk.approval_fingerprint()
    risk.chance = RiskChance.RARE
    db.session.commit()
    _sign_in(client, owner)

    resp = client.post(f"/risk/{risk.id}/approve", data={"fingerprint": stale})

    assert resp.status_code == 302
    db.session.refresh(risk)
    assert risk.approval_state == "awaiting"
    assert _decision_events(risk, "risk_approved") == []


def test_owner_can_flip_and_reapprove(client):
    owner = _user()
    risk = _undecided_risk(owner)
    _sign_in(client, owner)
    fingerprint = risk.approval_fingerprint()

    client.post(f"/risk/{risk.id}/approve", data={"fingerprint": fingerprint})
    client.post(f"/risk/{risk.id}/reject", data={"fingerprint": fingerprint, "comment": "On second thought"})
    client.post(f"/risk/{risk.id}/approve", data={"fingerprint": fingerprint})
    client.post(f"/risk/{risk.id}/approve", data={"fingerprint": fingerprint})

    db.session.refresh(risk)
    assert risk.approval_state == "approved"
    assert risk.approval_comment is None
    assert len(_decision_events(risk, "risk_approved")) == 3
    assert len(_decision_events(risk, "risk_rejected")) == 1


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_non_owner_and_admin_get_403(client, action):
    risk = _undecided_risk(_user())
    data = {"fingerprint": risk.approval_fingerprint(), "comment": "x"}

    _sign_in(client, _user("someone@example.com"))
    assert client.post(f"/risk/{risk.id}/{action}", data=data).status_code == 403

    _sign_in(client, _user("admin@example.com", admin=True))
    assert client.post(f"/risk/{risk.id}/{action}", data=data).status_code == 403

    db.session.refresh(risk)
    assert risk.approval_state == "awaiting"


def test_risk_without_owner_gets_403(client):
    owner = _user()
    risk = _undecided_risk(owner)
    risk.treatment_owner_id = None
    db.session.commit()
    _sign_in(client, owner)

    resp = client.post(f"/risk/{risk.id}/approve", data={"fingerprint": risk.approval_fingerprint()})

    assert resp.status_code == 403


def test_unknown_risk_gets_404(client):
    _sign_in(client, _user())

    assert client.post("/risk/999/approve", data={"fingerprint": "x"}).status_code == 404


def test_anonymous_is_redirected_to_login(client):
    risk = _undecided_risk(_user())

    resp = client.post(f"/risk/{risk.id}/approve", data={"fingerprint": risk.approval_fingerprint()})

    assert resp.status_code in (302, 401)
    db.session.refresh(risk)
    assert risk.approval_state == "awaiting"


# ---------------------------------------------------------------------------
# Task 13: approval panel on the edit page (decisions 20261118-1048, -1058)
# ---------------------------------------------------------------------------


def _edit_page(client, risk: Risk) -> str:
    resp = client.get(f"/risk/{risk.id}/edit")
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def test_owner_sees_decision_buttons_with_current_fingerprint(client):
    owner = _user()
    risk = _undecided_risk(owner)
    _sign_in(client, owner)

    html = _edit_page(client, risk)

    assert 'data-approval-state="awaiting"' in html
    assert f'formaction="/risk/{risk.id}/approve"' in html
    assert f'formaction="/risk/{risk.id}/reject"' in html
    assert f'value="{risk.approval_fingerprint()}"' in html


def test_non_owner_sees_state_but_no_buttons(client):
    owner = _user()
    risk = _approved_risk(owner)
    _sign_in(client, _user("someone@example.com"))

    html = _edit_page(client, risk)

    assert 'data-approval-state="approved"' in html
    assert "/approve" not in html
    assert "ok" in html  # the decision's comment
    assert owner.full_name in html


def test_no_owner_shows_hint(client):
    owner = _user()
    risk = _undecided_risk(owner)
    risk.treatment_owner_id = None
    db.session.commit()
    _sign_in(client, owner)

    html = _edit_page(client, risk)

    assert 'data-approval-state="no_owner"' in html
    assert "Assign an owner to request approval." in html
    assert "/approve" not in html


def test_previous_rejection_reason_shown_after_reset(client):
    owner = _user()
    owner.first_name, owner.last_name = "Olive", "Owner"
    risk = _undecided_risk(owner)
    _sign_in(client, owner)
    client.post(f"/risk/{risk.id}/reject", data={"fingerprint": risk.approval_fingerprint(), "comment": "Impact is understated"})
    risk.impact = RiskImpact.CATASTROPHIC  # manager revises -> reset
    db.session.commit()
    db.session.refresh(risk)
    assert risk.approval_state == "awaiting"

    html = _edit_page(client, risk)

    assert "Previously rejected by Olive Owner on" in html
    assert "Impact is understated" in html


def test_new_risk_page_has_no_approval_panel(client):
    _sign_in(client, _user())

    html = client.get("/risk/new").get_data(as_text=True)

    assert "data-approval-state" not in html


# ---------------------------------------------------------------------------
# Task 14: dashboard pill and ?approval= filter (decisions 20261118-1048, -1058)
# ---------------------------------------------------------------------------


def _dashboard_set(me: User, other: User) -> dict[str, Risk]:
    """One risk per case, all in BIA "A" except "other_bia"."""

    bia_a = ContextScope(name="A", risk_assessment_human=True)
    bia_b = ContextScope(name="B", risk_assessment_human=True)
    comp_a = Component(name="App A", context_scope=bia_a)
    comp_b = Component(name="App B", context_scope=bia_b)
    specs = {
        "mine_awaiting": (me, None, None, comp_a),
        "mine_rejected": (me, RiskApprovalStatus.REJECTED, None, comp_a),
        "mine_approved": (me, RiskApprovalStatus.APPROVED, None, comp_a),
        "mine_closed": (me, None, datetime.now(UTC), comp_a),
        "other_awaiting": (other, None, None, comp_a),
        "other_rejected": (other, RiskApprovalStatus.REJECTED, None, comp_a),
        "no_owner": (None, None, None, comp_a),
        "other_bia": (me, None, None, comp_b),
    }
    risks = {}
    for title, (owner, status, closed_at, component) in specs.items():
        risk = _risk(title=title, treatment_owner_id=owner.id if owner else None, discovered_on=date.today())
        risk.approval_status = status
        risk.closed_at = closed_at
        risk.components = [component]
        risks[title] = risk
    db.session.add_all([bia_a, bia_b, comp_a, comp_b, *risks.values()])
    db.session.commit()
    return risks


def _shown(client, query: str, risks: dict[str, Risk]) -> set[str]:
    html = client.get(f"/risk/{query}").get_data(as_text=True)
    return {title for title, risk in risks.items() if f'id="risk-{risk.id}"' in html}


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("?approval=mine", {"mine_awaiting", "mine_rejected", "other_bia"}),
        ("?approval=awaiting", {"mine_awaiting", "other_awaiting", "other_bia"}),
        ("?approval=rejected", {"mine_rejected", "other_rejected"}),
        ("?approval=bogus", None),  # ignored -> everything
        ("", None),
    ],
)
def test_approval_filter(client, query, expected):
    me = _user()
    risks = _dashboard_set(me, _user("other@example.com"))
    _sign_in(client, me)

    assert _shown(client, query, risks) == (expected if expected is not None else set(risks))


def test_approval_filter_combines_with_bia_filter_and_counts_mine(client):
    me = _user()
    risks = _dashboard_set(me, _user("other@example.com"))
    bia_a = ContextScope.query.filter_by(name="A").one()
    _sign_in(client, me)

    assert _shown(client, f"?approval=mine&bia={bia_a.id}", risks) == {"mine_awaiting", "mine_rejected"}
    html = client.get(f"/risk/?bia={bia_a.id}").get_data(as_text=True)
    assert "Awaiting my approval (2)" in html
    html = client.get("/risk/").get_data(as_text=True)
    assert "Awaiting my approval (3)" in html


def test_cards_show_approval_pill(client):
    me = _user()
    _dashboard_set(me, _user("other@example.com"))
    _sign_in(client, me)

    html = client.get("/risk/").get_data(as_text=True)

    for state in ("awaiting", "approved", "rejected", "no_owner"):
        assert f'data-approval-state="{state}"' in html


def test_empty_approval_filter_shows_message(client):
    me = _user()
    _sign_in(client, me)

    html = client.get("/risk/?approval=rejected").get_data(as_text=True)

    assert "data-approval-empty" in html
    assert "No risks match the approval filter." in html
