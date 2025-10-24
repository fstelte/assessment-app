"""Audit trail model."""

from __future__ import annotations

from ....extensions import db
from ...identity.models import TimestampMixin


class AuditTrail(TimestampMixin, db.Model):
    """Captures user facing audit events for compliance evidence."""

    __tablename__ = "csa_audit_trails"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    action = db.Column(db.String(120), nullable=False)
    entity_type = db.Column(db.String(120), nullable=False)
    entity_id = db.Column(db.String(64))
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))

    user = db.relationship("User")

    __table_args__ = (
        db.Index("ix_csa_audit_entity", "entity_type", "entity_id"),
        db.Index("ix_csa_audit_user", "user_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditTrail action={self.action!r} entity={self.entity_type}:{self.entity_id}>"
