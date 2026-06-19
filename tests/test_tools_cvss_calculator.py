from __future__ import annotations

import pytest

from scaffold import create_app
from scaffold.apps.tools import services
from scaffold.config import Settings
from scaffold.extensions import db


@pytest.fixture
def tools_app():
    settings = Settings(
        secret_key="test-secret",
        database_url="sqlite:///:memory:",
        session_cookie_secure=False,
        app_modules=["scaffold.apps.tools"],
    )
    app = create_app(settings)
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def tools_client(tools_app):
    return tools_app.test_client()


def nvd_payload(metric_key="cvssMetricV31", score=7.5):
    return {
        "vulnerabilities": [
            {
                "cve": {
                    "metrics": {
                        metric_key: [
                            {
                                "cvssData": {
                                    "baseScore": score,
                                }
                            }
                        ]
                    }
                }
            }
        ]
    }


def nvd_kev_payload(metric_key="cvssMetricV40", score=10.0):
    payload = nvd_payload(metric_key, score)
    payload["vulnerabilities"][0]["cve"].update(
        {
            "cisaExploitAdd": "2026-06-19",
            "cisaVulnerabilityName": "Example exploited vulnerability",
        }
    )
    return payload


def kev_payload(*cves: str):
    return {"vulnerabilities": [{"cveID": cve} for cve in cves]}


def patch_sources(monkeypatch, *, nvd=None, kev=None, nvd_error=False, kev_error=False):
    def fake_fetch_json(url, *, timeout=5, headers=None):
        if "services.nvd.nist.gov" in url:
            if nvd_error:
                raise services.LookupSourceError("nvd unavailable")
            return nvd if nvd is not None else nvd_payload()
        if "known_exploited_vulnerabilities" in url:
            if kev_error:
                raise services.LookupSourceError("kev unavailable")
            return kev if kev is not None else kev_payload()
        raise AssertionError(f"unexpected URL {url}")

    monkeypatch.setattr(services, "fetch_json", fake_fetch_json)


def test_cve_normalization_and_validation():
    assert services.normalize_cve_identifier(" cve-2024-12345 ") == "CVE-2024-12345"
    assert services.is_valid_cve_identifier("CVE-2024-1234")
    assert services.is_valid_cve_identifier("CVE-2024-12345")
    assert not services.is_valid_cve_identifier("2024-12345")
    assert not services.is_valid_cve_identifier("CVE-24-1234")
    assert not services.is_valid_cve_identifier("CVE-2024-ABC")
    assert not services.is_valid_cve_identifier("CVE-2024-123")


def test_extract_cvss_v31_preferred_over_v30():
    payload = {
        "vulnerabilities": [
            {
                "cve": {
                    "metrics": {
                        "cvssMetricV30": [{"cvssData": {"baseScore": 6.8}}],
                        "cvssMetricV31": [{"cvssData": {"baseScore": 8.1}}],
                    }
                }
            }
        ]
    }
    assert services.extract_cvss_v3_metric(payload) == (8.1, "nvd_cvss_v31")


def test_extract_cvss_v30_fallback_and_no_v3_score():
    assert services.extract_cvss_v3_metric(nvd_payload("cvssMetricV30", 6.4)) == (
        6.4,
        "nvd_cvss_v30",
    )
    assert services.extract_cvss_v3_metric({"vulnerabilities": [{"cve": {"metrics": {}}}]}) is None
    assert services.extract_cvss_v3_metric(nvd_payload("cvssMetricV31", 10.1)) is None


def test_extract_cvss_v40_fallback_when_v3_is_absent():
    assert services.extract_cvss_metric(nvd_payload("cvssMetricV40", 10.0)) == (
        10.0,
        "nvd_cvss_v40",
    )


def test_lookup_invalid_identifier_does_not_call_sources(monkeypatch):
    def fail_fetch_json(*args, **kwargs):
        raise AssertionError("external source should not be called")

    monkeypatch.setattr(services, "fetch_json", fail_fetch_json)
    result = services.lookup_vulnerability("not-a-cve")

    assert result["identifier_status"] == "invalid"
    assert result["requires_manual_base_score"] is False
    assert result["requires_manual_exploit_adjustment"] is False


def test_lookup_valid_cve_with_nvd_score_and_kev_absent(monkeypatch):
    patch_sources(monkeypatch, nvd=nvd_payload(score=7.5), kev=kev_payload("CVE-2024-0001"))

    result = services.lookup_vulnerability(" cve-2024-12345 ")

    assert result["identifier_status"] == "valid"
    assert result["vulnerability_identifier"] == "CVE-2024-12345"
    assert result["base_score"] == 7.5
    assert result["base_score_source"] == "nvd_cvss_v31"
    assert result["kev_status"] == "not_listed"
    assert result["exploit_adjustment"] == 0


