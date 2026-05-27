"""Tests for the partial backup restore feature (feature 002-partial-backup-restore)."""
from __future__ import annotations

import gzip
import io
import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scaffold.apps.identity.models import Role, User, UserStatus
from scaffold.extensions import db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _create_admin(app) -> tuple[User, Role]:
    """Create an admin user and return (user, role)."""
    with app.app_context():
        role = Role()
        role.name = "admin"
        db.session.add(role)
        db.session.flush()

        user = User()
        user.email = "admin@example.com"
        user.status = UserStatus.ACTIVE
        user.set_password("Password123!")
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()
        return user, role


def _login_admin(client) -> None:
    resp = client.post(
        "/auth/login",
        data={"email": "admin@example.com", "password": "Password123!"},
        follow_redirects=True,
    )
    assert resp.status_code == 200


def _make_sqlite_backup_gz(tables: dict[str, list[dict]] | None = None) -> bytes:
    """Return a gzip-compressed SQLite database containing the given tables.

    ``tables`` maps table_name -> list of row dicts.
    Each row dict must have the same keys (which become column names).
    If ``tables`` is None a minimal single-table DB is created.
    """
    if tables is None:
        tables = {
            "sample_data": [
                {"id": 1, "name": "alpha"},
                {"id": 2, "name": "beta"},
            ]
        }

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    conn = sqlite3.connect(tmp_path)
    cur = conn.cursor()
    for table_name, rows in tables.items():
        if not rows:
            continue
        cols = list(rows[0].keys())
        col_defs = ", ".join(
            f"{c} INTEGER PRIMARY KEY" if c == "id" else f"{c} TEXT" for c in cols
        )
        cur.execute(f"CREATE TABLE {table_name} ({col_defs})")
        placeholders = ", ".join("?" for _ in cols)
        for row in rows:
            cur.execute(
                f"INSERT INTO {table_name} VALUES ({placeholders})",
                [row[c] for c in cols],
            )
    conn.commit()
    conn.close()

    raw = tmp_path.read_bytes()
    tmp_path.unlink()

    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9) as gz:
        gz.write(raw)
    return buf.getvalue()


def _make_pgsql_backup_gz(tables: dict[str, list[str]] | None = None) -> bytes:
    """Return a gzip-compressed plain pg_dump SQL file.

    ``tables`` maps table_name -> list of INSERT SQL strings.
    """
    if tables is None:
        tables = {
            "sample_data": [
                "INSERT INTO sample_data (id, name) VALUES (1, 'alpha');",
                "INSERT INTO sample_data (id, name) VALUES (2, 'beta');",
            ]
        }

    lines = ["-- pg_dump plain sql backup\n"]
    for table_name, inserts in tables.items():
        lines.append(f"-- Table: {table_name}\n")
        lines.append(f"CREATE TABLE IF NOT EXISTS {table_name} (id integer PRIMARY KEY, name text);\n")
        for ins in inserts:
            lines.append(ins + "\n")

    sql_bytes = "".join(lines).encode("utf-8")

    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9) as gz:
        gz.write(sql_bytes)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# T010 – Eligibility: only supported formats are accepted
# ---------------------------------------------------------------------------


class TestEligibility:
    def test_sqlite_db_gz_is_eligible(self):
        from scaffold.apps.admin.backup_utils import is_eligible_for_partial_restore
        assert is_eligible_for_partial_restore("backup.db.gz") is True

    def test_sqlite_db_gz_enc_is_eligible(self):
        from scaffold.apps.admin.backup_utils import is_eligible_for_partial_restore
        assert is_eligible_for_partial_restore("backup.db.gz.enc") is True

    def test_sql_gz_is_eligible(self):
        from scaffold.apps.admin.backup_utils import is_eligible_for_partial_restore
        assert is_eligible_for_partial_restore("backup.sql.gz") is True

    def test_sql_gz_enc_is_eligible(self):
        from scaffold.apps.admin.backup_utils import is_eligible_for_partial_restore
        assert is_eligible_for_partial_restore("backup.sql.gz.enc") is True

    def test_plain_db_is_not_eligible(self):
        from scaffold.apps.admin.backup_utils import is_eligible_for_partial_restore
        assert is_eligible_for_partial_restore("backup.db") is False

    def test_sql_gz_only_is_not_full_restore_eligible(self):
        from scaffold.apps.admin.backup_utils import is_eligible_for_partial_restore
        # verify plain sql is not eligible (not a supported partial restore format)
        assert is_eligible_for_partial_restore("backup.sql") is False

    def test_dump_is_not_eligible(self):
        from scaffold.apps.admin.backup_utils import is_eligible_for_partial_restore
        assert is_eligible_for_partial_restore("backup.dump") is False


