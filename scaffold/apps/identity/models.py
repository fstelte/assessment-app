"""Unified identity models shared across scaffold applications."""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import List

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ...extensions import db


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


class Role(TimestampMixin, db.Model):
    """Application role used for authorisation decisions."""

    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))

    users = db.relationship("User", secondary=user_roles, back_populates="roles")

    def __repr__(self) -> str:  # pragma: no cover - diagnostic helper
        return f"<Role {self.name!r}>"


def ensure_default_roles() -> None:
    """Make sure the core authorisation roles exist in the database."""

    created = False
    for name, description in _DEFAULT_ROLES.items():
        if Role.query.filter_by(name=name).first():
            continue
        role = Role(name=name, description=description)
        db.session.add(role)
        created = True

    if created:
        db.session.commit()


class User(TimestampMixin, UserMixin, db.Model):
    """Application user with status-driven lifecycle."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(255), index=True)  # Optional legacy username support
    first_name = db.Column(db.String(120))
    last_name = db.Column(db.String(120))
    password_hash = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum(UserStatus, name="user_status"), default=UserStatus.PENDING, nullable=False)
    is_service_account = db.Column(db.Boolean, default=False, nullable=False)
    last_login_at = db.Column(db.DateTime(timezone=True))
    activated_at = db.Column(db.DateTime(timezone=True))
    deactivated_at = db.Column(db.DateTime(timezone=True))
    theme_preference = db.Column(db.String(20), default="dark", nullable=False)

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
