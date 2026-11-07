"""Tests for the partial backup restore feature (feature 002-partial-backup-restore)."""
from __future__ import annotations

import gzip
import io
import json
import os
import sqlite3
import tempfile
from datetime import UTC, datetime
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
    # Password login forces MFA enrolment; authenticate the session directly
    # (same approach as conftest.login and _sign_in in test_admin_routes.py).
    user = User.query.filter_by(email="admin@example.com").one()
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True
        sess["login_time"] = datetime.now(UTC).isoformat()


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


def _copy_escape(value) -> str:
    """Encode one value the way pg_dump writes it in COPY text format."""
    if value is None:
        return "\\N"
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def _make_pgsql_backup_gz(
    tables: dict[str, tuple[list[str], list[tuple]]] | None = None,
) -> bytes:
    """Return a gzip-compressed plain pg_dump SQL file with COPY data blocks.

    ``tables`` maps table_name -> (columns, rows). The first column is created
    as the integer primary key, the others as text.
    """
    if tables is None:
        tables = {"sample_data": (["id", "name"], [(1, "alpha"), (2, "beta")])}

    lines = ["-- pg_dump plain sql backup\n"]
    for table_name, (columns, rows) in tables.items():
        col_defs = ", ".join(
            [f"{columns[0]} integer PRIMARY KEY"] + [f"{c} text" for c in columns[1:]]
        )
        lines.append(f"CREATE TABLE public.{table_name} ({col_defs});\n")
        lines.append(f"COPY public.{table_name} ({', '.join(columns)}) FROM stdin;\n")
        for row in rows:
            lines.append("\t".join(_copy_escape(v) for v in row) + "\n")
        lines.append("\\.\n\n")

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

        backup_data = _make_pgsql_backup_gz({"reports": (["id", "title"], [(1, "R1")])})
        tables = inspect_pgsql_backup(backup_data)
        assert len(tables) >= 1
        assert any(t.table_name == "reports" for t in tables)

    def test_inspect_pgsql_identity_not_selected_by_default(self):
        from scaffold.apps.admin.backup_utils import inspect_pgsql_backup

        backup_data = _make_pgsql_backup_gz({"users": (["id", "email"], [(1, "a@b.com")])})
        tables = inspect_pgsql_backup(backup_data)
        users = next(t for t in tables if t.table_name == "users")
        assert users.selected_by_default is False

    def test_inspect_pgsql_row_count_is_estimate(self):
        from scaffold.apps.admin.backup_utils import inspect_pgsql_backup

        backup_data = _make_pgsql_backup_gz({"logs": (["id", "msg"], [(1, "x"), (2, "y")])})
        tables = inspect_pgsql_backup(backup_data)
        logs = next(t for t in tables if t.table_name == "logs")
        assert logs.row_count_kind == "estimate"
        assert logs.row_count_estimate == 2

    def test_inspect_pgsql_counts_adjacent_small_tables(self):
        """Each COPY block's rows are credited to its own table, even when blocks are close together."""
        from scaffold.apps.admin.backup_utils import inspect_pgsql_backup

        backup_data = _make_pgsql_backup_gz({
            "items": (["id", "name"], [(1, "a"), (2, "b"), (3, "c")]),
            "tags": (["id", "label"], [(1, "x")]),
        })
        counts = {t.table_name: t.row_count_estimate for t in inspect_pgsql_backup(backup_data)}
        assert counts == {"items": 3, "tags": 1}


