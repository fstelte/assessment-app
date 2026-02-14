from scaffold.apps.csa.models import Control
from scaffold.apps.identity.models import Role, User, UserStatus
from scaffold.extensions import db

def test_single_control_delete_successful(app, client):
    # Enable request context to access url_for and modify db
    with app.app_context():
        # strict CSRF protection is not enabled in test config (WTF_CSRF_ENABLED=False)
        # However, we want to ensure the form mechanics (prefixes) are correct.
        
        # Provision Admin User
        role = Role()
        role.name = "admin"
        db.session.add(role)
        
        admin = User()
        admin.email = "admin@example.com"
        admin.status = UserStatus.ACTIVE
        admin.set_password("Password123!")
        admin.roles.append(role)
        db.session.add(admin)
        
        # Provision Control to delete
        control = Control()
        control.domain = "Test Control"
        control.section = "TEST-01"
        db.session.add(control)
        db.session.commit()
        
        control_id = control.id

    # Login
    client.post(
        "/auth/login",
        data={"email": "admin@example.com", "password": "Password123!"},
        follow_redirects=True,
    )

    # Attempt delete with the prefix structure used by the frontend
    # The form expects prefixed fields: delete-{id}-control_id
    # Note: validation of CSRF token is disabled in tests, but field matching is not.
    response = client.post(
        f"/admin/controls/{control_id}/delete",
        data={
            f"delete-{control_id}-control_id": str(control_id),
            # In a real scenario, csrf_token would also be here
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    
    with app.app_context():
        # Verify control is gone
        deleted_control = db.session.get(Control, control_id)
        assert deleted_control is None