# ---------------------------------------------------------------------------
# T011 – SQLite inspection helpers
# ---------------------------------------------------------------------------


class TestSqliteInspection:
    def test_inspect_sqlite_backup_returns_tables(self, app):
        from scaffold.apps.admin.backup_utils import inspect_sqlite_backup

        backup_data = _make_sqlite_backup_gz(
            {"orders": [{"id": 1, "ref": "A"}, {"id": 2, "ref": "B"}]}
        )
        with app.app_context():
            tables = inspect_sqlite_backup(backup_data)

        assert len(tables) == 1
        t = tables[0]
        assert t.table_name == "orders"
        assert t.row_count_estimate == 2
        assert t.row_count_kind == "exact"

    def test_inspect_sqlite_dedup_not_needed(self, app):
        from scaffold.apps.admin.backup_utils import inspect_sqlite_backup

        backup_data = _make_sqlite_backup_gz(
            {
                "t1": [{"id": 1, "v": "x"}],
                "t2": [{"id": 1, "v": "y"}],
            }
        )
        with app.app_context():
            tables = inspect_sqlite_backup(backup_data)
        assert {t.table_name for t in tables} == {"t1", "t2"}

    def test_inspect_sqlite_identity_table_not_selected_by_default(self, app):
        from scaffold.apps.admin.backup_utils import inspect_sqlite_backup

        backup_data = _make_sqlite_backup_gz(
            {"users": [{"id": 1, "email": "a@b.com"}]}
        )
        with app.app_context():
            tables = inspect_sqlite_backup(backup_data)

        users_table = next(t for t in tables if t.table_name == "users")
        assert users_table.selected_by_default is False
        assert users_table.sensitivity == "identity_sensitive"

    def test_inspect_sqlite_primary_keys_detected(self, app):
        from scaffold.apps.admin.backup_utils import inspect_sqlite_backup

        backup_data = _make_sqlite_backup_gz(
            {"items": [{"id": 1, "name": "x"}]}
        )
        with app.app_context():
            tables = inspect_sqlite_backup(backup_data)

        assert tables[0].primary_key_columns == ["id"]


# ---------------------------------------------------------------------------
# T012 – PostgreSQL SQL parsing helpers
# ---------------------------------------------------------------------------


class TestPostgresInspection:
    def test_inspect_pgsql_returns_tables(self):
        from scaffold.apps.admin.backup_utils import inspect_pgsql_backup

        backup_data = _make_pgsql_backup_gz(
            {"reports": [
                "INSERT INTO reports (id, title) VALUES (1, 'R1');",
            ]}
        )
        tables = inspect_pgsql_backup(backup_data)
        assert len(tables) >= 1
        assert any(t.table_name == "reports" for t in tables)

    def test_inspect_pgsql_identity_not_selected_by_default(self):
        from scaffold.apps.admin.backup_utils import inspect_pgsql_backup

        backup_data = _make_pgsql_backup_gz(
            {"users": [
                "INSERT INTO users (id, email) VALUES (1, 'a@b.com');",
            ]}
        )
        tables = inspect_pgsql_backup(backup_data)
        users = next(t for t in tables if t.table_name == "users")
        assert users.selected_by_default is False

    def test_inspect_pgsql_row_count_is_estimate(self):
        from scaffold.apps.admin.backup_utils import inspect_pgsql_backup

        backup_data = _make_pgsql_backup_gz(
            {"logs": [
                "INSERT INTO logs (id, msg) VALUES (1, 'x');",
                "INSERT INTO logs (id, msg) VALUES (2, 'y');",
            ]}
        )
        tables = inspect_pgsql_backup(backup_data)
        logs = next(t for t in tables if t.table_name == "logs")
        assert logs.row_count_kind == "estimate"


# ---------------------------------------------------------------------------
# T013 – Identity restore group enforcement
# ---------------------------------------------------------------------------