class TestExtractCopyBlocks:
    def _extract(self, sql: str):
        from scaffold.apps.admin.backup_utils import _extract_copy_blocks

        return _extract_copy_blocks(sql)

    def test_multiple_tables(self):
        sql = gzip.decompress(
            _make_pgsql_backup_gz({
                "items": (["id", "name"], [(1, "a"), (2, "b")]),
                "tags": (["id", "label"], [(1, "x")]),
            })
        ).decode()
        blocks = self._extract(sql)
        assert blocks == {
            "items": (["id", "name"], "1\ta\n2\tb\n"),
            "tags": (["id", "label"], "1\tx\n"),
        }

    def test_quoted_identifiers_and_public_prefix(self):
        sql = 'COPY public."user" (id, "order", name) FROM stdin;\n1\t2\tz\n\\.\n'
        assert self._extract(sql) == {"user": (["id", "order", "name"], "1\t2\tz\n")}

    def test_empty_block(self):
        sql = "COPY public.items (id, name) FROM stdin;\n\\.\n"
        assert self._extract(sql) == {"items": (["id", "name"], "")}

    def test_line_starting_with_terminator_is_data(self):
        sql = "COPY public.items (id, name) FROM stdin;\n\\.not-end\t1\n\\.\n"
        assert self._extract(sql) == {"items": (["id", "name"], "\\.not-end\t1\n")}

    def test_escapes_nulls_and_semicolons_untouched(self):
        sql = gzip.decompress(
            _make_pgsql_backup_gz({
                "items": (["id", "name"], [(1, "a;b\tc\nd\\e"), (2, None)]),
            })
        ).decode()
        _, data = self._extract(sql)["items"]
        assert data == "1\ta;b\\tc\\nd\\\\e\n2\t\\N\n"

    def test_no_copy_block_means_table_absent(self):
        sql = (
            "CREATE TABLE public.other (id integer);\n"
            "INSERT INTO items (id) VALUES (1);\n"
            "COPY public.unterminated (id) FROM stdin;\n1\n"
        )
        assert self._extract(sql) == {}


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
            build_inspection("backup.db.gz", b"not-valid-data", encryption_keys=[])


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

    def test_all_skipped_run_is_completed(self, tmp_path):
        """A run where every table is skipped (rows already present) is completed, not partial."""
        from scaffold.apps.admin.backup_utils import (
            BackupInspection,
            TableRestoreResult,
            orchestrate_partial_restore,
        )
        from datetime import UTC, datetime, timedelta

        insp = BackupInspection(
            inspection_id="skip-001",
            backup_filename="backup.sql.gz",
            backend="postgresql",
            source_format="sql.gz",
            encrypted=False,
            inspected_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
            table_summaries=[],
            parse_warnings=[],
            full_restore_only=False,
        )
        skipped = {
            t: TableRestoreResult(table_name=t, status="skipped", skipped_conflict_count=2)
            for t in ("items", "tags")
        }
        with patch("scaffold.apps.admin.backup_utils.check_schema_compatibility", return_value={}), \
             patch("scaffold.apps.admin.backup_utils.execute_partial_restore_pgsql", return_value=skipped):
            run = orchestrate_partial_restore(
                inspection=insp,
                file_bytes=b"",
                selected_tables=["items", "tags"],
                user_id=None,
                engine=MagicMock(),
                state_dir=tmp_path,
            )
        assert run.status == "completed"

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
# PostgreSQL partial restore from COPY blocks (needs a real Postgres)
# Run with: TEST_POSTGRES_URL=postgresql://user:pw@host:port/db pytest ...
# ---------------------------------------------------------------------------

_PG_URL = os.environ.get("TEST_POSTGRES_URL")
_PR_TABLES = "pr_child, pr_parent, pr_owner, pr_pair, pr_items, pr_tags"


