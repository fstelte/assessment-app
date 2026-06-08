"""Methodology-aware export tests for the PASTA threat modeling feature.

T026 — HTML/PDF/CSV export permission and rendering tests
"""

from __future__ import annotations

import pytest

from scaffold import create_app
from scaffold.apps.identity.models import ROLE_ADMIN, Role, User, UserStatus
from scaffold.apps.threat.models import (
    AssetType,
    Methodology,
    PastaFinding,
    PastaFindingType,
    PastaStageStatus,
    PASTA_STAGE_CODES,
    ThreatModel,
)
from scaffold.apps.threat.services import initialize_pasta_stages
from scaffold.config import Settings
from scaffold.extensions import db

_PASSWORD = "Password123!"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    settings = Settings(
        secret_key="test-secret",
        database_url="sqlite:///:memory:",
        session_cookie_secure=False,
        session_cookie_httponly=True,
        session_cookie_samesite="Lax",
        audit_log_retention_days=0,
        app_modules=[
            "scaffold.apps.auth.routes",
            "scaffold.apps.admin",
            "scaffold.apps.bia",
            "scaffold.apps.csa",
            "scaffold.apps.risk",
            "scaffold.apps.ssp",
            "scaffold.apps.template",
            "scaffold.apps.threat",
        ],
        password_login_enabled=True,
    )
    flask_app = create_app(settings)
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    with app.app_context():
        role = Role.query.filter_by(name=ROLE_ADMIN).first()
        if role is None:
            role = Role(name=ROLE_ADMIN)
            db.session.add(role)
        user = User()
        user.email = "export-admin@example.com"
        user.status = UserStatus.ACTIVE
        user.azure_oid = "test-oid-export-admin"  # bypass MFA enforcement
        user.set_password(_PASSWORD)
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        email = user.email
    return {"id": user_id, "email": email}


def _login(client, email: str, password: str = _PASSWORD):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def _pasta_model_with_findings(app) -> int:
    """Create a PASTA model with a finding in stage 1 and return model ID."""
    with app.app_context():
        model = ThreatModel(
            title="Export Test PASTA Model",
            methodology=Methodology.PASTA.value,
            description="A model for export testing",
            scope="All services",
        )
        db.session.add(model)
        db.session.flush()
        initialize_pasta_stages(model)
        stage = next(s for s in model.pasta_stages if s.stage_code == PASTA_STAGE_CODES[0])
        stage.summary = "Stage 1 summary content"
        db.session.add(PastaFinding(
            stage_record_id=stage.id,
            finding_type=PastaFindingType.OBJECTIVE,
            title="Business Objective 1",
            description="Protect customer PII",
        ))
        db.session.commit()
        return model.id


def _stride_model_with_scenarios(app) -> int:
    """Create a plain STRIDE model and return its ID."""
    with app.app_context():
        model = ThreatModel(
            title="STRIDE Export Model",
            methodology=Methodology.STRIDE.value,
        )
        db.session.add(model)
        db.session.commit()
        return model.id


# ---------------------------------------------------------------------------
# CSV Export
# ---------------------------------------------------------------------------


class TestCSVExport:
    def test_pasta_model_csv_export_returns_200(self, client, app, admin_user):
        model_id = _pasta_model_with_findings(app)
        _login(client, admin_user["email"])
        resp = client.get(f"/threat/{model_id}/export/csv")
        assert resp.status_code == 200

    def test_pasta_csv_content_type(self, client, app, admin_user):
        model_id = _pasta_model_with_findings(app)
        _login(client, admin_user["email"])
        resp = client.get(f"/threat/{model_id}/export/csv")
        assert "text/csv" in resp.content_type

    def test_pasta_csv_contains_finding_columns(self, client, app, admin_user):
        model_id = _pasta_model_with_findings(app)
        _login(client, admin_user["email"])
        resp = client.get(f"/threat/{model_id}/export/csv")
        body = resp.data.decode("utf-8")
        # Headers row
        assert "stage" in body
        assert "finding_type" in body
        assert "title" in body

    def test_pasta_csv_contains_finding_data(self, client, app, admin_user):
        model_id = _pasta_model_with_findings(app)
        _login(client, admin_user["email"])
        resp = client.get(f"/threat/{model_id}/export/csv")
        body = resp.data.decode("utf-8")
        assert "Business Objective 1" in body

    def test_csv_export_requires_login(self, client, app, admin_user):
        model_id = _pasta_model_with_findings(app)
        resp = client.get(f"/threat/{model_id}/export/csv")
        assert resp.status_code == 302
        location = resp.headers.get("Location", "")
        assert "login" in location.lower()

    def test_stride_model_csv_export_still_works(self, client, app, admin_user):
        """Ensure non-PASTA models still export correctly after PASTA branching."""
        model_id = _stride_model_with_scenarios(app)
        _login(client, admin_user["email"])
        resp = client.get(f"/threat/{model_id}/export/csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type


# ---------------------------------------------------------------------------
# HTML Export
# ---------------------------------------------------------------------------


class TestHTMLExport:
    def test_pasta_model_html_export_returns_200(self, client, app, admin_user):
        model_id = _pasta_model_with_findings(app)
        _login(client, admin_user["email"])
        resp = client.get(f"/threat/{model_id}/export/html")
        assert resp.status_code == 200

    def test_pasta_html_export_uses_pasta_template(self, client, app, admin_user):
        """PASTA model HTML export should mention PASTA methodology."""
        model_id = _pasta_model_with_findings(app)
        _login(client, admin_user["email"])
        resp = client.get(f"/threat/{model_id}/export/html")
        body = resp.data.decode("utf-8")
        assert "PASTA" in body

    def test_pasta_html_export_includes_model_title(self, client, app, admin_user):
        model_id = _pasta_model_with_findings(app)
        _login(client, admin_user["email"])
        resp = client.get(f"/threat/{model_id}/export/html")
        body = resp.data.decode("utf-8")
        assert "Export Test PASTA Model" in body

    def test_pasta_html_export_includes_stage_content(self, client, app, admin_user):
        model_id = _pasta_model_with_findings(app)
        _login(client, admin_user["email"])
        resp = client.get(f"/threat/{model_id}/export/html")
        body = resp.data.decode("utf-8")
        assert "Stage 1 summary content" in body

    def test_pasta_html_export_includes_findings(self, client, app, admin_user):
        model_id = _pasta_model_with_findings(app)
        _login(client, admin_user["email"])
        resp = client.get(f"/threat/{model_id}/export/html")
        body = resp.data.decode("utf-8")
        assert "Business Objective 1" in body

    def test_html_export_requires_login(self, client, app, admin_user):
        model_id = _pasta_model_with_findings(app)
        resp = client.get(f"/threat/{model_id}/export/html")
        assert resp.status_code == 302

    def test_stride_html_export_still_works(self, client, app, admin_user):
        model_id = _stride_model_with_scenarios(app)
        _login(client, admin_user["email"])
        resp = client.get(f"/threat/{model_id}/export/html")
        assert resp.status_code == 200
