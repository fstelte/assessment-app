"""Business logic for SCIM-driven user and group provisioning."""

from __future__ import annotations

import secrets

from flask import current_app

from ...core.audit import log_event
from ...extensions import db
from ..identity.models import AADGroupMapping, Role, User, UserStatus


def provision_user(
    *,
    external_id: str | None,
    user_name: str | None,
    first_name: str | None,
    last_name: str | None,
    email: str | None,
    active: bool = True,
) -> tuple[User, bool]:
    """Create or update a user from SCIM attributes.

    Returns ``(user, created)`` where *created* is True when a new row was inserted.
    """
    if not external_id and not user_name and not email:
        raise ValueError("At least one of externalId, userName, or email is required")

    user: User | None = None

    if external_id:
        user = User.query.filter_by(azure_oid=external_id.strip().lower()).first()
    if user is None and user_name:
        user = User.query.filter_by(aad_upn=user_name.strip().lower()).first()
    if user is None and email:
        user = User.find_by_email(email)

    created = user is None
    if created:
        if not email:
            raise ValueError("email is required when creating a new user")
        user = User(
            email=email.strip().lower(),
            password_hash=secrets.token_hex(32),
            status=UserStatus.ACTIVE,
        )
        db.session.add(user)

    # Update fields
    if external_id:
        user.set_entra_identity(external_id, user_name)
    elif user_name:
        user.aad_upn = user_name.strip().lower()
    if email:
        user.email = email.strip().lower()
    if first_name is not None:
        user.first_name = first_name or None
    if last_name is not None:
        user.last_name = last_name or None

    target_status = UserStatus.ACTIVE if active else UserStatus.DISABLED
    user.status = target_status

    db.session.flush()
    log_event(
        "scim_user_provisioned" if created else "scim_user_updated",
        "User",
        entity_id=user.azure_oid or str(user.id),
        details={"active": active},
    )
    return user, created


def deprovision_user(user: User) -> None:
    """Disable a user and remove all roles. Does not hard-delete."""
    user.status = UserStatus.DISABLED
    user.roles.clear()
    db.session.flush()
    log_event(
        "scim_user_deprovisioned",
        "User",
        entity_id=user.azure_oid or str(user.id),
    )


def upsert_group(
    group_id: str,
    display_name: str | None = None,
    initial_members: list[str] | None = None,
) -> tuple[AADGroupMapping, bool]:
    """Create or update an AADGroupMapping for the given Entra OID.

    Returns ``(mapping, created)``.
    """
    normalised_id = group_id.strip().lower()
    mapping = AADGroupMapping.query.filter_by(group_object_id=normalised_id).first()
    created = mapping is None
    if created:
        mapping = AADGroupMapping(group_object_id=normalised_id)
        db.session.add(mapping)

    if display_name is not None:
        mapping.scim_display_name = display_name

    db.session.flush()

    if initial_members:
        for oid in initial_members:
            _sync_add_member(mapping, oid)

    log_event(
        "scim_group_registered" if created else "scim_group_updated",
        "AADGroupMapping",
        entity_id=normalised_id,
        details={"display_name": display_name},
    )
    return mapping, created


def add_member_to_group(mapping: AADGroupMapping, user_oid: str) -> None:
    """Assign the role associated with *mapping* to the user identified by *user_oid*."""
    _sync_add_member(mapping, user_oid)
    db.session.flush()


def remove_member_from_group(mapping: AADGroupMapping, user_oid: str) -> None:
    """Remove the group's role from the user, preserving other roles."""
    normalised_oid = user_oid.strip().lower()
    user = User.query.filter_by(azure_oid=normalised_oid).first()
    if user is None or mapping.role is None:
        return

    # Only remove the role if no other active group mapping grants the same role
    same_role_mappings = AADGroupMapping.query.filter_by(role_id=mapping.role_id).all()
    other_group_ids = {
        m.group_object_id for m in same_role_mappings if m.id != mapping.id
    }
    # Check if user is listed as having any other group that grants the same role —
    # we cannot know that here without querying membership, so we conservatively
    # remove it only if there are no other mappings for the same role.
    if not other_group_ids:
        if user.has_role(mapping.role.name):
            user.roles.remove(mapping.role)
            db.session.flush()
            log_event(
                "scim_role_revoked",
                "User",
                entity_id=normalised_oid,
                details={"role": mapping.role.name, "group": mapping.group_object_id},
            )


def delete_group(mapping: AADGroupMapping) -> None:
    """Remove an AADGroupMapping and revoke the role from users who only held it via this group."""
    if mapping.role:
        role = mapping.role
        # Find users who hold this role
        for user in list(role.users):
            # Check if another mapping also grants this role
            other_mappings = AADGroupMapping.query.filter(
                AADGroupMapping.role_id == mapping.role_id,
                AADGroupMapping.id != mapping.id,
            ).count()
            if other_mappings == 0:
                user.roles.remove(role)
    db.session.delete(mapping)
    db.session.flush()
    log_event(
        "scim_group_deleted",
        "AADGroupMapping",
        entity_id=mapping.group_object_id,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sync_add_member(mapping: AADGroupMapping, user_oid: str) -> None:
    normalised_oid = user_oid.strip().lower()
    user = User.query.filter_by(azure_oid=normalised_oid).first()
    if user is None:
        current_app.logger.debug("SCIM add member: unknown user OID %s", normalised_oid)
        return
    if mapping.role is None:
        current_app.logger.debug(
            "SCIM add member: group %s has no role mapping yet", mapping.group_object_id
        )
        return
    user.ensure_role(mapping.role.name)
    log_event(
        "scim_role_assigned",
        "User",
        entity_id=normalised_oid,
        details={"role": mapping.role.name, "group": mapping.group_object_id},
    )