@pytest.mark.skipif(not _PG_URL, reason="set TEST_POSTGRES_URL to run PostgreSQL restore tests")
class TestPgsqlRestore:
    @pytest.fixture
    def pg_engine(self):
        from sqlalchemy import create_engine, text as sa_text

        url = _PG_URL
        if url.startswith(("postgresql://", "postgres://")):
            url = "postgresql+psycopg://" + url.split("://", 1)[1]
        engine = create_engine(url)
        with engine.begin() as conn:
            conn.execute(sa_text(f"DROP TABLE IF EXISTS {_PR_TABLES}"))
            conn.execute(sa_text("CREATE TABLE pr_items (id serial PRIMARY KEY, name text)"))
            conn.execute(sa_text("CREATE TABLE pr_parent (id serial PRIMARY KEY, name text)"))
            conn.execute(sa_text("CREATE TABLE pr_tags (code text PRIMARY KEY, label text)"))
            conn.execute(sa_text("CREATE TABLE pr_owner (id serial PRIMARY KEY, name text)"))
            conn.execute(sa_text("CREATE TABLE pr_pair (a integer, b integer, PRIMARY KEY (a, b))"))
            conn.execute(sa_text(
                "CREATE TABLE pr_child (id serial PRIMARY KEY, "
                "parent_id integer NOT NULL REFERENCES pr_parent(id), "
                "owner_id integer REFERENCES pr_owner(id), name text, "
                "pair_a integer, pair_b integer, "
                "FOREIGN KEY (pair_a, pair_b) REFERENCES pr_pair(a, b))"
            ))
        yield engine
        with engine.begin() as conn:
            conn.execute(sa_text(f"DROP TABLE IF EXISTS {_PR_TABLES}"))
        engine.dispose()

    @staticmethod
    def _restore(engine, tables, selected):
        from scaffold.apps.admin.backup_utils import execute_partial_restore_pgsql

        return execute_partial_restore_pgsql(_make_pgsql_backup_gz(tables), selected, engine)

    @staticmethod
    def _rows(engine, sql):
        from sqlalchemy import text as sa_text

        with engine.connect() as conn:
            return [tuple(r) for r in conn.execute(sa_text(sql))]

    _ITEMS = {"pr_items": (["id", "name"], [(1, "alpha"), (2, "beta")])}

    def test_restores_rows_into_empty_table(self, pg_engine):
        result = self._restore(pg_engine, self._ITEMS, ["pr_items"])["pr_items"]
        assert (result.status, result.restored_row_count, result.skipped_conflict_count) == ("restored", 2, 0)
        assert self._rows(pg_engine, "SELECT id, name FROM pr_items ORDER BY id") == [(1, "alpha"), (2, "beta")]

    def test_rerun_skips_existing_rows(self, pg_engine):
        self._restore(pg_engine, self._ITEMS, ["pr_items"])
        result = self._restore(pg_engine, self._ITEMS, ["pr_items"])["pr_items"]
        assert (result.status, result.restored_row_count, result.skipped_conflict_count) == ("skipped", 0, 2)
        assert self._rows(pg_engine, "SELECT count(*) FROM pr_items") == [(2,)]

    def test_escapes_nulls_and_semicolons_round_trip(self, pg_engine):
        tricky = "a;b\tc\nd\\e'f"
        self._restore(pg_engine, {"pr_items": (["id", "name"], [(1, tricky), (2, None)])}, ["pr_items"])
        assert self._rows(pg_engine, "SELECT id, name FROM pr_items ORDER BY id") == [(1, tricky), (2, None)]

    def test_table_without_copy_block_is_skipped(self, pg_engine):
        result = self._restore(pg_engine, self._ITEMS, ["pr_items", "pr_parent"])["pr_parent"]
        assert result.status == "skipped"
        assert result.error_message == "Backup contains no data for this table."

    _BAD_PARENT = {"pr_parent": (["id", "name"], [("not-an-int", "mum")])}  # COPY fails on the integer id

    def test_failing_table_does_not_abort_others(self, pg_engine):
        results = self._restore(pg_engine, {**self._ITEMS, **self._BAD_PARENT}, ["pr_parent", "pr_items"])
        assert results["pr_parent"].status == "failed"
        assert results["pr_items"].status == "restored"
        assert self._rows(pg_engine, "SELECT count(*) FROM pr_items") == [(2,)]

    def test_parent_restored_before_child_regardless_of_selection(self, pg_engine):
        tables = {
            "pr_child": (["id", "parent_id", "name"], [(1, 1, "kid")]),
            "pr_parent": (["id", "name"], [(1, "mum")]),
        }
        results = self._restore(pg_engine, tables, ["pr_child", "pr_parent"])
        assert results["pr_parent"].status == "restored"
        assert results["pr_child"].status == "restored"

    # --- Dangling foreign keys (decision 20261106-1626) ---

    _CHILD_COLS = ["id", "parent_id", "owner_id", "name"]
    _MUM = {"pr_parent": (["id", "name"], [(1, "mum")])}

    @staticmethod
    def _assert_buckets(r, total):
        """Every backup row lands in exactly one bucket (decision 20261106-1635)."""
        assert r.restored_row_count + r.skipped_conflict_count + r.skipped_missing_parent_count == total

    def test_reference_to_unselected_table_is_cleared(self, pg_engine):
        tables = {**self._MUM, "pr_child": (self._CHILD_COLS, [(1, 1, 99, "kid")])}  # owner 99 missing
        r = self._restore(pg_engine, tables, ["pr_parent", "pr_child"])["pr_child"]
        assert (r.status, r.restored_row_count, r.cleared_reference_count, r.skipped_missing_parent_count) == (
            "restored", 1, 1, 0,
        )
        assert self._rows(pg_engine, "SELECT id, owner_id FROM pr_child") == [(1, None)]
        self._assert_buckets(r, 1)

    def test_not_null_reference_to_unselected_table_is_skipped(self, pg_engine):
        tables = {"pr_child": (self._CHILD_COLS, [(1, 99, None, "orphan")])}  # parent 99 missing
        r = self._restore(pg_engine, tables, ["pr_child"])["pr_child"]
        assert (r.status, r.restored_row_count, r.skipped_missing_parent_count, r.skipped_conflict_count) == (
            "skipped", 0, 1, 0,
        )
        self._assert_buckets(r, 1)

    def test_missing_row_in_selected_parent_is_skipped_not_cleared(self, pg_engine):
        tables = {**self._MUM, "pr_child": (self._CHILD_COLS, [(1, 2, None, "kid")])}  # parent 2 not in backup
        r = self._restore(pg_engine, tables, ["pr_parent", "pr_child"])["pr_child"]
        assert (r.restored_row_count, r.skipped_missing_parent_count, r.cleared_reference_count) == (0, 1, 0)
        self._assert_buckets(r, 1)

    def test_child_of_failed_parent_is_skipped_not_failed(self, pg_engine):
        tables = {**self._BAD_PARENT, "pr_child": (self._CHILD_COLS, [(1, 1, None, "kid")])}
        results = self._restore(pg_engine, tables, ["pr_parent", "pr_child"])
        assert results["pr_parent"].status == "failed"
        assert (results["pr_child"].status, results["pr_child"].skipped_missing_parent_count) == ("skipped", 1)
        self._assert_buckets(results["pr_child"], 1)

    # --- Order and counting (Task 2) ---

    def test_skip_wins_over_clear_on_the_same_row(self, pg_engine):
        tables = {"pr_child": (self._CHILD_COLS, [(1, 99, 99, "orphan")])}  # parent and owner missing
        r = self._restore(pg_engine, tables, ["pr_child"])["pr_child"]
        assert (r.skipped_missing_parent_count, r.cleared_reference_count) == (1, 0)
        self._assert_buckets(r, 1)

    def test_rerun_reports_conflict_not_cleared(self, pg_engine):
        tables = {**self._MUM, "pr_child": (self._CHILD_COLS, [(1, 1, 99, "kid")])}
        self._restore(pg_engine, tables, ["pr_parent", "pr_child"])
        r = self._restore(pg_engine, tables, ["pr_parent", "pr_child"])["pr_child"]
        assert (r.restored_row_count, r.cleared_reference_count, r.skipped_conflict_count) == (0, 0, 1)
        self._assert_buckets(r, 1)

    def test_partly_null_composite_key_is_not_checked(self, pg_engine):
        cols = ["id", "parent_id", "name", "pair_a", "pair_b"]
        tables = {**self._MUM, "pr_child": (cols, [(1, 1, "kid", 5, None)])}  # pr_pair empty
        r = self._restore(pg_engine, tables, ["pr_parent", "pr_child"])["pr_child"]
        assert (r.restored_row_count, r.skipped_missing_parent_count, r.cleared_reference_count) == (1, 0, 0)
        assert self._rows(pg_engine, "SELECT pair_a, pair_b FROM pr_child") == [(5, None)]
        self._assert_buckets(r, 1)

    @staticmethod
    def _insert_new_item(engine) -> int:
        from sqlalchemy import text as sa_text

        with engine.begin() as conn:
            return conn.execute(sa_text("INSERT INTO pr_items (name) VALUES ('new') RETURNING id")).scalar_one()

    def test_sequence_advanced_past_restored_ids(self, pg_engine):
        self._restore(pg_engine, self._ITEMS, ["pr_items"])  # ids 1, 2; sequence never used
        assert self._insert_new_item(pg_engine) == 3

    def test_sequence_never_moved_backwards(self, pg_engine):
        from sqlalchemy import text as sa_text

        for _ in range(5):
            self._insert_new_item(pg_engine)  # sequence now at 5
        with pg_engine.begin() as conn:
            conn.execute(sa_text("DELETE FROM pr_items"))
        self._restore(pg_engine, self._ITEMS, ["pr_items"])  # max restored id is 2
        assert self._insert_new_item(pg_engine) == 6

    def test_table_without_serial_key_restores(self, pg_engine):
        tables = {"pr_tags": (["code", "label"], [("a", "Alpha")])}
        result = self._restore(pg_engine, tables, ["pr_tags"])["pr_tags"]
        assert result.status == "restored"
        assert self._rows(pg_engine, "SELECT code, label FROM pr_tags") == [("a", "Alpha")]


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


