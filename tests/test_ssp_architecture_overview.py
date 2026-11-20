import io
from datetime import UTC, datetime

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
    """Authenticate the test client directly; the password login now forces MFA enrolment."""
    with client.application.app_context():
        token = User.query.filter_by(email=email).one().get_id()
    with client.session_transaction() as sess:
        sess["_user_id"] = token
        sess["_fresh"] = True
        sess["login_time"] = datetime.now(UTC).isoformat()


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


def test_second_upload_keeps_both_files(app, client):
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

    oversized = _png_bytes() + b"\x00" * (11 * 1024 * 1024)
    response = _upload(client, ssp_id, content=oversized)
    assert response.status_code == 200
    with app.app_context():
        assert SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id).count() == 0


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


def test_upload_writes_audit_log_row(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    _upload(client, ssp_id)
    with app.app_context():
        upload_entry = AuditLog.query.filter_by(
            event_type="ssp_architecture_overview_uploaded", target_type="ssp_architecture_overview"
        ).first()
        assert upload_entry is not None


_PDF_BYTES = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"


def _flashes(client):
    with client.session_transaction() as sess:
        return [message for _category, message in sess.get("_flashes", [])]


def _upload_no_follow(client, ssp_id, filename, content, mimetype=None):
    file_tuple = (io.BytesIO(content), filename, mimetype) if mimetype else (io.BytesIO(content), filename)
    return client.post(
        f"/ssp/{ssp_id}/architecture-overview",
        data={"image": file_tuple},
        content_type="multipart/form-data",
    )


def test_pdf_upload_is_stored_and_downloaded_as_attachment(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    _upload(client, ssp_id, filename="My Diagram.PDF", content=_PDF_BYTES)
    with app.app_context():
        version = SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id).one()
        assert version.mime_type == "application/pdf"
        assert version.original_filename == "my_diagram.pdf"
        version_id = version.id

    page = client.get(f"/ssp/{ssp_id}")
    assert b"Download PDF" in page.data
    assert f"/ssp/{ssp_id}/architecture-overview/{version_id}/image".encode() in page.data

    response = client.get(f"/ssp/{ssp_id}/architecture-overview/{version_id}/image")
    assert response.mimetype == "application/pdf"
    assert response.headers["Content-Disposition"] == 'attachment; filename="my_diagram.pdf"'
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_renamed_non_pdf_rejected_with_invalid_pdf_message(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    _upload_no_follow(client, ssp_id, "report.pdf", b"just text")
    assert "The file is not a valid PDF." in _flashes(client)
    with app.app_context():
        assert SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id).count() == 0


def test_svg_rejected_with_invalid_type_message(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    _upload_no_follow(client, ssp_id, "diagram.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>")
    assert any(message.startswith("Only PNG, JPEG or PDF") for message in _flashes(client))
    with app.app_context():
        assert SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id).count() == 0


def test_oversized_upload_names_the_size_limit(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    _upload_no_follow(client, ssp_id, "big.pdf", _PDF_BYTES + b"\x00" * (11 * 1024 * 1024))
    assert "The file must be 10 MB or smaller." in _flashes(client)


def test_image_mime_type_is_detected_not_taken_from_browser(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    _upload_no_follow(client, ssp_id, "overview.png", _png_bytes(), mimetype="application/octet-stream")
    with app.app_context():
        version = SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id).one()
        assert version.mime_type == "image/png"


def test_upload_form_explains_what_can_be_uploaded(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    page = client.get(f"/ssp/{ssp_id}").get_data(as_text=True)
    assert 'accept=".png,.jpg,.jpeg,.pdf"' in page
    assert "PNG, JPEG or PDF, max 10 MB" in page


def _version_numbers(app, ssp_id):
    with app.app_context():
        return [
            v.version_number
            for v in SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id)
            .order_by(SSPArchitectureOverview.version_number)
            .all()
        ]


def _version_id(app, ssp_id, number):
    with app.app_context():
        return SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id, version_number=number).one().id


def test_delete_current_version_makes_previous_current(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)
    _upload(client, ssp_id)
    _upload(client, ssp_id, filename="second.png")

    response = client.post(f"/ssp/{ssp_id}/architecture-overview/{_version_id(app, ssp_id, 2)}/delete")
    assert response.status_code == 302
    assert _version_numbers(app, ssp_id) == [1]

    page = client.get(f"/ssp/{ssp_id}").get_data(as_text=True)
    assert f"/ssp/{ssp_id}/architecture-overview/{_version_id(app, ssp_id, 1)}/image" in page

    # Next upload uses max(remaining) + 1, so the deleted number 2 is reused.
    _upload(client, ssp_id, filename="third.png")
    assert _version_numbers(app, ssp_id) == [1, 2]


def test_delete_only_version_shows_none_uploaded(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)
    _upload(client, ssp_id)

    client.post(f"/ssp/{ssp_id}/architecture-overview/{_version_id(app, ssp_id, 1)}/delete")
    assert _version_numbers(app, ssp_id) == []
    page = client.get(f"/ssp/{ssp_id}").get_data(as_text=True)
    assert "No architecture overview has been uploaded yet." in page


def test_delete_version_of_other_ssp_returns_404(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)
    _upload(client, ssp_id)
    with app.app_context():
        scope = ContextScope(name="Other Scope")
        db.session.add(scope)
        db.session.flush()
        other = SSPlan(context_scope_id=scope.id)
        db.session.add(other)
        db.session.commit()
        other_id = other.id

    response = client.post(f"/ssp/{other_id}/architecture-overview/{_version_id(app, ssp_id, 1)}/delete")
    assert response.status_code == 404
    assert _version_numbers(app, ssp_id) == [1]


def test_delete_version_writes_audit_log(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)
    _upload(client, ssp_id, filename="overview.png")
    version_id = _version_id(app, ssp_id, 1)

    client.post(f"/ssp/{ssp_id}/architecture-overview/{version_id}/delete")
    with app.app_context():
        entry = AuditLog.query.filter_by(
            event_type="ssp_architecture_overview_deleted", target_type="ssp_architecture_overview"
        ).one()
        assert entry.payload.get("version_number") == 1
        assert entry.payload.get("original_filename") == "overview.png"