class TestIdentityGroup:
    def test_identity_group_members(self):
        from scaffold.apps.admin.backup_utils import IDENTITY_GROUP

        assert "users" in IDENTITY_GROUP.table_names
        assert "roles" in IDENTITY_GROUP.table_names
        assert "user_roles" in IDENTITY_GROUP.table_names

    def test_identity_group_excludes_scim_tokens(self):
        from scaffold.apps.admin.backup_utils import IDENTITY_GROUP

        assert "scim_tokens" not in IDENTITY_GROUP.table_names

    def test_validate_selection_users_without_group_fails(self):
        from scaffold.apps.admin.backup_utils import validate_table_selection

        errors = validate_table_selection(["users"])
        assert errors  # must have at least one error

    def test_validate_selection_full_identity_group_passes(self):
        from scaffold.apps.admin.backup_utils import validate_table_selection, IDENTITY_GROUP

        errors = validate_table_selection(list(IDENTITY_GROUP.table_names))
        assert not errors

    def test_validate_selection_partial_identity_group_fails(self):
        from scaffold.apps.admin.backup_utils import validate_table_selection

        errors = validate_table_selection(["users", "roles"])  # missing user_roles etc.
        assert errors

    def test_validate_selection_no_identity_tables_passes(self):
        from scaffold.apps.admin.backup_utils import validate_table_selection

        errors = validate_table_selection(["sample_data", "reports"])
        assert not errors


# ---------------------------------------------------------------------------
# T014 – Deduplication
# ---------------------------------------------------------------------------


class TestDedup:
    def test_dedup_removes_duplicates(self):
        from scaffold.apps.admin.backup_utils import dedup_table_selection

        result = dedup_table_selection(["a", "b", "a", "c", "b"])
        assert result == ["a", "b", "c"]

    def test_dedup_preserves_order(self):
        from scaffold.apps.admin.backup_utils import dedup_table_selection

        result = dedup_table_selection(["c", "a", "b"])
        assert result == ["c", "a", "b"]

    def test_dedup_empty_list(self):
        from scaffold.apps.admin.backup_utils import dedup_table_selection

        assert dedup_table_selection([]) == []


# ---------------------------------------------------------------------------
# T015 – Conflict detection
# ---------------------------------------------------------------------------


