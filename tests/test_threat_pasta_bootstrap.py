"""Bootstrap conversion tests for the PASTA threat modeling feature.

T020 — Bootstrap service and route tests (STRIDE-LM → PASTA)
"""

from __future__ import annotations

import pytest

from scaffold import create_app
from scaffold.apps.identity.models import ROLE_ADMIN, Role, User, UserStatus
from scaffold.apps.threat.models import (
    AssetType,
    Methodology,
    PastaStageStatus,
    PASTA_STAGE_CODES,
    ThreatModel,
    ThreatModelAsset,
)
from scaffold.apps.threat.services import bootstrap_pasta_from_stride, initialize_pasta_stages
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
        user.email = "bootstrap-admin@example.com"
        user.status = UserStatus.ACTIVE
        user.azure_oid = "test-oid-bootstrap-admin"  # bypass MFA enforcement
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


def _stride_model_id(app, owner_id: int | None = None) -> int:
    """Create a STRIDE-LM model with two assets and return its ID."""
    with app.app_context():
        model = ThreatModel(
            title="Source STRIDE Model",
            description="STRIDE base model",
            scope="All services",
            methodology=Methodology.STRIDE.value,
            owner_id=owner_id,
        )
        db.session.add(model)
        db.session.flush()
        db.session.add(ThreatModelAsset(
            threat_model_id=model.id,
            name="Web Server",
            asset_type=AssetType.COMPONENT.value,
            description="Main web server",
            order=0,
        ))
        db.session.add(ThreatModelAsset(
            threat_model_id=model.id,
            name="Database",
            asset_type=AssetType.DATA_STORE.value,
            description="Primary DB",
            order=1,
        ))
        db.session.commit()
        return model.id


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


class TestBootstrapService:
    def test_creates_pasta_model_from_stride(self, app, admin_user):
        with app.app_context():
            owner = User.query.get(admin_user["id"])
            stride_id = _stride_model_id(app, owner_id=admin_user["id"])
            source = ThreatModel.query.get(stride_id)
            new_model = bootstrap_pasta_from_stride(source, owner)
            db.session.commit()

            assert new_model.id is not None
            assert new_model.methodology == Methodology.PASTA.value
            assert new_model.is_pasta

    def test_new_model_copies_title_with_suffix(self, app, admin_user):
        with app.app_context():
            owner = User.query.get(admin_user["id"])
            stride_id = _stride_model_id(app, owner_id=admin_user["id"])
            source = ThreatModel.query.get(stride_id)
            new_model = bootstrap_pasta_from_stride(source, owner)
            db.session.commit()

            assert "PASTA" in new_model.title

    def test_new_model_copies_scope_and_description(self, app, admin_user):
        with app.app_context():
            owner = User.query.get(admin_user["id"])
            stride_id = _stride_model_id(app, owner_id=admin_user["id"])
            source = ThreatModel.query.get(stride_id)
            new_model = bootstrap_pasta_from_stride(source, owner)
            db.session.commit()

            assert new_model.scope == source.scope
            assert new_model.description == source.description

    def test_bootstrap_records_source_model_id(self, app, admin_user):
        with app.app_context():
            owner = User.query.get(admin_user["id"])
            stride_id = _stride_model_id(app, owner_id=admin_user["id"])
            source = ThreatModel.query.get(stride_id)
            new_model = bootstrap_pasta_from_stride(source, owner)
            db.session.commit()

            assert new_model.bootstrap_source_model_id == stride_id

    def test_bootstrap_source_relationship(self, app, admin_user):
        with app.app_context():
            owner = User.query.get(admin_user["id"])
            stride_id = _stride_model_id(app, owner_id=admin_user["id"])
            source = ThreatModel.query.get(stride_id)
            new_model = bootstrap_pasta_from_stride(source, owner)
            db.session.commit()

            new_id = new_model.id
            fetched = ThreatModel.query.get(new_id)
            assert fetched.bootstrap_source is not None
            assert fetched.bootstrap_source.id == stride_id

    def test_bootstrap_copies_assets(self, app, admin_user):
        with app.app_context():
            owner = User.query.get(admin_user["id"])
            stride_id = _stride_model_id(app, owner_id=admin_user["id"])
            source = ThreatModel.query.get(stride_id)
            new_model = bootstrap_pasta_from_stride(source, owner)
            db.session.commit()

            assert len(new_model.assets) == 2
            asset_names = {a.name for a in new_model.assets}
            assert "Web Server" in asset_names
            assert "Database" in asset_names

    def test_bootstrap_assets_are_new_rows(self, app, admin_user):
        """Assets must be independent rows, not shared with the source model."""
        with app.app_context():
            owner = User.query.get(admin_user["id"])
            stride_id = _stride_model_id(app, owner_id=admin_user["id"])
            source = ThreatModel.query.get(stride_id)
            new_model = bootstrap_pasta_from_stride(source, owner)
            db.session.commit()

            source_asset_ids = {a.id for a in source.assets}
            new_asset_ids = {a.id for a in new_model.assets}
            assert not source_asset_ids.intersection(new_asset_ids)

    def test_bootstrap_initializes_7_stages(self, app, admin_user):
        with app.app_context():
            owner = User.query.get(admin_user["id"])
            stride_id = _stride_model_id(app, owner_id=admin_user["id"])
            source = ThreatModel.query.get(stride_id)
            new_model = bootstrap_pasta_from_stride(source, owner)
            db.session.commit()

            assert len(new_model.pasta_stages) == 7

    def test_bootstrap_stage1_available_rest_locked(self, app, admin_user):
        with app.app_context():
            owner = User.query.get(admin_user["id"])
            stride_id = _stride_model_id(app, owner_id=admin_user["id"])
            source = ThreatModel.query.get(stride_id)
            new_model = bootstrap_pasta_from_stride(source, owner)
            db.session.commit()

            stages_by_code = {s.stage_code: s for s in new_model.pasta_stages}
            assert stages_by_code[PASTA_STAGE_CODES[0]].status == PastaStageStatus.AVAILABLE
            for code in PASTA_STAGE_CODES[1:]:
                assert stages_by_code[code].status == PastaStageStatus.LOCKED

    def test_bootstrap_does_not_mutate_source_model(self, app, admin_user):
        with app.app_context():
            owner = User.query.get(admin_user["id"])
            stride_id = _stride_model_id(app, owner_id=admin_user["id"])
            source = ThreatModel.query.get(stride_id)
            source_methodology = source.methodology
            bootstrap_pasta_from_stride(source, owner)
            db.session.commit()

            refetched = ThreatModel.query.get(stride_id)
            assert refetched.methodology == source_methodology
            assert not refetched.is_pasta

    def test_bootstrap_custom_title(self, app, admin_user):
        with app.app_context():
            owner = User.query.get(admin_user["id"])
            stride_id = _stride_model_id(app, owner_id=admin_user["id"])
            source = ThreatModel.query.get(stride_id)
            new_model = bootstrap_pasta_from_stride(source, owner, title="Custom PASTA Title")
            db.session.commit()

            assert new_model.title == "Custom PASTA Title"


