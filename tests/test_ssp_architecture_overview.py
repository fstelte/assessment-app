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


def _upload(client, ssp_id, filename="overview.png", content=None, files=None):
    """Upload one file, or several when ``files`` is a list of ``(filename, bytes)``."""
    files = files if files is not None else [(filename, content or _png_bytes())]
    return client.post(
        f"/ssp/{ssp_id}/architecture-overview",
        data={"files": [(io.BytesIO(data), name) for name, data in files]},
        content_type="multipart/form-data",
        follow_redirects=True,
    )


def _filenames(app, ssp_id):
    with app.app_context():
        return [
            f.original_filename
            for f in SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id).order_by(SSPArchitectureOverview.id)
        ]


def _file_id(app, ssp_id, filename):
    with app.app_context():
        return SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id, original_filename=filename).one().id


def test_upload_stores_one_file(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    response = _upload(client, ssp_id)
    assert response.status_code == 200
    assert _filenames(app, ssp_id) == ["overview.png"]


def test_second_upload_keeps_both_files(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    _upload(client, ssp_id)
    _upload(client, ssp_id, filename="second.png")

    assert _filenames(app, ssp_id) == ["overview.png", "second.png"]


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
        ).one()
        assert upload_entry.payload == {"ssp_id": ssp_id, "original_filename": "overview.png"}


_PDF_BYTES = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"


def _flashes(client):
    with client.session_transaction() as sess:
        return [message for _category, message in sess.get("_flashes", [])]


def _upload_no_follow(client, ssp_id, filename, content, mimetype=None):
    file_tuple = (io.BytesIO(content), filename, mimetype) if mimetype else (io.BytesIO(content), filename)
    return client.post(
        f"/ssp/{ssp_id}/architecture-overview",
        data={"files": file_tuple},
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
    assert "report.pdf: The file is not a valid PDF." in _flashes(client)
    with app.app_context():
        assert SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id).count() == 0


def test_svg_rejected_with_invalid_type_message(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    _upload_no_follow(client, ssp_id, "diagram.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>")
    assert any(message.startswith("diagram.svg: Only PNG, JPEG or PDF") for message in _flashes(client))
    with app.app_context():
        assert SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id).count() == 0


def test_oversized_upload_names_the_size_limit(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    _upload_no_follow(client, ssp_id, "big.pdf", _PDF_BYTES + b"\x00" * (11 * 1024 * 1024))
    assert "big.pdf: The file must be 10 MB or smaller." in _flashes(client)


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


def _image_url(ssp_id, file_id):
    return f"/ssp/{ssp_id}/architecture-overview/{file_id}/image"


def test_all_files_are_shown_oldest_first(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)
    _upload(client, ssp_id, filename="context.png")
    _upload(client, ssp_id, filename="network.png")
    # Give the later row an earlier upload time: the order must follow uploaded_at, not id.
    with app.app_context():
        network = SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id, original_filename="network.png").one()
        network.uploaded_at = datetime(2020, 1, 1, tzinfo=UTC)
        db.session.commit()
    context_id, network_id = _file_id(app, ssp_id, "context.png"), _file_id(app, ssp_id, "network.png")

    page = client.get(f"/ssp/{ssp_id}").get_data(as_text=True)
    assert page.count("data-architecture-overview-file") == 2
    assert page.index(_image_url(ssp_id, network_id)) < page.index(_image_url(ssp_id, context_id))
    for file_id in (context_id, network_id):
        assert f"/ssp/{ssp_id}/architecture-overview/{file_id}/delete" in page
    assert 'Delete &#34;context.png&#34;? This cannot be undone.' in page


def test_delete_one_file_keeps_the_others(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)
    _upload(client, ssp_id)
    _upload(client, ssp_id, filename="second.png")

    response = client.post(f"/ssp/{ssp_id}/architecture-overview/{_file_id(app, ssp_id, 'second.png')}/delete")
    assert response.status_code == 302
    assert _filenames(app, ssp_id) == ["overview.png"]

    page = client.get(f"/ssp/{ssp_id}").get_data(as_text=True)
    assert _image_url(ssp_id, _file_id(app, ssp_id, "overview.png")) in page
    assert page.count("data-architecture-overview-file") == 1


def test_overview_images_are_lazy_loaded(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)
    _upload(client, ssp_id)

    page = client.get(f"/ssp/{ssp_id}").get_data(as_text=True)
    assert 'loading="lazy"' in page
    assert 'decoding="async"' in page
    assert 'alt="Architecture overview: overview.png"' in page


def test_delete_only_version_shows_none_uploaded(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)
    _upload(client, ssp_id)

    client.post(f"/ssp/{ssp_id}/architecture-overview/{_file_id(app, ssp_id, 'overview.png')}/delete")
    assert _filenames(app, ssp_id) == []
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

    response = client.post(f"/ssp/{other_id}/architecture-overview/{_file_id(app, ssp_id, 'overview.png')}/delete")
    assert response.status_code == 404
    assert _filenames(app, ssp_id) == ["overview.png"]


def test_delete_version_writes_audit_log(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)
    _upload(client, ssp_id, filename="overview.png")
    version_id = _file_id(app, ssp_id, 'overview.png')

    client.post(f"/ssp/{ssp_id}/architecture-overview/{version_id}/delete")
    with app.app_context():
        entry = AuditLog.query.filter_by(
            event_type="ssp_architecture_overview_deleted", target_type="ssp_architecture_overview"
        ).one()
        assert "version_number" not in entry.payload
        assert entry.payload.get("original_filename") == "overview.png"


# --- Multi-file upload, all or nothing (Task 4) ----------------------------------


def test_upload_several_files_stores_each_in_order_with_audit(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    response = _upload(client, ssp_id, files=[("c.png", _png_bytes()), ("a.png", _png_bytes()), ("b.png", _png_bytes())])
    assert response.status_code == 200
    assert "3 file(s) uploaded." in response.get_data(as_text=True)
    assert _filenames(app, ssp_id) == ["c.png", "a.png", "b.png"]
    with app.app_context():
        entries = AuditLog.query.filter_by(event_type="ssp_architecture_overview_uploaded").all()
        assert sorted(e.payload["original_filename"] for e in entries) == ["a.png", "b.png", "c.png"]


def test_one_invalid_file_blocks_the_whole_batch(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    client.post(
        f"/ssp/{ssp_id}/architecture-overview",
        data={"files": [
            (io.BytesIO(_png_bytes()), "context.png"),
            (io.BytesIO(b"<svg xmlns='http://www.w3.org/2000/svg'/>"), "network.svg"),
            (io.BytesIO(_PDF_BYTES), "flow.pdf"),
        ]},
        content_type="multipart/form-data",
    )
    messages = _flashes(client)
    assert any(message.startswith("network.svg: Only PNG, JPEG or PDF") for message in messages)
    assert not any(message.startswith(("context.png", "flow.pdf")) for message in messages)
    assert _filenames(app, ssp_id) == []
    with app.app_context():
        assert AuditLog.query.filter_by(event_type="ssp_architecture_overview_uploaded").count() == 0


def test_png_and_pdf_together_keep_their_detected_types(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    _upload(client, ssp_id, files=[("context.png", _png_bytes()), ("flow.pdf", _PDF_BYTES)])
    with app.app_context():
        rows = SSPArchitectureOverview.query.filter_by(ssp_id=ssp_id).order_by(SSPArchitectureOverview.id).all()
        assert [(r.original_filename, r.mime_type) for r in rows] == [
            ("context.png", "image/png"),
            ("flow.pdf", "application/pdf"),
        ]


def test_empty_submit_reports_required(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    client.post(
        f"/ssp/{ssp_id}/architecture-overview",
        data={"files": (io.BytesIO(b""), "")},
        content_type="multipart/form-data",
    )
    assert "Please choose a file to upload." in _flashes(client)
    assert _filenames(app, ssp_id) == []


def test_named_zero_byte_png_is_rejected_as_invalid_image(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    _upload_no_follow(client, ssp_id, "empty.png", b"")
    assert "empty.png: The file is not a valid PNG or JPEG image." in _flashes(client)
    assert _filenames(app, ssp_id) == []


def test_upload_form_carries_the_batch_size_limit_for_the_browser_check(app, client):
    _make_user(app)
    _login(client)
    ssp_id = _make_ssp(app)

    page = client.get(f"/ssp/{ssp_id}").get_data(as_text=True)
    assert 'data-max-total-bytes="100000000"' in page
    assert "The selected files are larger than 100 MB in total." in page
    assert "data-max-total-error" in page
