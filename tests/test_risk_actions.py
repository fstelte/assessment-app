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
