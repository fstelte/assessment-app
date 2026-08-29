import io

from PIL import Image

from scaffold.apps.bia.models import ContextScope
from scaffold.apps.identity.models import User, UserStatus
from scaffold.apps.ssp.models import SSPArchitectureOverview, SSPlan
from scaffold.extensions import db
from scaffold.models import AuditLog


def _make_user(app, email="author@example.com"):
    with app.app_context():
        user = User()
        user.email = email
        user.status = UserStatus.ACTIVE
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()


def _login(client, email="author@example.com", password="Password123!"):
    client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def _make_ssp(app):
    with app.app_context():
        scope = ContextScope(name="Test Scope")
        db.session.add(scope)
        db.session.flush()
        ssp = SSPlan(context_scope_id=scope.id)
        db.session.add(ssp)
        db.session.commit()
        return ssp.id


def _png_bytes(size=(10, 10)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=(255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


def _upload(client, ssp_id, filename="overview.png", content=None):
    return client.post(
        f"/ssp/{ssp_id}/architecture-overview",
        data={"image": (io.BytesIO(content or _png_bytes()), filename)},
        content_type="multipart/form-data",
        follow_redirects=True,
    )


def test_upload_becomes_current_version(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    response = _upload(client, ssp_id)
    assert response.status_code == 200
    with app.app_context():
        versions = SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id).all()
        assert len(versions) == 1
        assert versions[0].version_number == 1


def test_second_upload_keeps_first_in_history(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    _upload(client, ssp_id)
    _upload(client, ssp_id)

    with app.app_context():
        versions = SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id).order_by(
            SSPArchitectureOverview.version_number
        ).all()
        assert [v.version_number for v in versions] == [1, 2]


def test_non_image_upload_rejected_and_nothing_persisted(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    response = _upload(client, ssp_id, filename="malware.png", content=b"not an image")
    assert response.status_code == 200
    with app.app_context():
        assert SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id).count() == 0


def test_oversized_upload_rejected_and_nothing_persisted(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    oversized = _png_bytes() + b"\x00" * (6 * 1024 * 1024)
    response = _upload(client, ssp_id, content=oversized)
    assert response.status_code == 200
    with app.app_context():
        assert SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id).count() == 0


def test_restore_creates_new_version_without_mutating_old(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    _upload(client, ssp_id)
    _upload(client, ssp_id)
    with app.app_context():
        first_version = SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id, version_number=1).first()
        first_id, first_bytes = first_version.id, first_version.image_data

    response = client.post(
        f"/ssp/{ssp_id}/architecture-overview/{first_id}/restore",
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        versions = SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id).order_by(
            SSPArchitectureOverview.version_number
        ).all()
        assert [v.version_number for v in versions] == [1, 2, 3]
        assert versions[0].id == first_id
        assert versions[0].image_data == first_bytes
        assert versions[2].image_data == first_bytes


def test_image_route_returns_correct_headers(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)
    _upload(client, ssp_id)

    with app.app_context():
        version_id = SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id).first().id

    response = client.get(f"/ssp/{ssp_id}/architecture-overview/{version_id}/image")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.headers["Content-Disposition"] == "inline"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_ssp_delete_cascades_architecture_overview_versions(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)
    _upload(client, ssp_id)

    with app.app_context():
        db.session.delete(db.session.get(SSPlan, ssp_id))
        db.session.commit()
        assert SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id).count() == 0


def test_upload_and_restore_write_audit_log_rows(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    _upload(client, ssp_id)
    with app.app_context():
        upload_entry = AuditLog.query.filter_by(
            event_type="ssp_architecture_overview_uploaded", target_type="ssp_architecture_overview"
        ).first()
        assert upload_entry is not None
        first_id = SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id).first().id

    client.post(f"/ssp/{ssp_id}/architecture-overview/{first_id}/restore", follow_redirects=True)
    with app.app_context():
        restore_entry = AuditLog.query.filter_by(
            event_type="ssp_architecture_overview_restored", target_type="ssp_architecture_overview"
        ).first()
        assert restore_entry is not None
        assert restore_entry.payload.get("restored_from_version") == 1
