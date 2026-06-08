"""Finding-level STRIDE-LM mapping and context reuse tests for PASTA.

T021 — STRIDE-LM mapping persistence tests
"""

from __future__ import annotations

import pytest

from scaffold import create_app
from scaffold.apps.identity.models import ROLE_ADMIN, Role, User, UserStatus
from scaffold.apps.threat.models import (
    AssetType,
    Methodology,
    PastaFinding,
    PastaFindingStatus,
    PastaFindingStrideCategoryLink,
    PastaFindingType,
    PastaStageStatus,
    PASTA_STAGE_CODES,
    StrideCategory,
    ThreatModel,
    ThreatModelAsset,
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
        user.email = "mapping-admin@example.com"
        user.status = UserStatus.ACTIVE
        user.azure_oid = "test-oid-mapping-admin"  # bypass MFA enforcement
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


def _pasta_model_with_stage1_available(app) -> int:
    """Create a PASTA model with stage 1 available and return its ID."""
    with app.app_context():
        model = ThreatModel(
            title="Mapping Test Model",
            methodology=Methodology.PASTA.value,
        )
        db.session.add(model)
        db.session.flush()
        # Add an asset for link tests
        db.session.add(ThreatModelAsset(
            threat_model_id=model.id,
            name="Payment API",
            asset_type=AssetType.EXTERNAL_ENTITY.value,
            order=0,
        ))
        initialize_pasta_stages(model)
        db.session.commit()
        return model.id


def _stage1_with_finding(app, model_id: int) -> tuple[int, int]:
    """Add a finding to stage 1 and return (stage_id, finding_id)."""
    with app.app_context():
        model = ThreatModel.query.get(model_id)
        stage = next(s for s in model.pasta_stages if s.stage_code == PASTA_STAGE_CODES[0])
        finding = PastaFinding(
            stage_record_id=stage.id,
            finding_type=PastaFindingType.SCOPE_ITEM,
            title="Test Finding",
            description="A finding for mapping tests",
            status=PastaFindingStatus.CURRENT,
        )
        db.session.add(finding)
        db.session.commit()
        return stage.id, finding.id


# ---------------------------------------------------------------------------
# STRIDE-LM mapping persistence (service/model level)
# ---------------------------------------------------------------------------


class TestFindingStrideMappingPersistence:
    def test_finding_can_have_no_stride_mappings(self, app):
        model_id = _pasta_model_with_stage1_available(app)
        _, finding_id = _stage1_with_finding(app, model_id)
        with app.app_context():
            finding = PastaFinding.query.get(finding_id)
            assert finding.stride_links == []

    def test_adding_stride_mapping_to_finding(self, app):
        model_id = _pasta_model_with_stage1_available(app)
        _, finding_id = _stage1_with_finding(app, model_id)
        with app.app_context():
            finding = PastaFinding.query.get(finding_id)
            link = PastaFindingStrideCategoryLink(
                finding_id=finding.id,
                stride_category=StrideCategory.SPOOFING.value,
            )
            db.session.add(link)
            db.session.commit()

        with app.app_context():
            finding = PastaFinding.query.get(finding_id)
            assert len(finding.stride_links) == 1
            assert finding.stride_links[0].stride_category == StrideCategory.SPOOFING.value

    def test_finding_can_have_multiple_stride_mappings(self, app):
        model_id = _pasta_model_with_stage1_available(app)
        _, finding_id = _stage1_with_finding(app, model_id)
        with app.app_context():
            finding = PastaFinding.query.get(finding_id)
            for cat in [StrideCategory.SPOOFING.value, StrideCategory.TAMPERING.value, StrideCategory.ELEVATION_OF_PRIVILEGE.value]:
                db.session.add(PastaFindingStrideCategoryLink(
                    finding_id=finding.id,
                    stride_category=cat,
                ))
            db.session.commit()

        with app.app_context():
            finding = PastaFinding.query.get(finding_id)
            assert len(finding.stride_links) == 3

    def test_stride_mapping_cascades_delete_with_finding(self, app):
        """Deleting a finding removes its STRIDE category links."""
        model_id = _pasta_model_with_stage1_available(app)
        _, finding_id = _stage1_with_finding(app, model_id)
        with app.app_context():
            finding = PastaFinding.query.get(finding_id)
            db.session.add(PastaFindingStrideCategoryLink(
                finding_id=finding.id,
                stride_category=StrideCategory.SPOOFING.value,
            ))
            db.session.commit()
            # Now delete the finding
            db.session.delete(finding)
            db.session.commit()

        with app.app_context():
            links = PastaFindingStrideCategoryLink.query.filter_by(
                finding_id=finding_id
            ).all()
            assert links == []

    def test_finding_without_stride_mapping_is_valid(self, app):
        """Findings without STRIDE mappings should be persisted without error."""
        model_id = _pasta_model_with_stage1_available(app)
        _, finding_id = _stage1_with_finding(app, model_id)
        with app.app_context():
            finding = PastaFinding.query.get(finding_id)
            assert finding is not None
            assert finding.stride_links == []


# ---------------------------------------------------------------------------
# Route-level: creating findings with STRIDE mappings
# ---------------------------------------------------------------------------


class TestFindingWithStrideMappingRoute:
    def test_create_finding_with_stride_categories_via_route(self, client, app, admin_user):
        model_id = _pasta_model_with_stage1_available(app)
        stage_code = PASTA_STAGE_CODES[0]
        _login(client, admin_user["email"])
        resp = client.post(
            f"/threat/{model_id}/pasta/stages/{stage_code}/findings",
            data={
                "finding_type": PastaFindingType.SCOPE_ITEM.value,
                "title": "Route STRIDE Mapped Finding",
                "description": "Found via route",
                "stride_category_values": [
                    StrideCategory.SPOOFING.value,
                    StrideCategory.INFORMATION_DISCLOSURE.value,
                ],
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            finding = PastaFinding.query.filter_by(
                title="Route STRIDE Mapped Finding"
            ).first()
            assert finding is not None
            assert len(finding.stride_links) == 2

    def test_create_finding_without_stride_mappings_via_route(self, client, app, admin_user):
        model_id = _pasta_model_with_stage1_available(app)
        stage_code = PASTA_STAGE_CODES[0]
        _login(client, admin_user["email"])
        resp = client.post(
            f"/threat/{model_id}/pasta/stages/{stage_code}/findings",
            data={
                "finding_type": PastaFindingType.SCOPE_ITEM.value,
                "title": "No STRIDE Mapping Finding",
                "description": "No STRIDE context needed",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            finding = PastaFinding.query.filter_by(
                title="No STRIDE Mapping Finding"
            ).first()
            assert finding is not None
            assert finding.stride_links == []

    def test_create_finding_with_asset_links_via_route(self, client, app, admin_user):
        model_id = _pasta_model_with_stage1_available(app)
        with app.app_context():
            asset = ThreatModelAsset.query.filter_by(
                threat_model_id=model_id, name="Payment API"
            ).first()
            asset_id = asset.id

        stage_code = PASTA_STAGE_CODES[0]
        _login(client, admin_user["email"])
        resp = client.post(
            f"/threat/{model_id}/pasta/stages/{stage_code}/findings",
            data={
                "finding_type": PastaFindingType.SCOPE_ITEM.value,
                "title": "Asset-Linked Finding",
                "description": "This finding references an asset",
                "asset_ids": [str(asset_id)],
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            finding = PastaFinding.query.filter_by(
                title="Asset-Linked Finding"
            ).first()
            assert finding is not None
            assert len(finding.asset_links) == 1
            assert finding.asset_links[0].asset_id == asset_id

    def test_mixed_findings_with_and_without_stride(self, client, app, admin_user):
        """Multiple findings in the same stage can mix STRIDE-mapped and non-mapped."""
        model_id = _pasta_model_with_stage1_available(app)
        stage_code = PASTA_STAGE_CODES[0]
        _login(client, admin_user["email"])
        # First finding with STRIDE mapping
        client.post(
            f"/threat/{model_id}/pasta/stages/{stage_code}/findings",
            data={
                "finding_type": PastaFindingType.SCOPE_ITEM.value,
                "title": "Mapped Finding",
                "stride_category_values": [StrideCategory.TAMPERING.value],
            },
            follow_redirects=True,
        )
        # Second finding without
        client.post(
            f"/threat/{model_id}/pasta/stages/{stage_code}/findings",
            data={
                "finding_type": PastaFindingType.THREAT.value,
                "title": "Unmapped Finding",
            },
            follow_redirects=True,
        )
        with app.app_context():
            mapped = PastaFinding.query.filter_by(title="Mapped Finding").first()
            unmapped = PastaFinding.query.filter_by(title="Unmapped Finding").first()
            assert mapped is not None and len(mapped.stride_links) == 1
            assert unmapped is not None and unmapped.stride_links == []
