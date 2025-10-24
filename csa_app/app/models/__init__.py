"""Database models package."""

from __future__ import annotations

from datetime import UTC, datetime

from ..extensions import db


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for defaults."""

    return datetime.now(UTC)


class TimestampMixin:
    """Reusable mixin that tracks create/update timestamps."""

    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


from .assessment import (  # noqa: E402
    Assessment,
    AssessmentAssignment,
    AssessmentDimension,
    AssessmentResponse,
    AssessmentResult,
    AssessmentStatus,
)
from .audit import AuditTrail  # noqa: E402
from .control import AssessmentTemplate, Control  # noqa: E402
from .user import MFASetting, Role, User, UserStatus  # noqa: E402

__all__ = [
    "TimestampMixin",
    "Assessment",
    "AssessmentAssignment",
    "AssessmentDimension",
    "AssessmentResponse",
    "AssessmentResult",
    "AssessmentStatus",
    "AuditTrail",
    "AssessmentTemplate",
    "Control",
    "MFASetting",
    "Role",
    "User",
    "UserStatus",
]