# ---------------------------------------------------------------------------
# Encrypted uploads: key normalization and error messages (inspect route)
# ---------------------------------------------------------------------------


_ENC_BACKUPS = {
    "pg_dump-manual-20261106T070556Z.sql.gz.enc": lambda: _make_pgsql_backup_gz(
        {"sample_data": (["id", "name"], [(1, "alpha")])}
    ),
    "sqlite-manual-20261106T070556Z.db.gz.enc": lambda: _make_sqlite_backup_gz(),
}


class TestEncryptedInspect:
    @pytest.fixture
    def env(self, app, client, tmp_path, monkeypatch):
        from cryptography.fernet import Fernet

        app.config.update(BACKUP_DIR=str(tmp_path), BACKUP_ENCRYPTION_KEY=None)
        _create_admin(app)
        _login_admin(client)
        cached: dict[str, bytes] = {}
        monkeypatch.setattr(
            "scaffold.apps.admin.routes._store_backup_bytes",
            lambda key, data: cached.__setitem__(key, data),
        )
        return {"key": Fernet.generate_key().decode(), "cached": cached}

    @staticmethod
    def _inspect(client, filename, plain, key, typed=""):
        from scaffold.apps.admin.backup_crypto import encrypt_bytes

        return client.post(
            "/admin/backup/partial-restore/inspect",
            data={
                "backup_file": (io.BytesIO(encrypt_bytes(plain, key)), filename),
                "encryption_key": typed,
            },
            content_type="multipart/form-data",
        )

    @staticmethod
    def _flashes(client) -> str:
        with client.session_transaction() as sess:
            return " ".join(msg for _cat, msg in sess.get("_flashes", []))

    @pytest.mark.parametrize("filename", list(_ENC_BACKUPS))
    def test_key_without_padding_lists_tables(self, client, env, filename):  # scenario 1
        plain = _ENC_BACKUPS[filename]()
        resp = self._inspect(client, filename, plain, env["key"], env["key"].rstrip("="))
        assert resp.status_code == 200
        assert b"sample_data" in resp.data
        assert list(env["cached"].values()) == [plain]

    @pytest.mark.parametrize("filename", list(_ENC_BACKUPS))
    def test_invalid_key_says_invalid_not_ineligible(self, client, env, filename, caplog):  # scenarios 3, 10
        resp = self._inspect(client, filename, _ENC_BACKUPS[filename](), env["key"], "my-passphrase")
        assert resp.status_code == 302
        flashes = self._flashes(client)
        assert "not a valid backup key" in flashes
        assert "does not support partial restore" not in flashes
        assert "my-passphrase" not in flashes + caplog.text
        assert env["cached"] == {}

    @pytest.mark.parametrize("filename", list(_ENC_BACKUPS))
    def test_wrong_key_says_decrypt_failed(self, client, env, filename):  # scenario 4
        from cryptography.fernet import Fernet

        other = Fernet.generate_key().decode()
        resp = self._inspect(client, filename, _ENC_BACKUPS[filename](), env["key"], other)
        assert resp.status_code == 302
        assert "Decryption failed" in self._flashes(client)
        assert env["cached"] == {}

    @pytest.mark.parametrize("filename", list(_ENC_BACKUPS))
    def test_invalid_typed_key_falls_back_to_configured(self, app, client, env, filename):  # scenario 8
        app.config["BACKUP_ENCRYPTION_KEY"] = env["key"]
        plain = _ENC_BACKUPS[filename]()
        resp = self._inspect(client, filename, plain, env["key"], "my-passphrase")
        assert resp.status_code == 200
        assert b"sample_data" in resp.data
        assert list(env["cached"].values()) == [plain]

    @pytest.mark.parametrize("filename", list(_ENC_BACKUPS))
    def test_no_key_says_decrypt_failed(self, client, env, filename):  # scenario 9
        resp = self._inspect(client, filename, _ENC_BACKUPS[filename](), env["key"])
        assert resp.status_code == 302
        assert "Decryption failed" in self._flashes(client)
        assert env["cached"] == {}
