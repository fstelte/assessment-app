"""Core audit logging model."""

from __future__ import annotations

from ..extensions import db
from ..apps.identity.models import TimestampMixin


class AuditLog(TimestampMixin, db.Model):
    """Application-wide audit log entry."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    actor_email = db.Column(db.String(255))
    actor_name = db.Column(db.String(255))
    actor_ip = db.Column(db.String(45))
    actor_user_agent = db.Column(db.String(255))
    event_type = db.Column(db.String(120), nullable=False)
    target_type = db.Column(db.String(120), nullable=False)
    target_id = db.Column(db.String(64))
    payload = db.Column(db.JSON)

    actor = db.relationship("User", foreign_keys=[actor_id])

    __table_args__ = (
        db.Index("ix_audit_logs_target", "target_type", "target_id"),
        db.Index("ix_audit_logs_event", "event_type"),
        db.Index("ix_audit_logs_actor", "actor_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover - diagnostic helper
        return f"<AuditLog event={self.event_type!r} target={self.target_type}:{self.target_id}>"
