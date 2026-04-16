"""SCIM-compliant error response helpers."""

from __future__ import annotations

from flask import jsonify

_ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"


def scim_error(status: int, detail: str, scim_type: str | None = None):
    """Return a SCIM error response with the correct schema."""
    body: dict = {
        "schemas": [_ERROR_SCHEMA],
        "status": str(status),
        "detail": detail,
    }
    if scim_type:
        body["scimType"] = scim_type
    response = jsonify(body)
    response.status_code = status
    response.content_type = "application/scim+json"
    return response
