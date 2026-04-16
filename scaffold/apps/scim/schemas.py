"""SCIM 2.0 JSON serialisation and deserialisation for User and Group resources."""

from __future__ import annotations

from typing import Any

from ..identity.models import AADGroupMapping, User, UserStatus

_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
_GROUP_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Group"
_LIST_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"


def user_to_scim(user: User) -> dict[str, Any]:
    """Serialise a User model instance into a SCIM User resource dict."""
    return {
        "schemas": [_USER_SCHEMA],
        "id": user.azure_oid or str(user.id),
        "externalId": user.azure_oid,
        "userName": user.aad_upn or user.email,
        "name": {
            "givenName": user.first_name or "",
            "familyName": user.last_name or "",
        },
        "emails": [
            {"value": user.email, "type": "work", "primary": True}
        ],
        "active": user.status == UserStatus.ACTIVE,
        "meta": {
            "resourceType": "User",
        },
    }


def group_to_scim(mapping: AADGroupMapping, members: list[User] | None = None) -> dict[str, Any]:
    """Serialise an AADGroupMapping into a SCIM Group resource dict."""
    resource: dict[str, Any] = {
        "schemas": [_GROUP_SCHEMA],
        "id": mapping.group_object_id,
        "externalId": mapping.group_object_id,
        "displayName": mapping.scim_display_name or mapping.group_object_id,
        "meta": {
            "resourceType": "Group",
        },
    }
    if members is not None:
        resource["members"] = [
            {"value": u.azure_oid, "display": u.email}
            for u in members
            if u.azure_oid
        ]
    return resource


def list_response(resources: list[dict], total: int) -> dict[str, Any]:
    """Wrap serialised resources in a SCIM ListResponse envelope."""
    return {
        "schemas": [_LIST_SCHEMA],
        "totalResults": total,
        "startIndex": 1,
        "itemsPerPage": total,
        "Resources": resources,
    }


def parse_user(data: dict[str, Any]) -> dict[str, Any]:
    """Extract normalised fields from a raw SCIM User payload."""
    emails = data.get("emails", [])
    primary_email = next(
        (e["value"] for e in emails if isinstance(e, dict) and e.get("primary")),
        emails[0]["value"] if emails and isinstance(emails[0], dict) else None,
    )
    name = data.get("name") or {}
    return {
        "external_id": data.get("externalId") or data.get("id"),
        "user_name": data.get("userName"),
        "first_name": name.get("givenName"),
        "last_name": name.get("familyName"),
        "email": primary_email,
        "active": data.get("active", True),
    }


def parse_group(data: dict[str, Any]) -> dict[str, Any]:
    """Extract normalised fields from a raw SCIM Group payload."""
    members = [
        m.get("value")
        for m in data.get("members", [])
        if isinstance(m, dict) and m.get("value")
    ]
    return {
        "group_id": (data.get("externalId") or data.get("id") or "").strip().lower(),
        "display_name": data.get("displayName"),
        "members": members,
    }
