import io
import json
from datetime import UTC, datetime

from scaffold.apps.bia.models import ContextScope
from scaffold.apps.identity.models import Role, User, UserStatus
from scaffold.apps.ssp.models import ADRRecord, ADRStatus, ArchitecturePrinciple, SSPlan
from scaffold.extensions import db
from scaffold.models import AuditLog


def _make_admin(app):
    with app.app_context():
        role = Role()
        role.name = "admin"
        db.session.add(role)

        admin = User()
        admin.email = "admin@example.com"
        admin.status = UserStatus.ACTIVE
        admin.set_password("Password123!")
        admin.roles.append(role)
        db.session.add(admin)
        db.session.commit()


def _login(client, email="admin@example.com", password="Password123!"):
    """Authenticate the test client directly; the password login now forces MFA enrolment."""
    with client.application.app_context():
        token = User.query.filter_by(email=email).one().get_id()
    with client.session_transaction() as sess:
        sess["_user_id"] = token
        sess["_fresh"] = True
        sess["login_time"] = datetime.now(UTC).isoformat()


def _upload(client, payload):
    data = {"data_file": (io.BytesIO(json.dumps(payload).encode("utf-8")), "principles.json")}
    return client.post(
        "/admin/principles",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )


def test_import_creates_then_updates_on_reimport(app, client):
    _make_admin(app)
    _login(client)

    payload = {"principles": [{"name": "Least Privilege", "description": "Grant minimum access."}]}
    response = _upload(client, payload)
    assert response.status_code == 200
    with app.app_context():
        assert ArchitecturePrinciple.query.count() == 1

    payload["principles"][0]["description"] = "Updated description."
    _upload(client, payload)
    with app.app_context():
        assert ArchitecturePrinciple.query.count() == 1
        principle = ArchitecturePrinciple.query.filter_by(name="Least Privilege").first()
        assert principle.description == "Updated description."


def test_import_rejects_invalid_json_file(app, client):
    _make_admin(app)
    _login(client)

    data = {"data_file": (io.BytesIO(b"not json"), "bad.json")}
    response = client.post(
        "/admin/principles",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert ArchitecturePrinciple.query.count() == 0


def test_import_partial_batch_reports_errors_without_aborting(app, client):
    _make_admin(app)
    _login(client)

    payload = {
        "principles": [
            {"name": "Valid Principle", "description": "Ok."},
            {"name": "", "description": "Missing name, should be skipped."},
        ]
    }
    _upload(client, payload)
    with app.app_context():
        assert ArchitecturePrinciple.query.count() == 1
        assert ArchitecturePrinciple.query.first().name == "Valid Principle"


def test_delete_blocked_when_principle_referenced_by_adr(app, client):
    _make_admin(app)
    _login(client)

    with app.app_context():
        admin = User.query.filter_by(email="admin@example.com").first()
        principle = ArchitecturePrinciple(name="In Use Principle", description="x")
        db.session.add(principle)

        scope = ContextScope(name="Test Scope")
        db.session.add(scope)
        db.session.flush()

        ssp = SSPlan(context_scope_id=scope.id)
        db.session.add(ssp)
        db.session.flush()

        adr = ADRRecord(
            ssp_id=ssp.id,
            title="Use a managed database",
            status=ADRStatus.PROPOSED,
            context="ctx",
            decision="dec",
            primary_principle_id=principle.id,
            author_id=admin.id,
        )
        db.session.add(adr)
        db.session.commit()
        principle_id = principle.id

    response = client.post(
        f"/admin/principles/{principle_id}/delete",
        data={f"delete-{principle_id}-principle_id": str(principle_id)},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(ArchitecturePrinciple, principle_id) is not None


def test_non_admin_gets_403(app, client):
    with app.app_context():
        user = User()
        user.email = "user@example.com"
        user.status = UserStatus.ACTIVE
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    _login(client, email="user@example.com", password="Password123!")
    response = client.get("/admin/principles")
    assert response.status_code == 403


def test_create_writes_audit_log_row(app, client):
    _make_admin(app)
    _login(client)

    client.post(
        "/admin/principles/create",
        data={"name": "Audited Principle", "description": "x"},
        follow_redirects=True,
    )

    with app.app_context():
        entry = AuditLog.query.filter_by(event_type="create", target_type="architecture_principle").first()
        assert entry is not None
        assert entry.payload.get("name") == "Audited Principle"


def test_admin_sees_principles_links_in_admin_menu_and_nav(app, client):
    _make_admin(app)
    _login(client)

    html = client.get("/admin/users").get_data(as_text=True)
    assert 'id="nav-principles"' in html
    assert html.count('href="/admin/principles"') >= 2  # nav button + admin menu button


def test_control_owner_does_not_see_nav_principles_button(app, client):
    with app.app_context():
        role = Role()
        role.name = "control_owner"
        db.session.add(role)
        user = User()
        user.email = "owner@example.com"
        user.status = UserStatus.ACTIVE
        user.set_password("Password123!")
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()

    _login(client, email="owner@example.com", password="Password123!")
    response = client.get("/admin/principles")
    assert response.status_code == 200
    assert 'id="nav-principles"' not in response.get_data(as_text=True)


def test_create_and_update_accept_description_over_5000_chars(app, client):
    _make_admin(app)
    _login(client)
    long_text = "x" * 6000

    client.post(
        "/admin/principles/create",
        data={"name": "Long Principle", "description": long_text},
        follow_redirects=True,
    )
    with app.app_context():
        principle = ArchitecturePrinciple.query.filter_by(name="Long Principle").first()
        assert principle is not None
        assert len(principle.description) == 6000
        principle_id = principle.id

    updated_text = "y" * 7000
    client.post(
        f"/admin/principles/{principle_id}/update",
        data={"principle_id": str(principle_id), "name": "Long Principle", "description": updated_text},
        follow_redirects=True,
    )
    with app.app_context():
        assert db.session.get(ArchitecturePrinciple, principle_id).description == updated_text


def test_import_skips_description_over_form_memory_limit(app, client):
    _make_admin(app)
    _login(client)
    # Werkzeug also applies this limit to its ~64 KB multipart read buffer,
    # so it must stay above that or every upload is rejected with a 413.
    app.config["MAX_FORM_MEMORY_SIZE"] = 100_000

    response = _upload(
        client,
        {
            "principles": [
                {"name": "Too Long", "description": "x" * 100_001},
                {"name": "Fits", "description": "x" * 100_000},
            ]
        },
    )
    assert response.status_code == 200
    assert "exceeds 100000 bytes" in response.get_data(as_text=True)
    with app.app_context():
        assert ArchitecturePrinciple.query.filter_by(name="Too Long").first() is None
        assert ArchitecturePrinciple.query.filter_by(name="Fits").first() is not None
