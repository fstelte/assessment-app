"""Tests for the System Security Plan module."""

from __future__ import annotations

import pytest

from scaffold.apps.bia.models import Component, ContextScope, Consequences
from scaffold.apps.csa.models import Control
from scaffold.apps.identity.models import User, UserStatus
from scaffold.apps.ssp.models import SSPlan, SSPControlEntry, SSPInterconnection
from scaffold.apps.ssp.services import derive_fips_rating
from scaffold.extensions import db

_PASSWORD = "Password123!"


@pytest.fixture
def app(app):
    """Extend the base app fixture to include the SSP module."""
    return app


@pytest.fixture
def ssp_app():
    from scaffold.config import Settings
    from scaffold import create_app

    settings = Settings(
        secret_key="test-secret",
        database_url="sqlite:///:memory:",
        session_cookie_secure=False,
        session_cookie_httponly=True,
        session_cookie_samesite="Lax",
        app_modules=[
            "scaffold.apps.auth.routes",
            "scaffold.apps.bia",
            "scaffold.apps.csa",
            "scaffold.apps.dpia",
            "scaffold.apps.risk.api",
            "scaffold.apps.risk.routes",
            "scaffold.apps.threat",
            "scaffold.apps.ssp",
        ],
        password_login_enabled=True,
    )
    app = create_app(settings)
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def ssp_client(ssp_app):
    return ssp_app.test_client()


@pytest.fixture
def logged_in_user(ssp_app, ssp_client):
    with ssp_app.app_context():
        user = User()
        user.email = "ssp-user@example.com"
        user.status = UserStatus.ACTIVE
        user.set_password(_PASSWORD)
        db.session.add(user)
        db.session.commit()

    ssp_client.post(
        "/auth/login",
        data={"email": "ssp-user@example.com", "password": _PASSWORD},
        follow_redirects=True,
    )
    return ssp_client


@pytest.fixture
def scope_with_ssp(ssp_app, logged_in_user):
    """Create a ContextScope and an SSP for it, return (scope_id, ssp_id)."""
    with ssp_app.app_context():
        scope = ContextScope(
            name="Test System",
            abbreviation="TST",
            operational_status="operational",
            system_type="major_application",
        )
        db.session.add(scope)
        db.session.commit()
        scope_id = scope.id

    resp = logged_in_user.post(f"/ssp/create/{scope_id}", follow_redirects=False)
    assert resp.status_code == 302

    with ssp_app.app_context():
        ssp = SSPlan.query.filter_by(context_scope_id=scope_id).first()
        assert ssp is not None
        return scope_id, ssp.id


# ---------------------------------------------------------------------------
# Unit tests — derive_fips_rating
# ---------------------------------------------------------------------------


class _FakeConsequence:
    def __init__(self, security_property, worstcase):
        self.security_property = security_property
        self.consequence_worstcase = worstcase


def test_derive_fips_rating_defaults_to_low():
    result = derive_fips_rating([])
    assert result == {"confidentiality": "low", "integrity": "low", "availability": "low"}


def test_derive_fips_rating_maps_moderate():
    conseqs = [
        _FakeConsequence("Confidentiality", "Moderate"),
        _FakeConsequence("Integrity", "Low"),
        _FakeConsequence("Availability", "Significant"),
    ]
    result = derive_fips_rating(conseqs)
    assert result["confidentiality"] == "moderate"
    assert result["integrity"] == "low"
    assert result["availability"] == "high"


def test_derive_fips_rating_returns_highest():
    """When multiple records exist for a property the highest rating wins."""
    conseqs = [
        _FakeConsequence("Confidentiality", "Low"),
        _FakeConsequence("Confidentiality", "Severe"),
    ]
    result = derive_fips_rating(conseqs)
    assert result["confidentiality"] == "high"


def test_derive_fips_rating_unknown_scale_ignored():
    conseqs = [_FakeConsequence("Confidentiality", "Unknown value")]
    result = derive_fips_rating(conseqs)
    assert result["confidentiality"] == "low"


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


def test_ssp_index_requires_login(ssp_client):
    resp = ssp_client.get("/ssp/", follow_redirects=False)
    assert resp.status_code in (302, 401)


def test_ssp_index_renders(logged_in_user):
    resp = logged_in_user.get("/ssp/")
    assert resp.status_code == 200
    assert b"System Security Plan" in resp.data


def test_ssp_create_for_scope(ssp_app, logged_in_user):
    with ssp_app.app_context():
        scope = ContextScope(name="New System")
        db.session.add(scope)
        db.session.commit()
        scope_id = scope.id

    resp = logged_in_user.post(f"/ssp/create/{scope_id}", follow_redirects=True)
    assert resp.status_code == 200

    with ssp_app.app_context():
        ssp = SSPlan.query.filter_by(context_scope_id=scope_id).first()
        assert ssp is not None


