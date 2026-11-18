from __future__ import annotations

from datetime import date

from scaffold.apps.identity.models import Role, User
from scaffold.apps.risk.models import Risk, RiskChance, RiskImpact, RiskTreatmentOption
from scaffold.extensions import db


def _ensure_admin_role(app, user: User) -> None:
    with app.app_context():
        role = Role.query.filter_by(name="admin").first()
        if role is None:
            role = Role()
            role.name = "admin"
            db.session.add(role)
            db.session.commit()
        stored_user = db.session.get(User, user.id)
        if stored_user is None:
            raise RuntimeError("Active user fixture is missing")
        if role not in stored_user.roles:
            stored_user.roles.append(role)
            db.session.commit()


def _create_risk(app) -> int:
    with app.app_context():
        risk = Risk()
        risk.title = "Example risk"
        risk.description = "Example description"
        risk.discovered_on = date.today()
        risk.impact = RiskImpact.MINOR
        risk.chance = RiskChance.POSSIBLE
        risk.treatment = RiskTreatmentOption.ACCEPT
        db.session.add(risk)
        db.session.commit()
        return risk.id


def _login(client, active_user):
    response = client.post(
        "/auth/login",
        data={"email": active_user.email, "password": "Password123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200


def test_close_and_reopen_risk(app, client, active_user):
    _ensure_admin_role(app, active_user)
    _login(client, active_user)
    risk_id = _create_risk(app)

    close_resp = client.post(f"/risk/{risk_id}/close", follow_redirects=True)
    assert close_resp.status_code == 200
    with app.app_context():
        stored = db.session.get(Risk, risk_id)
        assert stored is not None
        assert stored.closed_at is not None

    reopen_resp = client.post(f"/risk/{risk_id}/reopen", follow_redirects=True)
    assert reopen_resp.status_code == 200
    with app.app_context():
        stored = db.session.get(Risk, risk_id)
        assert stored is not None
        assert stored.closed_at is None


def test_delete_risk(app, client, active_user):
    _ensure_admin_role(app, active_user)
    _login(client, active_user)
    risk_id = _create_risk(app)

    delete_resp = client.post(f"/risk/{risk_id}/delete", follow_redirects=True)
    assert delete_resp.status_code == 200
    with app.app_context():
        stored = db.session.get(Risk, risk_id)
        assert stored is None


# ---------------------------------------------------------------------------
# Closed banner on the edit page (Task 20)
# ---------------------------------------------------------------------------


def _closed_risk(app) -> int:
    from datetime import UTC, datetime

    risk_id = _create_risk(app)
    with app.app_context():
        db.session.get(Risk, risk_id).closed_at = datetime(2026, 11, 3, tzinfo=UTC)
        db.session.commit()
    return risk_id


def test_closed_manual_risk_edit_page_shows_banner_with_reopen(client, app, login):
    risk_id = _closed_risk(app)

    page = client.get(f"/risk/{risk_id}/edit").get_data(as_text=True)

    assert "data-risk-closed-banner" in page
    assert "Closed on 03 Nov 2026" in page
    assert f'action="/risk/{risk_id}/reopen"' in page
    assert "data-risk-closed-threat-note" not in page
    # The banner comes before the approval panel.
    assert page.index("data-risk-closed-banner") < page.index('aria-labelledby="risk-approval-heading"')


def test_reopen_from_edit_page_reopens_and_returns_to_edit(client, app, login):
    risk_id = _closed_risk(app)
    edit_url = f"/risk/{risk_id}/edit"

    response = client.post(f"/risk/{risk_id}/reopen", headers={"Referer": f"http://localhost{edit_url}"})

    assert response.status_code == 302
    assert response.headers["Location"].endswith(edit_url)
    with app.app_context():
        assert db.session.get(Risk, risk_id).closed_at is None
    assert "data-risk-closed-banner" not in client.get(edit_url).get_data(as_text=True)


def test_closed_threat_linked_risk_shows_note_without_reopen(client, app, login):
    from scaffold.apps.threat.models import (
        ScenarioStatus,
        StrideCategory,
        ThreatModel,
        ThreatScenario,
        TreatmentOption,
    )

    risk_id = _create_risk(app)
    with app.app_context():
        model = ThreatModel(title="TM")
        db.session.add(model)
        db.session.flush()
        db.session.add(
            ThreatScenario(
                threat_model_id=model.id,
                title="Accepted scenario",
                stride_category=StrideCategory.SPOOFING,
                status=ScenarioStatus.ACCEPTED,
                treatment=TreatmentOption.MITIGATE,
                likelihood=2,
                impact_score=2,
                risk_id=risk_id,
            )
        )
        db.session.commit()

    # Opening the page syncs the risk from its Accepted scenario, which closes it.
    page = client.get(f"/risk/{risk_id}/edit").get_data(as_text=True)

    assert "data-risk-closed-banner" in page
    assert "Reopens when its threat scenario is reopened." in page
    assert f'action="/risk/{risk_id}/reopen"' not in page


def test_open_risk_edit_page_has_no_closed_banner(client, app, login):
    risk_id = _create_risk(app)

    page = client.get(f"/risk/{risk_id}/edit").get_data(as_text=True)

    assert "data-risk-closed-banner" not in page
