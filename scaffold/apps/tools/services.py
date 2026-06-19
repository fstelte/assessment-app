"""Services for security and assessment tools."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

NVD_CVE_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
KEV_FEED_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,}$")


class LookupSourceError(RuntimeError):
    """Raised when an external vulnerability source cannot be used."""


def normalize_cve_identifier(raw_identifier: str | None) -> str:
    """Return a trimmed, uppercased vulnerability identifier."""

    return (raw_identifier or "").strip().upper()


def is_valid_cve_identifier(identifier: str) -> bool:
    """Return whether the identifier matches the supported CVE shape."""

    return bool(CVE_PATTERN.fullmatch(identifier))


def invalid_lookup_response(identifier: str) -> dict[str, Any]:
    return {
        "vulnerability_identifier": identifier,
        "identifier_status": "invalid",
        "base_score": None,
        "base_score_source": "unavailable",
        "kev_status": "unavailable",
        "exploit_adjustment": None,
        "requires_manual_base_score": False,
        "requires_manual_exploit_adjustment": False,
        "messages": [
            "Enter a CVE identifier such as CVE-2024-12345, or leave the field blank for manual scoring."
        ],
    }


def lookup_vulnerability(
    raw_identifier: str | None,
    *,
    nvd_api_key: str = "",
    nvd_timeout: int = 5,
    kev_timeout: int = 5,
) -> dict[str, Any]:
    """Return normalized CVSS and KEV lookup data for the calculator."""

    identifier = normalize_cve_identifier(raw_identifier)
    if not is_valid_cve_identifier(identifier):
        return invalid_lookup_response(identifier)

    messages: list[str] = []
    base_score: float | None = None
    base_score_source = "manual_required"
    nvd_kev_listed: bool | None = None

    try:
        nvd_payload = fetch_nvd_cve(identifier, nvd_api_key=nvd_api_key, timeout=nvd_timeout)
        metric = extract_cvss_metric(nvd_payload)
        nvd_kev_listed = extract_nvd_kev_status(nvd_payload)
        if metric is None:
            messages.append("No usable CVSS base score was found for this vulnerability.")
        else:
            base_score, base_score_source = metric
    except LookupSourceError:
        base_score_source = "unavailable"
        messages.append("NVD is unavailable. Enter the CVSS v3 base score manually.")

    kev_status = "unavailable"
    exploit_adjustment: int | None = None
    requires_manual_exploit_adjustment = False

    try:
        kev_listed = fetch_kev_status(identifier, timeout=kev_timeout)
        if kev_listed or nvd_kev_listed:
            kev_status = "listed"
            exploit_adjustment = 1
        else:
            kev_status = "not_listed"
            exploit_adjustment = 0
    except LookupSourceError:
        if nvd_kev_listed:
            kev_status = "listed"
            exploit_adjustment = 1
            messages.append("CISA KEV feed is unavailable; KEV status was inferred from NVD CISA metadata.")
        else:
            requires_manual_exploit_adjustment = True
            messages.append(
                "KEV status is unavailable. Choose exploit availability manually; the result will be marked as a manual override."
            )

    return {
        "vulnerability_identifier": identifier,
        "identifier_status": "valid",
        "base_score": base_score,
        "base_score_source": base_score_source,
        "kev_status": kev_status,
        "exploit_adjustment": exploit_adjustment,
        "requires_manual_base_score": base_score is None,
        "requires_manual_exploit_adjustment": requires_manual_exploit_adjustment,
        "messages": messages,
    }


def fetch_nvd_cve(identifier: str, *, nvd_api_key: str = "", timeout: int = 5) -> dict[str, Any]:
    query = urllib.parse.urlencode({"cveId": identifier})
    headers = {"User-Agent": "assessment-app-cvss-calculator"}
    if nvd_api_key:
        headers["apiKey"] = nvd_api_key
    return fetch_json(f"{NVD_CVE_API_URL}?{query}", timeout=timeout, headers=headers)


def fetch_kev_status(identifier: str, *, timeout: int = 5) -> bool:
    payload = fetch_json(KEV_FEED_URL, timeout=timeout)
    vulnerabilities = payload.get("vulnerabilities")
    if not isinstance(vulnerabilities, list):
        raise LookupSourceError("KEV feed did not contain a vulnerabilities list")
    return any(
        normalize_cve_identifier(item.get("cveID") if isinstance(item, dict) else None) == identifier
        for item in vulnerabilities
    )


def fetch_json(url: str, *, timeout: int = 5, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=max(timeout, 1)) as response:
            payload = response.read().decode("utf-8")
    except (TimeoutError, OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise LookupSourceError(str(exc)) from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise LookupSourceError("source returned malformed JSON") from exc
    if not isinstance(data, dict):
        raise LookupSourceError("source returned an unexpected JSON shape")
    return data


def extract_cvss_metric(payload: dict[str, Any]) -> tuple[float, str] | None:
    for metric_key, source in (("cvssMetricV31", "nvd_cvss_v31"), ("cvssMetricV30", "nvd_cvss_v30")):
        for metric in _iter_nvd_metrics(payload, metric_key):
            score = _extract_base_score(metric)
            if score is not None:
                return score, source
    for metric in _iter_nvd_metrics(payload, "cvssMetricV40"):
        score = _extract_base_score(metric)
        if score is not None:
            return score, "nvd_cvss_v40"
    return None


def extract_cvss_v3_metric(payload: dict[str, Any]) -> tuple[float, str] | None:
    return extract_cvss_metric(payload)


def extract_nvd_kev_status(payload: dict[str, Any]) -> bool | None:
    vulnerabilities = payload.get("vulnerabilities")
    if not isinstance(vulnerabilities, list):
        return None
    for vulnerability in vulnerabilities:
        if not isinstance(vulnerability, dict):
            continue
        cve = vulnerability.get("cve")
        if not isinstance(cve, dict):
            continue
        if any(cve.get(key) for key in ("cisaExploitAdd", "cisaActionDue", "cisaRequiredAction", "cisaVulnerabilityName")):
            return True
    return None


def _iter_nvd_metrics(payload: dict[str, Any], metric_key: str) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    vulnerabilities = payload.get("vulnerabilities")
    if not isinstance(vulnerabilities, list):
        return metrics
    for vulnerability in vulnerabilities:
        if not isinstance(vulnerability, dict):
            continue
        cve = vulnerability.get("cve")
        if not isinstance(cve, dict):
            continue
        metric_container = cve.get("metrics")
        if not isinstance(metric_container, dict):
            continue
        metric_values = metric_container.get(metric_key)
        if isinstance(metric_values, list):
            metrics.extend(item for item in metric_values if isinstance(item, dict))
    return metrics


def _extract_base_score(metric: dict[str, Any]) -> float | None:
    cvss_data = metric.get("cvssData")
    if not isinstance(cvss_data, dict):
        return None
    raw_score = cvss_data.get("baseScore")
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        return None
    if 0.0 <= score <= 10.0:
        return score
    return None
