"""Role synchronisation helpers for SAML logins."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Iterable, Mapping, Set

from flask import current_app

from ..identity.models import Role, User


@dataclass(slots=True)
class RoleSyncConfig:
    """Container for role synchronisation settings."""

    mapping: Mapping[str, Set[str]]

    @property
    def managed_role_names(self) -> Set[str]:
        names: Set[str] = set()
        for role_names in self.mapping.values():
            names.update(role_names)
        return names


class RoleSyncService:
    """Apply federated group membership to platform roles."""

    def __init__(self, config: RoleSyncConfig, use_db_mappings: bool = True) -> None:
        self._config = config
        self._use_db_mappings = use_db_mappings

    @classmethod
    def from_app(cls, app) -> "RoleSyncService":
        raw = (
            app.config.get("SAML_ROLE_MAP")
            or app.config.get("ENTRA_ROLE_MAP")
            or app.config.get("AZURE_ROLE_MAP")
            or ""
        ).strip()
        mapping: dict[str, Set[str]] = {}
        if raw:
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                app.logger.error("Failed to parse SAML_ROLE_MAP; expected JSON object mapping group IDs to role names")
            else:
                mapping = _normalise_mapping(payload)
        app.logger.debug("SAML role map loaded with %d entries", len(mapping))
        return cls(RoleSyncConfig(mapping=mapping), use_db_mappings=True)

    def apply(self, user: User, group_ids: Iterable[str]) -> None:
        normalized_groups = {gid.strip().lower() for gid in group_ids if gid and gid.strip()}
        if current_app.logger.isEnabledFor(logging.DEBUG):
            current_app.logger.debug(
                "SAML role sync for %s: groups=%s", user.email, sorted(normalized_groups)
            )

        if self._use_db_mappings:
            user.sync_roles_from_entra_groups(normalized_groups, remove_missing=True)

        if not self._config.mapping:
            return

        if current_app.logger.isEnabledFor(logging.DEBUG):
            current_app.logger.debug(
                "SAML role sync map targets: %s",
                {group: sorted(roles) for group, roles in self._config.mapping.items()},
            )
        self._apply_config_mapping(user, normalized_groups)

    def _apply_config_mapping(self, user: User, group_ids: Set[str]) -> None:
        managed_names = self._config.managed_role_names
        if not managed_names:
            return

        target_names: Set[str] = set()
        for group_id in group_ids:
            target_names.update(self._config.mapping.get(group_id, set()))

        roles = Role.query.filter(Role.name.in_(managed_names)).all() if managed_names else []
        roles_by_name = {role.name: role for role in roles}
        missing = managed_names - roles_by_name.keys()
        if missing:
            current_app.logger.warning(
                "Configured SAML role mappings reference unknown roles: %s",
                ", ".join(sorted(missing)),
            )

        for role_name in sorted(target_names):
            role = roles_by_name.get(role_name)
            if role and role not in user.roles:
                user.roles.append(role)

        for role in list(user.roles):
            if role.name in managed_names and role.name not in target_names:
                user.roles.remove(role)


def _normalise_mapping(payload: object) -> dict[str, Set[str]]:
    mapping: dict[str, Set[str]] = {}
    if not isinstance(payload, dict):
        current_app.logger.error("SAML_ROLE_MAP must be a JSON object, got %s", type(payload).__name__)
        return mapping

    for raw_group, raw_roles in payload.items():
        if not isinstance(raw_group, str):
            current_app.logger.warning("Skipping non-string group key in SAML_ROLE_MAP: %r", raw_group)
            continue
        group_key = raw_group.strip().lower()
        if not group_key:
            continue

        roles: Set[str] = set()
        if isinstance(raw_roles, str):
            roles.add(raw_roles.strip())
        elif isinstance(raw_roles, Iterable):
            for item in raw_roles:
                if isinstance(item, str) and item.strip():
                    roles.add(item.strip())
        else:
            current_app.logger.warning("Skipping unsupported role mapping value for %s", raw_group)

        if roles:
            mapping[group_key] = roles

    return mapping
