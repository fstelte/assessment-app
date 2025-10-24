from __future__ import annotations

from scaffold.apps.identity.models import Role, User, UserStatus
from scaffold.extensions import db


def test_admin_mfa_routes_use_shared_helpers(app, client):
    with app.app_context():
        admin_role = Role()
        admin_role.name = "admin"
        db.session.add(admin_role)
        db.session.commit()

        admin = User()
        admin.email = "admin@example.com"
        admin.status = UserStatus.ACTIVE
        admin.set_password("Password123!")
        admin.roles.append(admin_role)
        db.session.add(admin)
        db.session.commit()

    response = client.post(
        "/auth/login",
        data={"email": "admin@example.com", "password": "Password123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        target_user = User()
        target_user.email = "target@example.com"
        target_user.status = UserStatus.ACTIVE
        target_user.set_password("Password123!")
        db.session.add(target_user)
        db.session.commit()
        target_id = target_user.id

    manage_resp = client.get(f"/admin/users/{target_id}/mfa")
    assert manage_resp.status_code == 200
    assert "Manage MFA" in manage_resp.get_data(as_text=True)

    reset_resp = client.post(f"/admin/users/{target_id}/mfa/reset", follow_redirects=True)
    assert reset_resp.status_code == 200
    page = reset_resp.get_data(as_text=True)
    assert "MFA secret regenerated" in page

    with app.app_context():
        refreshed_user = db.session.get(User, target_id)
        assert refreshed_user.mfa_setting is not None
        assert refreshed_user.mfa_setting.enabled is True
