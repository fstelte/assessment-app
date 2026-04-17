"""SCIM 2.0 HTTP endpoints."""

from __future__ import annotations

import re
from typing import Any

from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from ...core.audit import log_event
from ...extensions import csrf, db, limiter
from ..identity.models import AADGroupMapping, User, UserStatus
from .auth import require_scim_token
from .errors import scim_error
from .provisioner import (
    add_member_to_group,
    delete_group,
    deprovision_user,
    provision_user,
    remove_member_from_group,
    upsert_group,
)
from .schemas import (
    group_to_scim,
    list_response,
    parse_group,
    parse_user,
    user_to_scim,
)

bp = Blueprint("scim", __name__, url_prefix="/scim/v2")

# SCIM is a server-to-server API authenticated by bearer token; CSRF tokens
# are not applicable and the entire blueprint is exempted.
csrf.exempt(bp)

_SCIM_CONTENT_TYPE = "application/scim+json"
_SP_CONFIG_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"
_SCHEMAS_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Schema"
_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
_GROUP_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Group"

_RATE_LIMIT = "100 per minute"


def _scim_response(data: dict, status: int = 200):
    resp = jsonify(data)
    resp.status_code = status
    resp.content_type = _SCIM_CONTENT_TYPE
    return resp


# ---------------------------------------------------------------------------
# Service Provider Config
# ---------------------------------------------------------------------------

@bp.get("/ServiceProviderConfig")
@limiter.limit(_RATE_LIMIT)
@require_scim_token
def service_provider_config():
    return _scim_response({
        "schemas": [_SP_CONFIG_SCHEMA],
        "patch": {"supported": True},
        "bulk": {"supported": False},
        "filter": {"supported": True, "maxResults": 200},
        "changePassword": {"supported": False},
        "sort": {"supported": False},
        "etag": {"supported": False},
        "authenticationSchemes": [
            {
                "type": "oauthbearertoken",
                "name": "OAuth Bearer Token",
                "description": "Bearer token issued via the admin panel.",
                "primary": True,
            }
        ],
    })


# ---------------------------------------------------------------------------
# Schemas endpoint (discovery)
# ---------------------------------------------------------------------------

@bp.get("/Schemas")
@limiter.limit(_RATE_LIMIT)
@require_scim_token
def schemas():
    return _scim_response({
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 2,
        "Resources": [
            {"id": _USER_SCHEMA, "name": "User"},
            {"id": _GROUP_SCHEMA, "name": "Group"},
        ],
    })


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@bp.get("/Users")
@limiter.limit(_RATE_LIMIT)
@require_scim_token
def list_users():
    filter_param = request.args.get("filter", "")
    query = User.query

    if filter_param:
        user = _apply_user_filter(filter_param)
        if user is None:
            return _scim_response(list_response([], 0))
        return _scim_response(list_response([user_to_scim(user)], 1))

    users = query.all()
    return _scim_response(list_response([user_to_scim(u) for u in users], len(users)))


@bp.post("/Users")
@limiter.limit(_RATE_LIMIT)
@require_scim_token
def create_user():
    data = request.get_json(silent=True)
    if not data:
        return scim_error(400, "Request body must be valid JSON", "invalidValue")

    parsed = parse_user(data)
    if not parsed.get("email") and not parsed.get("user_name"):
        return scim_error(400, "Either email or userName is required", "invalidValue")

    # Check uniqueness
    if parsed.get("external_id"):
        existing = User.query.filter_by(
            azure_oid=parsed["external_id"].strip().lower()
        ).first()
        if existing:
            user, _ = provision_user(**parsed)
            db.session.commit()
            return _scim_response(user_to_scim(user), 200)

    try:
        user, created = provision_user(**parsed)
        db.session.commit()
    except ValueError as exc:
        return scim_error(400, str(exc), "invalidValue")

    return _scim_response(user_to_scim(user), 201 if created else 200)


@bp.get("/Users/<path:user_id>")
@limiter.limit(_RATE_LIMIT)
@require_scim_token
def get_user(user_id: str):
    user = _find_user(user_id)
    if user is None:
        return scim_error(404, f"User '{user_id}' not found")
    return _scim_response(user_to_scim(user))


