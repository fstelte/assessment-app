"""Unified identity models shared across scaffold applications."""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Iterable, List, Set

import sqlalchemy as sa
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ...extensions import db
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import joinedload, validates


ROLE_ADMIN = "admin"
ROLE_ASSESSMENT_MANAGER = "manager"

_DEFAULT_ROLES: dict[str, str] = {
    ROLE_ADMIN: "Platform administrator",
    ROLE_ASSESSMENT_MANAGER: "Assessment manager",
}


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for defaults."""

    return datetime.now(UTC)


user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    db.Column("created_at", db.DateTime(timezone=True), default=utc_now, nullable=False),
)


class TimestampMixin:
    """Reusable mixin tracking created and updated timestamps."""

    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class UserStatus(enum.Enum):
    """Lifecycle state for an account."""

    PENDING = "pending"
    ACTIVE = "active"
    DISABLED = "disabled"


_USER_STATUS_VALUES = tuple(member.value for member in UserStatus)


class UserStatusType(sa.types.TypeDecorator):
    """Persist :class:`UserStatus` values while returning enum instances."""

    impl = sa.String()
    cache_ok = True

    def load_dialect_impl(self, dialect: sa.engine.Dialect) -> sa.types.TypeEngine:
        if dialect.name == "postgresql":
            return postgresql.ENUM(
                *_USER_STATUS_VALUES,
                name="user_status",
                create_type=False,
            )
        return sa.Enum(
            *_USER_STATUS_VALUES,
            name="user_status",
            native_enum=False,
            validate_strings=False,
        )

    def process_bind_param(self, value: UserStatus | str | None, dialect: sa.engine.Dialect) -> str | None:
        if value is None:
            return None
        if isinstance(value, UserStatus):
            return value.value
        if isinstance(value, str):
            lowered = value.lower()
            if lowered not in _USER_STATUS_VALUES:
                raise ValueError(f"Invalid user status '{value}'")
            return lowered
        raise TypeError(f"Cannot bind value of type {type(value)!r} for UserStatus")

    def process_result_value(self, value: str | None, dialect: sa.engine.Dialect) -> UserStatus | None:
        if value is None:
            return None
        if isinstance(value, UserStatus):
            return value
        normalized = value.lower()
        if normalized not in _USER_STATUS_VALUES:
            raise LookupError(
                f"'{value}' is not among the defined enum values. Enum name: user_status. Possible values: {', '.join(_USER_STATUS_VALUES)}"
            )
        return UserStatus(normalized)


class Role(TimestampMixin, db.Model):
    """Application role used for authorisation decisions."""

    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))

    users = db.relationship("User", secondary=user_roles, back_populates="roles")
    aad_group_mappings = db.relationship(
        "AADGroupMapping",
        back_populates="role",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - diagnostic helper
        return f"<Role {self.name!r}>"


def ensure_default_roles() -> None:
    """Make sure the core authorisation roles exist in the database."""

    try:
        created = False
        for name, description in _DEFAULT_ROLES.items():
            if Role.query.filter_by(name=name).first():
                continue
            role = Role(name=name, description=description)
            db.session.add(role)
            created = True

        if created:
            db.session.commit()
    except (ProgrammingError, OperationalError):
        db.session.rollback()
        logger = current_app.logger if current_app else None
        if logger:
            logger.debug("Default role provisioning skipped; tables not ready yet.")


class AADGroupMapping(TimestampMixin, db.Model):
    """Maps Microsoft Entra ID security groups to platform roles."""

    __tablename__ = "aad_group_mappings"

    id = db.Column(db.Integer, primary_key=True)
    group_object_id = db.Column(db.String(255), unique=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)

    role = db.relationship("Role", back_populates="aad_group_mappings")

    @validates("group_object_id")
    def _normalize_group(self, key: str, value: str | None) -> str:
        if not value or not value.strip():
            raise ValueError("group_object_id cannot be empty")
        return value.strip().lower()

    def __repr__(self) -> str:  # pragma: no cover - diagnostic helper
        return f"<AADGroupMapping group={self.group_object_id!r} role_id={self.role_id}>"


class User(TimestampMixin, UserMixin, db.Model):
    """Application user with status-driven lifecycle."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(255), index=True)  # Optional legacy username support
    first_name = db.Column(db.String(120))
    last_name = db.Column(db.String(120))
    password_hash = db.Column(db.String(255), nullable=False)
    status = db.Column(UserStatusType(), default=UserStatus.PENDING, nullable=False)
    is_service_account = db.Column(db.Boolean, default=False, nullable=False)
    last_login_at = db.Column(db.DateTime(timezone=True))
    activated_at = db.Column(db.DateTime(timezone=True))
    deactivated_at = db.Column(db.DateTime(timezone=True))
    theme_preference = db.Column(db.String(20), default="dark", nullable=False)
    locale_preference = db.Column(db.String(10), default="en", nullable=False)
    azure_oid = db.Column(db.String(255), unique=True, index=True)
    aad_upn = db.Column(db.String(255), unique=True)

    roles = db.relationship("Role", secondary=user_roles, back_populates="users")
    mfa_setting = db.relationship(
        "MFASetting",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    assignments = db.relationship(
        "AssessmentAssignment",
        back_populates="assignee",
        foreign_keys="AssessmentAssignment.assignee_id",
    )
    created_assessments = db.relationship(
        "Assessment",
        back_populates="created_by",
        foreign_keys="Assessment.created_by_id",
    )
    bia_contexts = db.relationship("ContextScope", back_populates="author")

    @property
    def is_active(self) -> bool:  # type: ignore[override]
        return self.status == UserStatus.ACTIVE

    @property
    def is_anonymous(self) -> bool:  # type: ignore[override]
        return False

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, candidate: str) -> bool:
        return check_password_hash(self.password_hash, candidate)

    def has_role(self, role: str) -> bool:
        return any(r.name == role for r in self.roles)

    def ensure_role(self, role: str) -> None:
        if not self.has_role(role):
            target = Role.query.filter_by(name=role).first()
            if target:
                self.roles.append(target)

    def set_entra_identity(self, object_id: str | None, upn: str | None = None) -> None:
        """Persist the external Entra identity attributes for the user."""

        self.azure_oid = object_id.strip().lower() if object_id else None
        if upn is not None:
            upn_value = upn.strip().lower()
            self.aad_upn = upn_value or None

    def clear_entra_roles(self) -> None:
        """Remove all roles that are managed via Entra group mappings."""

        mapping_role_ids = set(db.session.execute(sa.select(AADGroupMapping.role_id)).scalars())
        if not mapping_role_ids:
            return
        for role in list(self.roles):
            if role.id in mapping_role_ids:
                self.roles.remove(role)

    def sync_roles_from_entra_groups(self, group_ids: Iterable[str], remove_missing: bool = True) -> None:
        """Align user roles with the configured Entra security group mappings."""

        normalized_groups = {gid.strip().lower() for gid in group_ids if gid and gid.strip()}
        mappings = (
            AADGroupMapping.query.options(joinedload(AADGroupMapping.role)).all()
        )
        if not mappings:
            if remove_missing:
                self.clear_entra_roles()
            return

        target_role_ids: Set[int] = {
            mapping.role_id
            for mapping in mappings
            if mapping.group_object_id in normalized_groups
        }
        mapping_role_ids: Set[int] = {mapping.role_id for mapping in mappings}
        roles_by_id = {mapping.role_id: mapping.role for mapping in mappings if mapping.role is not None}

        for role_id in target_role_ids:
            role = roles_by_id.get(role_id)
            if role and role not in self.roles:
                self.roles.append(role)

        if remove_missing and mapping_role_ids:
            for role in list(self.roles):
                if role.id in mapping_role_ids and role.id not in target_role_ids:
                    self.roles.remove(role)

    @property
    def full_name(self) -> str:
        names: List[str] = [name for name in (self.first_name, self.last_name) if name]
        if names:
            return " ".join(names)
        if self.username:
            return self.username
        return self.email

    @property
    def mfa_is_enabled(self) -> bool:
        return bool(self.mfa_setting and self.mfa_setting.enabled)

    @property
    def mfa_is_enrolled(self) -> bool:
        return bool(self.mfa_setting and self.mfa_setting.enabled and self.mfa_setting.enrolled_at)

    @classmethod
    def find_by_email(cls, email: str) -> "User | None":
        return cls.query.filter(db.func.lower(cls.email) == email.lower()).one_or_none()

    @classmethod
    def find_by_azure_oid(cls, object_id: str) -> "User | None":
        return cls.query.filter(db.func.lower(cls.azure_oid) == object_id.lower()).one_or_none()

    @classmethod
    def find_by_aad_upn(cls, upn: str) -> "User | None":
        return cls.query.filter(db.func.lower(cls.aad_upn) == upn.lower()).one_or_none()

    def __repr__(self) -> str:  # pragma: no cover - diagnostic helper
        return f"<User {self.email!r} status={self.status.value}>"


class MFASetting(TimestampMixin, db.Model):
    """Stores per-user MFA preferences and secrets."""

    __tablename__ = "mfa_settings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    secret = db.Column(db.String(64), nullable=False)
    enabled = db.Column(db.Boolean, default=False, nullable=False)
    enrolled_at = db.Column(db.DateTime(timezone=True))
    last_verified_at = db.Column(db.DateTime(timezone=True))
    backup_codes = db.Column(db.JSON)

    user = db.relationship("User", back_populates="mfa_setting")

    def mark_enrolled(self) -> None:
        self.enabled = True
        self.enrolled_at = datetime.now(UTC)

    def mark_verified(self) -> None:
        self.last_verified_at = datetime.now(UTC)

    def __repr__(self) -> str:  # pragma: no cover - diagnostic helper
        return f"<MFASetting user_id={self.user_id} enabled={self.enabled}>"
