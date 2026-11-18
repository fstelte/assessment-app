"""Admin page for SSP option lists (decision 20261118-1500; Task 4)."""

from __future__ import annotations

from datetime import UTC, datetime

from scaffold.apps.bia.models import ContextScope
from scaffold.apps.identity.models import Role, User, UserStatus
from scaffold.apps.ssp.models import SSPlan, SSPOption, SSPOptionKind
from scaffold.extensions import db
from scaffold.models import AuditLog


def _make_user(app, email, *, admin):
    with app.app_context():
        user = User()
        user.email = email
        user.status = UserStatus.ACTIVE
        user.set_password("Password123!")
        if admin:
            role = Role.query.filter_by(name="admin").first() or Role(name="admin")
            user.roles.append(role)
        db.session.add(user)
        db.session.commit()


def _login(client, email):
    with client.application.app_context():
        token = User.query.filter_by(email=email).one().get_id()
    with client.session_transaction() as sess:
        sess["_user_id"] = token
        sess["_fresh"] = True
        sess["login_time"] = datetime.now(UTC).isoformat()


def _admin(app, client):
    _make_user(app, "admin@example.com", admin=True)
    _login(client, "admin@example.com")


def _create(client, kind, name, description=""):
    return client.post("/admin/ssp-options", data={"kind": kind, "name": name, "description": description})


def _option(app, name):
    with app.app_context():
        option = SSPOption.query.filter_by(name=name).one()
        db.session.expunge(option)
        return option


def test_non_admin_gets_403(app, client):
    _make_user(app, "user@example.com", admin=False)
    _login(client, "user@example.com")

    assert client.get("/admin/ssp-options").status_code == 403
    assert _create(client, "law_regulation", "NIS2").status_code == 403


def test_create_lists_alphabetically_per_kind(app, client):
    _admin(app, client)
    _create(client, "law_regulation", "NIS2", "Network and Information Security")
    _create(client, "law_regulation", "AVG")
    _create(client, "monitoring_frequency", "  Monthly  ")

    page = client.get("/admin/ssp-options").get_data(as_text=True)
    cell = '<td class="px-4 py-2 font-medium">{}</td>'.format
    assert page.index(cell("AVG")) < page.index(cell("NIS2")) < page.index(cell("Monthly"))
    with app.app_context():
        monthly = SSPOption.query.filter_by(kind=SSPOptionKind.MONITORING_FREQUENCY).one()
        assert monthly.name == "Monthly" and monthly.is_active
        assert AuditLog.query.filter_by(event_type="ssp_option_created").count() == 3


def test_duplicate_name_is_case_insensitive_per_kind(app, client):
    _admin(app, client)
    _create(client, "law_regulation", "NIS2")
    response = _create(client, "law_regulation", "nis2")
    assert "An option with this name already exists." in response.get_data(as_text=True)
    _create(client, "monitoring_frequency", "nis2")  # other kind: allowed

    with app.app_context():
        assert SSPOption.query.filter_by(kind=SSPOptionKind.LAW_REGULATION).count() == 1
        assert SSPOption.query.filter_by(kind=SSPOptionKind.MONITORING_FREQUENCY).count() == 1


def test_edit_and_toggle(app, client):
    _admin(app, client)
    _create(client, "law_regulation", "BIO")
    option = _option(app, "BIO")

    client.post(f"/admin/ssp-options/{option.id}", data={"kind": "law_regulation", "name": "BIO 2", "description": "x"})
    client.post(f"/admin/ssp-options/{option.id}/toggle")

    with app.app_context():
        updated = db.session.get(SSPOption, option.id)
        assert (updated.name, updated.description, updated.is_active) == ("BIO 2", "x", False)
        assert AuditLog.query.filter_by(event_type="ssp_option_updated").count() == 1
        assert AuditLog.query.filter_by(event_type="ssp_option_toggled").count() == 1


def test_delete_unused_removes_but_in_use_deactivates(app, client):
    _admin(app, client)
    _create(client, "law_regulation", "Unused")
    _create(client, "law_regulation", "Used law")
    _create(client, "monitoring_frequency", "Used frequency")
    with app.app_context():
        scope = ContextScope(name="System")
        db.session.add(scope)
        db.session.flush()
        ssp = SSPlan(context_scope_id=scope.id)
        ssp.laws_regulations_options = [SSPOption.query.filter_by(name="Used law").one()]
        ssp.monitoring_frequency_option = SSPOption.query.filter_by(name="Used frequency").one()
        db.session.add(ssp)
        db.session.commit()

    for name in ("Unused", "Used law", "Used frequency"):
        client.post(f"/admin/ssp-options/{_option(app, name).id}/delete")

    with app.app_context():
        remaining = {o.name: o.is_active for o in SSPOption.query.all()}
        assert remaining == {"Used law": False, "Used frequency": False}
        assert AuditLog.query.filter_by(event_type="ssp_option_deleted").count() == 1
        ssp = SSPlan.query.one()
        assert [o.name for o in ssp.laws_regulations_options] == ["Used law"]
        assert ssp.monitoring_frequency_option.name == "Used frequency"


def test_hub_links_to_ssp_lists(app, client):
    _admin(app, client)

    page = client.get("/admin/users").get_data(as_text=True)
    assert 'href="/admin/ssp-options"' in page