@bp.put("/Users/<path:user_id>")
@limiter.limit(_RATE_LIMIT)
@require_scim_token
def replace_user(user_id: str):
    user = _find_user(user_id)
    if user is None:
        return scim_error(404, f"User '{user_id}' not found")

    data = request.get_json(silent=True)
    if not data:
        return scim_error(400, "Request body must be valid JSON", "invalidValue")

    parsed = parse_user(data)
    try:
        updated_user, _ = provision_user(**parsed)
        db.session.commit()
    except ValueError as exc:
        return scim_error(400, str(exc), "invalidValue")
    return _scim_response(user_to_scim(updated_user))


@bp.route("/Users/<path:user_id>", methods=["PATCH"])
@limiter.limit(_RATE_LIMIT)
@require_scim_token
def patch_user(user_id: str):
    user = _find_user(user_id)
    if user is None:
        return scim_error(404, f"User '{user_id}' not found")

    data = request.get_json(silent=True)
    if not data:
        return scim_error(400, "Request body must be valid JSON", "invalidValue")

    operations = data.get("Operations", [])
    for op in operations:
        op_name = (op.get("op") or "").lower()
        path = op.get("path") or ""
        value = op.get("value")

        if op_name == "replace":
            if path == "active" or path == "":
                if isinstance(value, dict):
                    if "active" in value:
                        _set_active(user, value["active"])
                    _apply_attribute_dict(user, value)
                elif path == "active":
                    _set_active(user, value)
            elif path.startswith("name."):
                attr = path.split(".", 1)[1]
                if attr == "givenName":
                    user.first_name = value or None
                elif attr == "familyName":
                    user.last_name = value or None
            elif path == "userName":
                user.aad_upn = str(value).strip().lower() if value else user.aad_upn
            elif path == "emails":
                if isinstance(value, list) and value:
                    user.email = value[0].get("value", user.email)

    db.session.commit()
    return _scim_response(user_to_scim(user))


@bp.delete("/Users/<path:user_id>")
@limiter.limit(_RATE_LIMIT)
@require_scim_token
def delete_user(user_id: str):
    user = _find_user(user_id)
    if user is None:
        return scim_error(404, f"User '{user_id}' not found")
    deprovision_user(user)
    db.session.commit()
    return ("", 204)


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------

@bp.get("/Groups")
@limiter.limit(_RATE_LIMIT)
@require_scim_token
def list_groups():
    filter_param = request.args.get("filter", "")
    if filter_param:
        mapping = _apply_group_filter(filter_param)
        if mapping is None:
            return _scim_response(list_response([], 0))
        return _scim_response(list_response([group_to_scim(mapping)], 1))

    mappings = AADGroupMapping.query.all()
    return _scim_response(list_response([group_to_scim(m) for m in mappings], len(mappings)))


@bp.post("/Groups")
@limiter.limit(_RATE_LIMIT)
@require_scim_token
def create_group():
    data = request.get_json(silent=True)
    if not data:
        return scim_error(400, "Request body must be valid JSON", "invalidValue")

    parsed = parse_group(data)
    if not parsed["group_id"]:
        return scim_error(400, "Group id or externalId is required", "invalidValue")

    mapping, created = upsert_group(
        parsed["group_id"],
        display_name=parsed["display_name"],
        initial_members=parsed["members"],
    )
    db.session.commit()
    return _scim_response(group_to_scim(mapping), 201 if created else 200)


@bp.get("/Groups/<path:group_id>")
@limiter.limit(_RATE_LIMIT)
@require_scim_token
def get_group(group_id: str):
    mapping = AADGroupMapping.query.filter_by(
        group_object_id=group_id.strip().lower()
    ).first()
    if mapping is None:
        return scim_error(404, f"Group '{group_id}' not found")
    return _scim_response(group_to_scim(mapping))


@bp.put("/Groups/<path:group_id>")
@limiter.limit(_RATE_LIMIT)
@require_scim_token
def replace_group(group_id: str):
    mapping = AADGroupMapping.query.filter_by(
        group_object_id=group_id.strip().lower()
    ).first()
    if mapping is None:
        return scim_error(404, f"Group '{group_id}' not found")

    data = request.get_json(silent=True)
    if not data:
        return scim_error(400, "Request body must be valid JSON", "invalidValue")

    parsed = parse_group(data)
    updated, _ = upsert_group(
        group_id,
        display_name=parsed["display_name"],
        initial_members=parsed["members"],
    )
    db.session.commit()
    return _scim_response(group_to_scim(updated))