def test_ssp_create_duplicate_redirects(ssp_app, scope_with_ssp, logged_in_user):
    scope_id, ssp_id = scope_with_ssp
    resp = logged_in_user.post(f"/ssp/create/{scope_id}", follow_redirects=True)
    assert resp.status_code == 200
    # Only one SSP should exist
    with ssp_app.app_context():
        count = SSPlan.query.filter_by(context_scope_id=scope_id).count()
        assert count == 1


def test_ssp_view_renders_sections(ssp_app, scope_with_ssp, logged_in_user):
    scope_id, ssp_id = scope_with_ssp
    resp = logged_in_user.get(f"/ssp/{ssp_id}")
    assert resp.status_code == 200
    # Key section headings should be present
    for heading in [b"System Identification", b"System Owner", b"FIPS 199", b"Security Controls"]:
        assert heading in resp.data, f"Expected section heading '{heading}' not found in SSP view"


def test_ssp_edit_get(ssp_app, scope_with_ssp, logged_in_user):
    _, ssp_id = scope_with_ssp
    resp = logged_in_user.get(f"/ssp/{ssp_id}/edit")
    assert resp.status_code == 200
    assert b"FIPS 199" in resp.data


def test_ssp_edit_post(ssp_app, scope_with_ssp, logged_in_user):
    _, ssp_id = scope_with_ssp
    resp = logged_in_user.post(
        f"/ssp/{ssp_id}/edit",
        data={
            "laws_regulations": "GDPR, NIS2",
            "authorization_boundary": "Internal network only",
            "fips_confidentiality": "moderate",
            "fips_integrity": "low",
            "fips_availability": "high",
            "plan_completion_date": "2026-12-31",
            "plan_approval_date": "",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with ssp_app.app_context():
        ssp = SSPlan.query.get(ssp_id)
        assert ssp.laws_regulations == "GDPR, NIS2"
        assert ssp.fips_confidentiality.value == "moderate"
        assert ssp.fips_availability.value == "high"


def test_ssp_add_interconnection(ssp_app, scope_with_ssp, logged_in_user):
    _, ssp_id = scope_with_ssp
    resp = logged_in_user.post(
        f"/ssp/{ssp_id}/interconnections",
        data={
            "system_name": "External HR System",
            "owning_organization": "HR Corp",
            "agreement_type": "mou",
            "data_direction": "bidirectional",
            "security_contact": "sec@hr.example",
            "notes": "",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with ssp_app.app_context():
        ic = SSPInterconnection.query.filter_by(ssp_id=ssp_id).first()
        assert ic is not None
        assert ic.system_name == "External HR System"


def test_seed_interconnections_from_interfaces(ssp_app, logged_in_user):
    """Interconnections are seeded from ContextScope.interfaces on SSP creation."""
    with ssp_app.app_context():
        scope = ContextScope(
            name="Iface System",
            interfaces="System A\nSystem B; System C",
        )
        db.session.add(scope)
        db.session.commit()
        scope_id = scope.id

    logged_in_user.post(f"/ssp/create/{scope_id}", follow_redirects=True)

    with ssp_app.app_context():
        ssp = SSPlan.query.filter_by(context_scope_id=scope_id).first()
        assert ssp is not None
        names = {ic.system_name for ic in ssp.interconnections}
        assert "System A" in names
        assert "System B" in names
        assert "System C" in names


def test_seed_controls_from_risks(ssp_app, logged_in_user):
    """Controls linked to Risk items are seeded into SSPControlEntry on creation."""
    with ssp_app.app_context():
        from scaffold.apps.risk.models import Risk, RiskImpact, RiskChance, RiskTreatmentOption

        scope = ContextScope(name="Control Test System", risk_assessment_human=True)
        component = Component(name="Web App", context_scope=scope)
        control = Control(domain="AC-1 Access Control Policy", section="Access Control")
        risk = Risk(
            title="Unauthorized Access",
            description="Risk of unauthorized access",
            impact=RiskImpact.MEDIUM,
            chance=RiskChance.MEDIUM,
            treatment=RiskTreatmentOption.MITIGATE,
        )
        risk.components.append(component)
        risk.controls.append(control)
        db.session.add_all([scope, component, control, risk])
        db.session.commit()
        scope_id = scope.id

    logged_in_user.post(f"/ssp/create/{scope_id}", follow_redirects=True)

    with ssp_app.app_context():
        ssp = SSPlan.query.filter_by(context_scope_id=scope_id).first()
        assert ssp is not None
        entry_controls = [e.control.domain for e in ssp.control_entries]
        assert "AC-1 Access Control Policy" in entry_controls


def test_ssp_pdf_export(ssp_app, scope_with_ssp, logged_in_user):
    """PDF export route returns a PDF content type."""
    _, ssp_id = scope_with_ssp
    resp = logged_in_user.get(f"/ssp/{ssp_id}/export/pdf")
    assert resp.status_code == 200
    assert "pdf" in resp.content_type