# ---------------------------------------------------------------------------
# Route-level tests
# ---------------------------------------------------------------------------


class TestBootstrapRoute:
    def test_bootstrap_route_creates_pasta_model(self, client, app, admin_user):
        stride_id = _stride_model_id(app, owner_id=admin_user["id"])
        _login(client, admin_user["email"])
        resp = client.post(
            f"/threat/{stride_id}/bootstrap-pasta",
            follow_redirects=False,
        )
        assert resp.status_code == 302
        with app.app_context():
            pasta_model = ThreatModel.query.filter(
                ThreatModel.methodology == Methodology.PASTA.value,
                ThreatModel.bootstrap_source_model_id == stride_id,
            ).first()
            assert pasta_model is not None

    def test_bootstrap_route_redirects_to_new_model_detail(self, client, app, admin_user):
        stride_id = _stride_model_id(app, owner_id=admin_user["id"])
        _login(client, admin_user["email"])
        resp = client.post(
            f"/threat/{stride_id}/bootstrap-pasta",
            follow_redirects=False,
        )
        assert resp.status_code == 302
        location = resp.headers.get("Location", "")
        assert "/threat/" in location

    def test_bootstrap_route_logs_audit_event(self, client, app, admin_user):
        from scaffold.models import AuditLog
        stride_id = _stride_model_id(app, owner_id=admin_user["id"])
        _login(client, admin_user["email"])
        client.post(
            f"/threat/{stride_id}/bootstrap-pasta",
            follow_redirects=True,
        )
        with app.app_context():
            event = AuditLog.query.filter_by(
                event_type="pasta_model_bootstrapped",
            ).first()
            assert event is not None

    def test_bootstrap_archived_model_returns_404(self, client, app, admin_user):
        stride_id = _stride_model_id(app, owner_id=admin_user["id"])
        with app.app_context():
            model = ThreatModel.query.get(stride_id)
            model.is_archived = True
            db.session.commit()
        _login(client, admin_user["email"])
        resp = client.post(f"/threat/{stride_id}/bootstrap-pasta")
        assert resp.status_code == 404