@bp.route("/Groups/<path:group_id>", methods=["PATCH"])
@limiter.limit(_RATE_LIMIT)
@require_scim_token
def patch_group(group_id: str):
    normalised_id = group_id.strip().lower()
    mapping = AADGroupMapping.query.filter_by(group_object_id=normalised_id).first()
    if mapping is None:
        return scim_error(404, f"Group '{group_id}' not found")

    data = request.get_json(silent=True)
    if not data:
        return scim_error(400, "Request body must be valid JSON", "invalidValue")

    operations = data.get("Operations", [])
    for op in operations:
        op_name = (op.get("op") or "").lower()
        path = op.get("path") or ""
        value = op.get("value")

        if path == "displayName" and op_name == "replace":
            mapping.scim_display_name = value

        elif path == "members" and op_name == "add":
            if isinstance(value, list):
                for member in value:
                    oid = member.get("value") if isinstance(member, dict) else str(member)
                    if oid:
                        add_member_to_group(mapping, oid)

        elif op_name == "remove" and path.startswith("members"):
            # Entra sends: members[value eq "<oid>"]
            match = re.search(r'members\[value eq "([^"]+)"\]', path)
            if match:
                remove_member_from_group(mapping, match.group(1))
            elif isinstance(value, list):
                for member in value:
                    oid = member.get("value") if isinstance(member, dict) else str(member)
                    if oid:
                        remove_member_from_group(mapping, oid)

        elif op_name == "add" and not path:
            # Some IdPs send {"op": "add", "value": {"displayName": "foo"}}
            if isinstance(value, dict) and "displayName" in value:
                mapping.scim_display_name = value["displayName"]

    db.session.commit()
    return _scim_response(group_to_scim(mapping))


@bp.delete("/Groups/<path:group_id>")
@limiter.limit(_RATE_LIMIT)
@require_scim_token
def delete_group_route(group_id: str):
    normalised_id = group_id.strip().lower()
    mapping = AADGroupMapping.query.filter_by(group_object_id=normalised_id).first()
    if mapping is None:
        return scim_error(404, f"Group '{group_id}' not found")
    delete_group(mapping)
    db.session.commit()
    return ("", 204)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_user(user_id: str) -> User | None:
    """Look up a user by azure_oid (primary) or internal id."""
    normalised = user_id.strip().lower()
    user = User.query.filter_by(azure_oid=normalised).first()
    if user is None and user_id.isdigit():
        user = db.session.get(User, int(user_id))
    return user


def _apply_user_filter(filter_str: str) -> User | None:
    """Parse a simple SCIM filter and return a matching User or None."""
    # Support: userName eq "value", externalId eq "value"
    m = re.match(r'(\w+)\s+eq\s+"([^"]+)"', filter_str.strip(), re.IGNORECASE)
    if not m:
        return None
    attr, val = m.group(1).lower(), m.group(2)
    if attr == "username":
        return User.query.filter(
            or_(User.aad_upn == val.lower(), User.email == val.lower())
        ).first()
    if attr == "externalid":
        return User.query.filter_by(azure_oid=val.strip().lower()).first()
    return None


def _apply_group_filter(filter_str: str) -> AADGroupMapping | None:
    m = re.match(r'(\w+)\s+eq\s+"([^"]+)"', filter_str.strip(), re.IGNORECASE)
    if not m:
        return None
    attr, val = m.group(1).lower(), m.group(2)
    if attr in ("externalid", "id"):
        return AADGroupMapping.query.filter_by(
            group_object_id=val.strip().lower()
        ).first()
    if attr == "displayname":
        return AADGroupMapping.query.filter_by(scim_display_name=val).first()
    return None


def _set_active(user: User, active: Any) -> None:
    if isinstance(active, str):
        active = active.lower() == "true"
    user.status = UserStatus.ACTIVE if active else UserStatus.DISABLED


def _apply_attribute_dict(user: User, value: dict) -> None:
    if "userName" in value:
        user.aad_upn = str(value["userName"]).strip().lower()
    if "emails" in value and isinstance(value["emails"], list) and value["emails"]:
        user.email = value["emails"][0].get("value", user.email)
    name = value.get("name") or {}
    if "givenName" in name:
        user.first_name = name["givenName"] or None
    if "familyName" in name:
        user.last_name = name["familyName"] or None
