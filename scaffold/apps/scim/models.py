"""SCIM token model."""

from __future__ import annotations

from datetime import datetime, UTC

from ...extensions import db


def utc_now() -> datetime:
    return datetime.now(UTC)


class SCIMToken(db.Model):
    """Long-lived bearer tokens for SCIM provisioning access.

    Raw token values are never stored; only the SHA-256 hex digest is persisted.
    """

    __tablename__ = "scim_tokens"

    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(128), unique=True, nullable=False)
    description = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    last_used_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SCIMToken id={self.id} active={self.is_active}>"
