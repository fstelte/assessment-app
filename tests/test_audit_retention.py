from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest

from scaffold.extensions import db
from scaffold.core.audit import enforce_audit_retention
from scaffold.models import AuditLog


@pytest.fixture
def audit_app(app, tmp_path):
    with app.app_context():
        app.config["AUDIT_LOG_PATH"] = str(tmp_path / "audit.log")
        app.config["AUDIT_LOG_RETENTION_DAYS"] = 2
        yield app


def _add_audit_event(created_at: datetime) -> None:
    entry = AuditLog(
        event_type="test.event",
        target_type="test",
        target_id="123",
        payload={"created": created_at.isoformat()},
        created_at=created_at,
    )
    db.session.add(entry)
    db.session.commit()


def test_enforce_audit_retention_prunes_records_and_files(audit_app, tmp_path):
    with audit_app.app_context():
        recent = datetime.now(UTC)
        old = recent - timedelta(days=5)

        _add_audit_event(recent)
        _add_audit_event(old)

        log_dir = tmp_path
        active_log = log_dir / "audit.log"
        active_log.write_text("active")

        old_rotated = log_dir / "audit.log.1"
        old_rotated.write_text("old")
        old_ts = (recent - timedelta(days=5)).timestamp()
        os.utime(old_rotated, (old_ts, old_ts))

        recent_rotated = log_dir / "audit.log.2"
        recent_rotated.write_text("recent")

        result = enforce_audit_retention(retention_days=2)

        remaining = AuditLog.query.order_by(AuditLog.created_at.asc()).all()
        assert len(remaining) == 1
        assert datetime.fromisoformat(remaining[0].payload["created"]) >= recent - timedelta(seconds=1)

        assert not old_rotated.exists()
        assert active_log.exists()
        assert recent_rotated.exists()

        assert result["db_deleted"] == 1
        assert result["files_deleted"] == 1


def test_audit_retention_cli_command(audit_app, tmp_path):
    with audit_app.app_context():
        audit_app.config["AUDIT_LOG_PATH"] = str(tmp_path / "audit.log")
        recent = datetime.now(UTC)
        stale = recent - timedelta(days=10)

        _add_audit_event(recent)
        _add_audit_event(stale)

        active_log = tmp_path / "audit.log"
        active_log.write_text("active")

        old_rotated = tmp_path / "audit.log.1"
        old_rotated.write_text("old")
        stale_ts = stale.timestamp()
        os.utime(old_rotated, (stale_ts, stale_ts))

    runner = audit_app.test_cli_runner()
    result = runner.invoke(args=["audit-retention"])
    assert result.exit_code == 0
    assert "Removed" in result.output

    with audit_app.app_context():
        remaining = AuditLog.query.all()
        assert len(remaining) == 1
        assert not old_rotated.exists()
        assert active_log.exists()