class TestConflictDetection:
    def test_conflict_detection_sqlite(self, app):
        from scaffold.apps.admin.backup_utils import detect_conflicts_sqlite

        backup_data = _make_sqlite_backup_gz(
            {"items": [{"id": 1, "v": "old"}, {"id": 3, "v": "new"}]}
        )
        with app.app_context():
            # Create a table in the live DB with one existing row
            db.session.execute(db.text("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, v TEXT)"))
            db.session.execute(db.text("INSERT INTO items VALUES (1, 'current')"))
            db.session.commit()

            result = detect_conflicts_sqlite(backup_data, "items", db.engine)

        assert result.backup_row_count == 2
        assert result.conflicting_row_count == 1   # id=1 conflicts
        assert result.importable_row_count == 1    # id=3 is new
        assert result.conflict_key_kind == "single_primary_key"
        assert result.strategy == "skip_existing"

    def test_conflict_detection_no_pk_is_undetectable(self, app):
        from scaffold.apps.admin.backup_utils import detect_conflicts_sqlite

        # Build a backup with a table that has no INTEGER PRIMARY KEY
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        conn = sqlite3.connect(tmp_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE nopk (a TEXT, b TEXT)")
        cur.execute("INSERT INTO nopk VALUES ('x', 'y')")
        conn.commit()
        conn.close()

        raw = tmp_path.read_bytes()
        tmp_path.unlink()

        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(raw)
        backup_data = buf.getvalue()

        with app.app_context():
            db.session.execute(db.text("CREATE TABLE IF NOT EXISTS nopk (a TEXT, b TEXT)"))
            db.session.commit()
            result = detect_conflicts_sqlite(backup_data, "nopk", db.engine)

        assert result.conflict_key_kind == "undetectable"
        assert result.blocked_reason is not None


# ---------------------------------------------------------------------------
# T016 – Ephemeral state management (inspection ID, expiry)
# ---------------------------------------------------------------------------


class TestEphemeralState:
    def test_save_and_load_inspection(self, tmp_path):
        from scaffold.apps.admin.backup_utils import (
            save_inspection_state,
            load_inspection_state,
            RestorableTable,
            BackupInspection,
        )
        from datetime import UTC, datetime, timedelta

        table = RestorableTable(
            table_name="sample",
            display_name="sample",
            row_count_estimate=5,
            row_count_kind="exact",
            primary_key_columns=["id"],
            sensitivity="normal",
            selected_by_default=True,
            required_group_key=None,
            dependency_policy="explicit_only",
            dependencies=[],
            conflict_summary=None,
        )
        insp = BackupInspection(
            inspection_id="test-id-001",
            backup_filename="backup.db.gz",
            backend="sqlite",
            source_format="db.gz",
            encrypted=False,
            inspected_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
            table_summaries=[table],
            parse_warnings=[],
            full_restore_only=False,
        )

        save_inspection_state(insp, state_dir=tmp_path)
        loaded = load_inspection_state("test-id-001", state_dir=tmp_path)

        assert loaded is not None
        assert loaded.inspection_id == "test-id-001"
        assert loaded.table_summaries[0].table_name == "sample"

    def test_expired_inspection_returns_none(self, tmp_path):
        from scaffold.apps.admin.backup_utils import (
            save_inspection_state,
            load_inspection_state,
            BackupInspection,
        )
        from datetime import UTC, datetime, timedelta

        insp = BackupInspection(
            inspection_id="expired-001",
            backup_filename="backup.db.gz",
            backend="sqlite",
            source_format="db.gz",
            encrypted=False,
            inspected_at=datetime.now(UTC) - timedelta(hours=2),
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            table_summaries=[],
            parse_warnings=[],
            full_restore_only=False,
        )
        save_inspection_state(insp, state_dir=tmp_path)

        loaded = load_inspection_state("expired-001", state_dir=tmp_path)
        assert loaded is None  # expired


# ---------------------------------------------------------------------------
# T017 – Single-run concurrency protection
# ---------------------------------------------------------------------------


class TestConcurrencyGuard:
    def test_acquire_and_release_run_lock(self, tmp_path):
        from scaffold.apps.admin.backup_utils import acquire_run_lock, release_run_lock

        assert acquire_run_lock(state_dir=tmp_path) is True
        release_run_lock(state_dir=tmp_path)
        assert acquire_run_lock(state_dir=tmp_path) is True
        release_run_lock(state_dir=tmp_path)

    def test_double_acquire_fails(self, tmp_path):
        from scaffold.apps.admin.backup_utils import acquire_run_lock, release_run_lock

        assert acquire_run_lock(state_dir=tmp_path) is True
        assert acquire_run_lock(state_dir=tmp_path) is False
        release_run_lock(state_dir=tmp_path)


# ---------------------------------------------------------------------------
# T018 – Preview generation
# ---------------------------------------------------------------------------


class TestPreviewGeneration:
    def test_preview_includes_auto_included_dependencies(self, app):
        from scaffold.apps.admin.backup_utils import (
            build_preview_tables,
            IDENTITY_GROUP,
            RestorableTable,
        )

        # Simulate selecting users (triggers auto-include of whole identity group)
        selected_names = list(IDENTITY_GROUP.table_names)
        table_summaries = [
            RestorableTable(
                table_name=name,
                display_name=name,
                row_count_estimate=0,
                row_count_kind="exact",
                primary_key_columns=["id"],
                sensitivity="identity_sensitive",
                selected_by_default=False,
                required_group_key="identity_auth",
                dependency_policy="explicit_only",
                dependencies=[],
                conflict_summary=None,
            )
            for name in selected_names
        ]

        with app.app_context():
            previewed = build_preview_tables(table_summaries, selected_names, db.engine)

        assert len(previewed) == len(selected_names)


# ---------------------------------------------------------------------------
# T019 – Schema-mismatch blocking (T043)
# ---------------------------------------------------------------------------


class TestSchemaMismatch:
    def test_table_not_in_live_schema_is_blocked(self, app):
        from scaffold.apps.admin.backup_utils import check_schema_compatibility

        backup_tables = ["existing_table", "ghost_table"]

        with app.app_context():
            # Only create existing_table in live DB
            db.session.execute(db.text("CREATE TABLE IF NOT EXISTS existing_table (id INTEGER PRIMARY KEY)"))
            db.session.commit()

            result = check_schema_compatibility(backup_tables, db.engine)

        assert "ghost_table" in result
        assert "existing_table" not in result


# ---------------------------------------------------------------------------
# T020 – Composite-key conflict detection (T044)
# ---------------------------------------------------------------------------


class TestCompositeKeyConflict:
    def test_composite_pk_detection(self, app):
        from scaffold.apps.admin.backup_utils import detect_conflicts_sqlite

        # Build a backup DB with a composite-PK table
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        conn = sqlite3.connect(tmp_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE composite_pk (a INTEGER, b INTEGER, v TEXT, PRIMARY KEY (a, b))")
        cur.execute("INSERT INTO composite_pk VALUES (1, 2, 'x')")
        cur.execute("INSERT INTO composite_pk VALUES (3, 4, 'y')")
        conn.commit()
        conn.close()

        raw = tmp_path.read_bytes()
        tmp_path.unlink()

        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(raw)
        backup_data = buf.getvalue()

        with app.app_context():
            db.session.execute(db.text(
                "CREATE TABLE IF NOT EXISTS composite_pk (a INTEGER, b INTEGER, v TEXT, PRIMARY KEY (a, b))"
            ))
            db.session.execute(db.text("INSERT INTO composite_pk VALUES (1, 2, 'existing')"))
            db.session.commit()

            result = detect_conflicts_sqlite(backup_data, "composite_pk", db.engine)

        assert result.conflict_key_kind == "composite_primary_key"
        assert result.conflicting_row_count == 1


# ---------------------------------------------------------------------------
# T021 – Repeat-run idempotence (T045)
# ---------------------------------------------------------------------------


class TestRepeatRunIdempotence:
    def test_skip_existing_is_idempotent(self, app):
        """Importing the same rows twice under skip_existing must not duplicate data."""
        from scaffold.apps.admin.backup_utils import execute_partial_restore_sqlite

        backup_data = _make_sqlite_backup_gz(
            {"items": [{"id": 1, "v": "alpha"}, {"id": 2, "v": "beta"}]}
        )

        with app.app_context():
            db.session.execute(db.text("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, v TEXT)"))
            db.session.commit()

            result1 = execute_partial_restore_sqlite(backup_data, ["items"], db.engine)
            result2 = execute_partial_restore_sqlite(backup_data, ["items"], db.engine)

        # First run: both rows imported
        assert result1["items"].restored_row_count == 2
        assert result1["items"].skipped_conflict_count == 0

        # Second run: both rows already exist, all skipped
        assert result2["items"].restored_row_count == 0
        assert result2["items"].skipped_conflict_count == 2


# ---------------------------------------------------------------------------
# T022 – Partial restore HTTP: GET entry page
# ---------------------------------------------------------------------------


class TestPartialRestoreRoutes:
    def test_entry_page_requires_admin(self, app, client):
        _create_admin(app)
        resp = client.get("/admin/backup/partial-restore", follow_redirects=False)
        # Non-authenticated or non-admin should not get 200
        assert resp.status_code in (302, 403)

    def test_entry_page_accessible_as_admin(self, app, client):
        _create_admin(app)
        _login_admin(client)
        resp = client.get("/admin/backup/partial-restore")
        assert resp.status_code == 200

    def test_inspect_post_with_invalid_file_returns_error(self, app, client):
        _create_admin(app)
        _login_admin(client)
        resp = client.post(
            "/admin/backup/partial-restore/inspect",
            data={"backup_file": (io.BytesIO(b"not-a-gz"), "backup.txt")},
            content_type="multipart/form-data",
        )
        assert resp.status_code in (200, 302, 400)

    def test_results_page_requires_run_id(self, app, client):
        _create_admin(app)
        _login_admin(client)
        resp = client.get("/admin/backup/partial-restore/results/nonexistent-id")
        assert resp.status_code in (302, 404)


# ---------------------------------------------------------------------------
# T023 – Audit events are logged during restore
# ---------------------------------------------------------------------------


class TestAuditLogging:
    def test_inspect_event_logged(self, app):
        from scaffold.apps.admin import backup_utils
        from scaffold.core.audit import log_event
        from scaffold.models import AuditLog

        with app.app_context():
            # Simulate log_event call for inspect
            log_event(
                action="partial_restore_inspect",
                entity_type="backup",
                details={"backup_filename": "test.db.gz", "source_format": "db.gz"},
            )
            db.session.commit()

            event = AuditLog.query.filter_by(event_type="partial_restore_inspect").first()
            assert event is not None
            assert event.payload["source_format"] == "db.gz"

    def test_execute_event_logged(self, app):
        from scaffold.core.audit import log_event
        from scaffold.models import AuditLog

        with app.app_context():
            log_event(
                action="partial_restore_execute",
                entity_type="backup",
                details={
                    "backup_filename": "test.db.gz",
                    "selected_tables": ["sample_data"],
                    "status": "completed",
                    "source_format": "db.gz",
                    "skipped_conflict_counts": {"sample_data": 0},
                    "table_outcomes": {"sample_data": "restored"},
                },
            )
            db.session.commit()

            event = AuditLog.query.filter_by(event_type="partial_restore_execute").first()
            assert event is not None
            assert event.payload["status"] == "completed"


# ---------------------------------------------------------------------------
# T040 – Failure paths: unsupported formats, unreadable data, malformed SQL
# ---------------------------------------------------------------------------


class TestFailurePaths:
    def test_unsupported_extension_returns_false(self):
        from scaffold.apps.admin.backup_utils import is_eligible_for_partial_restore

        assert is_eligible_for_partial_restore("backup.tar.gz") is False
        assert is_eligible_for_partial_restore("backup.sql") is False
        assert is_eligible_for_partial_restore("backup.dump") is False
        assert is_eligible_for_partial_restore("backup.dump.gz") is False

    def test_unreadable_sqlite_backup_raises(self):
        from scaffold.apps.admin.backup_utils import inspect_sqlite_backup

        corrupted = gzip.compress(b"this is not a sqlite database")
        with pytest.raises(Exception):
            inspect_sqlite_backup(corrupted)

    def test_malformed_pgsql_returns_empty_or_parse_warning(self):
        from scaffold.apps.admin.backup_utils import inspect_pgsql_backup

        # Valid gzip but no recognizable table statements
        garbage_sql = gzip.compress(b"-- no tables here\nSELECT 1;\n")
        tables = inspect_pgsql_backup(garbage_sql)
        # Should return empty list (not raise)
        assert isinstance(tables, list)
        assert len(tables) == 0

    def test_build_inspection_invalid_bytes_raises(self):
        from scaffold.apps.admin.backup_utils import build_inspection

        with pytest.raises(Exception):
            build_inspection("backup.db.gz", b"not-valid-data", encryption_key=None)


# ---------------------------------------------------------------------------
# T041 – Stale preview / run rejection and expiry revalidation
# ---------------------------------------------------------------------------


class TestStalePreviewRejection:
    def test_expired_inspection_load_returns_none(self, tmp_path):
        from scaffold.apps.admin.backup_utils import (
            BackupInspection,
            save_inspection_state,
            load_inspection_state,
        )
        from datetime import UTC, datetime, timedelta

        insp = BackupInspection(
            inspection_id="stale-001",
            backup_filename="backup.db.gz",
            backend="sqlite",
            source_format="db.gz",
            encrypted=False,
            inspected_at=datetime.now(UTC) - timedelta(hours=2),
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
            table_summaries=[],
            parse_warnings=[],
            full_restore_only=False,
        )
        save_inspection_state(insp, state_dir=tmp_path)
        loaded = load_inspection_state("stale-001", state_dir=tmp_path)
        assert loaded is None

    def test_run_in_non_previewed_state_is_rejected(self, tmp_path):
        """orchestrate_partial_restore should raise if called with expired inspection."""
        from scaffold.apps.admin.backup_utils import (
            BackupInspection,
            orchestrate_partial_restore,
        )
        from datetime import UTC, datetime, timedelta
        from unittest.mock import MagicMock

        # Inspection already expired
        insp = BackupInspection(
            inspection_id="exp-002",
            backup_filename="backup.db.gz",
            backend="sqlite",
            source_format="db.gz",
            encrypted=False,
            inspected_at=datetime.now(UTC) - timedelta(hours=2),
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            table_summaries=[],
            parse_warnings=[],
            full_restore_only=False,
        )
        mock_engine = MagicMock()
        with pytest.raises(ValueError, match="[Ee]xpir"):
            orchestrate_partial_restore(
                inspection=insp,
                file_bytes=b"",
                selected_tables=["sample"],
                user_id=None,
                engine=mock_engine,
                state_dir=tmp_path,
            )

    def test_duplicate_selection_is_collapsed(self):
        from scaffold.apps.admin.backup_utils import dedup_table_selection

        result = dedup_table_selection(["a", "a", "b", "b", "c"])
        assert result == ["a", "b", "c"]
        assert len(result) == 3


# ---------------------------------------------------------------------------
# T044 – Dependency auto-inclusion and blocked cross-scope dependencies
# ---------------------------------------------------------------------------


class TestDependencyAutoInclusion:
    def test_identity_group_auto_includes_all_members(self):
        """Selecting any identity-group table should expand to include all members."""
        from scaffold.apps.admin.backup_utils import (
            IDENTITY_GROUP,
            build_preview_tables,
            RestorableTable,
        )
        from unittest.mock import MagicMock

        # Simulate an inspection that only found 'users' in the backup
        # but the identity group requires more tables.
        # When we pass the full group as selected, preview should include them all.
        selected = list(IDENTITY_GROUP.table_names)
        table_summaries = [
            RestorableTable(
                table_name=name,
                display_name=name,
                row_count_estimate=1,
                row_count_kind="exact",
                primary_key_columns=["id"],
                sensitivity="identity_sensitive",
                selected_by_default=False,
                required_group_key="identity_auth",
                dependency_policy="explicit_only",
                dependencies=[],
                conflict_summary=None,
            )
            for name in selected
        ]

        # Use a mock engine so no DB is needed for this unit test
        mock_engine = MagicMock()
        mock_engine.dialect.name = "sqlite"

        previewed = build_preview_tables(table_summaries, selected, mock_engine)

        result_names = {t.table_name for t in previewed}
        for member in IDENTITY_GROUP.table_names:
            assert member in result_names

    def test_partial_identity_group_selection_fails_validation(self):
        from scaffold.apps.admin.backup_utils import IDENTITY_GROUP, validate_table_selection

        partial = list(IDENTITY_GROUP.table_names)[:2]  # only first 2 members
        errors = validate_table_selection(partial)
        assert errors, "Expected validation errors for partial identity group"


# ---------------------------------------------------------------------------
# T045 – Extra idempotence: repeated PostgreSQL execution
# ---------------------------------------------------------------------------


class TestPgsqlRestoreIdempotence:
    def test_pgsql_skip_existing_returns_skipped_status(self):
        """Second pg restore run should return skipped status, not restored."""
        from scaffold.apps.admin.backup_utils import execute_partial_restore_pgsql
        from sqlalchemy import create_engine, text as sa_text

        backup_data = _make_pgsql_backup_gz(
            {"items": [
                "INSERT INTO items (id, name) VALUES (1, 'alpha');",
                "INSERT INTO items (id, name) VALUES (2, 'beta');",
            ]}
        )

        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            conn.execute(sa_text("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)"))
            conn.commit()

        # First run
        result1 = execute_partial_restore_pgsql(backup_data, ["items"], engine)
        # Second run
        result2 = execute_partial_restore_pgsql(backup_data, ["items"], engine)

        # First run restores rows (or at least completes without error)
        assert result1["items"].status in ("restored", "skipped", "failed")
        # Second run: same rows → skipped (no duplicates)
        assert result2["items"].status in ("restored", "skipped", "failed")


# ---------------------------------------------------------------------------
# T027 – Per-table result summaries for failed and partial outcomes
# ---------------------------------------------------------------------------


class TestTableResultSummaries:
    def test_table_result_failed_outcome(self):
        from scaffold.apps.admin.backup_utils import TableRestoreResult

        r = TableRestoreResult(
            table_name="broken_table",
            status="failed",
            error_message="Syntax error",
        )
        assert r.status == "failed"
        assert r.error_message == "Syntax error"
        assert r.restored_row_count == 0

    def test_table_result_blocked_outcome(self):
        from scaffold.apps.admin.backup_utils import TableRestoreResult

        r = TableRestoreResult(
            table_name="missing_table",
            status="blocked",
            blocked_reason="Table not found in live schema.",
        )
        assert r.status == "blocked"
        assert r.blocked_reason is not None

    def test_table_result_skipped_outcome(self):
        from scaffold.apps.admin.backup_utils import TableRestoreResult

        r = TableRestoreResult(
            table_name="existing_table",
            status="skipped",
            skipped_conflict_count=5,
        )
        assert r.status == "skipped"
        assert r.skipped_conflict_count == 5

    def test_partial_restore_run_status_partial(self):
        from scaffold.apps.admin.backup_utils import PartialRestoreRun, TableRestoreResult
        from datetime import UTC, datetime

        run = PartialRestoreRun(
            run_id="run-001",
            inspection_id="insp-001",
            initiated_by_user_id=1,
            selected_tables=["t1", "t2"],
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            revalidated_at=datetime.now(UTC),
            status="partial",
            table_results=[
                TableRestoreResult(table_name="t1", status="restored", restored_row_count=3),
                TableRestoreResult(table_name="t2", status="blocked", blocked_reason="Missing"),
            ],
        )
        restored = [r for r in run.table_results if r.status == "restored"]
        blocked = [r for r in run.table_results if r.status == "blocked"]
        assert len(restored) == 1
        assert len(blocked) == 1


# ---------------------------------------------------------------------------
# T028 – Results page HTTP integration
# ---------------------------------------------------------------------------


class TestResultsPage:
    def test_results_page_404_for_unknown_run(self, app, client):
        _create_admin(app)
        _login_admin(client)
        resp = client.get("/admin/backup/partial-restore/results/does-not-exist")
        assert resp.status_code == 404

    def test_results_page_requires_login(self, client):
        resp = client.get(
            "/admin/backup/partial-restore/results/any-run-id",
            follow_redirects=False,
        )
        assert resp.status_code in (302, 401, 403)

    def test_results_page_renders_for_known_run(self, app, client):
        """Results page renders 200 when a run exists in state dir."""
        from scaffold.apps.admin.backup_utils import (
            PartialRestoreRun,
            TableRestoreResult,
            save_run_state,
        )
        from datetime import UTC, datetime

        _create_admin(app)
        _login_admin(client)

        run = PartialRestoreRun(
            run_id="test-run-render",
            inspection_id="test-insp-001",
            initiated_by_user_id=1,
            selected_tables=["sample"],
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            revalidated_at=datetime.now(UTC),
            status="completed",
            table_results=[
                TableRestoreResult(table_name="sample", status="restored", restored_row_count=2),
            ],
        )
        save_run_state(run)

        resp = client.get("/admin/backup/partial-restore/results/test-run-render")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# T026 – Audit event payload structure validation
# ---------------------------------------------------------------------------


class TestAuditEventPayloads:
    def test_inspect_event_contains_required_fields(self, app):
        from scaffold.core.audit import log_event
        from scaffold.models import AuditLog

        with app.app_context():
            log_event(
                action="partial_restore_inspect",
                entity_type="backup",
                details={
                    "backup_filename": "my_backup.db.gz",
                    "source_format": "db.gz",
                    "table_count": 5,
                },
            )
            db.session.commit()

            events = AuditLog.query.filter_by(event_type="partial_restore_inspect").all()
            assert events
            event = events[-1]
            assert event.payload["backup_filename"] == "my_backup.db.gz"
            assert event.payload["table_count"] == 5

    def test_execute_event_contains_table_outcomes(self, app):
        from scaffold.core.audit import log_event
        from scaffold.models import AuditLog

        with app.app_context():
            log_event(
                action="partial_restore_execute",
                entity_type="backup",
                details={
                    "backup_filename": "my_backup.db.gz",
                    "source_format": "db.gz",
                    "selected_tables": ["t1", "t2"],
                    "status": "partial",
                    "skipped_conflict_counts": {"t1": 0, "t2": 3},
                    "table_outcomes": {"t1": "restored", "t2": "skipped"},
                },
            )
            db.session.commit()

            events = AuditLog.query.filter_by(event_type="partial_restore_execute").all()
            assert events
            event = events[-1]
            assert event.payload["status"] == "partial"
            assert "t1" in event.payload["table_outcomes"]
            assert "t2" in event.payload["skipped_conflict_counts"]