def test_lookup_uses_cvss_v40_and_nvd_cisa_metadata_when_available(monkeypatch):
    patch_sources(monkeypatch, nvd=nvd_kev_payload(), kev=kev_payload())

    result = services.lookup_vulnerability("CVE-2026-45829")

    assert result["base_score"] == 10.0
    assert result["base_score_source"] == "nvd_cvss_v40"
    assert result["kev_status"] == "listed"
    assert result["exploit_adjustment"] == 1


def test_lookup_uses_nvd_cisa_metadata_when_kev_feed_unavailable(monkeypatch):
    patch_sources(monkeypatch, nvd=nvd_kev_payload(), kev_error=True)

    result = services.lookup_vulnerability("CVE-2026-45829")

    assert result["base_score"] == 10.0
    assert result["base_score_source"] == "nvd_cvss_v40"
    assert result["kev_status"] == "listed"
    assert result["exploit_adjustment"] == 1
    assert result["requires_manual_exploit_adjustment"] is False


def test_lookup_nvd_missing_cvss_v3_keeps_known_kev_status(monkeypatch):
    patch_sources(
        monkeypatch,
        nvd={"vulnerabilities": [{"cve": {"metrics": {}}}]},
        kev=kev_payload("CVE-2024-12345"),
    )

    result = services.lookup_vulnerability("CVE-2024-12345")

    assert result["base_score"] is None
    assert result["base_score_source"] == "manual_required"
    assert result["requires_manual_base_score"] is True
    assert result["kev_status"] == "listed"
    assert result["exploit_adjustment"] == 1


def test_lookup_nvd_unavailable_and_kev_unavailable(monkeypatch):
    patch_sources(monkeypatch, nvd_error=True, kev_error=True)

    result = services.lookup_vulnerability("CVE-2024-12345")

    assert result["base_score_source"] == "unavailable"
    assert result["requires_manual_base_score"] is True
    assert result["kev_status"] == "unavailable"
    assert result["exploit_adjustment"] is None
    assert result["requires_manual_exploit_adjustment"] is True


def test_lookup_kev_malformed_feed_is_unavailable(monkeypatch):
    patch_sources(monkeypatch, nvd=nvd_payload(), kev={"not_vulnerabilities": []})

    result = services.lookup_vulnerability("CVE-2024-12345")

    assert result["kev_status"] == "unavailable"
    assert result["exploit_adjustment"] is None
    assert result["requires_manual_exploit_adjustment"] is True


def test_route_returns_lookup_contract(tools_client, monkeypatch):
    patch_sources(monkeypatch, nvd=nvd_payload(score=9.8), kev=kev_payload("CVE-2024-12345"))

    response = tools_client.get(
        "/tools/cvss-calculator/lookup?vulnerability_identifier=CVE-2024-12345"
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["vulnerability_identifier"] == "CVE-2024-12345"
    assert data["base_score"] == 9.8
    assert data["kev_status"] == "listed"
    assert data["exploit_adjustment"] == 1
    assert data["requires_manual_exploit_adjustment"] is False


def test_route_returns_invalid_identifier_contract(tools_client, monkeypatch):
    patch_sources(monkeypatch)

    response = tools_client.get("/tools/cvss-calculator/lookup?vulnerability_identifier=nope")

    assert response.status_code == 200
    data = response.get_json()
    assert data["identifier_status"] == "invalid"
    assert data["base_score"] is None
    assert data["kev_status"] == "unavailable"


def test_route_uses_configured_timeouts_and_api_key(tools_client, tools_app, monkeypatch):
    seen = []

    def fake_fetch_json(url, *, timeout=5, headers=None):
        seen.append((url, timeout, headers or {}))
        if "services.nvd.nist.gov" in url:
            return nvd_payload()
        return kev_payload()

    monkeypatch.setattr(services, "fetch_json", fake_fetch_json)
    tools_app.config.update(
        NVD_API_KEY="secret-test-key",
        NVD_LOOKUP_TIMEOUT_SECONDS=3,
        KEV_LOOKUP_TIMEOUT_SECONDS=4,
    )

    response = tools_client.get(
        "/tools/cvss-calculator/lookup?vulnerability_identifier=CVE-2024-12345"
    )

    assert response.status_code == 200
    assert seen[0][1] == 3
    assert seen[0][2]["apiKey"] == "secret-test-key"
    assert seen[1][1] == 4


def test_calculator_template_contains_lookup_controls(tools_client):
    response = tools_client.get("/tools/cvss-calculator")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "vulnerabilityInput" in html
    assert "lookupStatus" in html
    assert "baseSourceLabel" in html
    assert "exploitSelect" in html
    assert "exploitSourceLabel" in html
    assert "manual override" in html.lower()
    assert "bExploit" in html


def test_manual_calculation_script_contains_required_behaviour(tools_client):
    response = tools_client.get("/tools/cvss-calculator")
    html = response.get_data(as_text=True)

    assert "Math.min(10" in html
    assert "manual_no_identifier" in html
    assert "manual_kev_unavailable" in html
    assert "resetLookupState" in html
    assert "requires_manual_exploit_adjustment" in html
