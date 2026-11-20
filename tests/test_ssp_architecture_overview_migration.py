"""Migration 20261119_0001: architecture overview becomes a flat list of files.

Feature 20261119-182410-ssp-architecture-overview-multiple-files (Task 2).
Fixture from decision 20261120-0900, CHK016: SSP 1 has versions 1-3, SSP 2
has version 1, SSP 3 has none.
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

import pytest
import sqlalchemy as sa

_MIGRATION = Path(__file__).resolve().parents[1] / "migrations/versions/20261119_0001_architecture_overview_flat_list.py"
_TABLE = "ssp_architecture_overview_versions"

# Pre-migration shape of the table (SQLite), as created by 20260829_0003.
_PRE_SCHEMA = [
    "CREATE TABLE users (id INTEGER PRIMARY KEY)",
    "CREATE TABLE ssp_plans (id INTEGER PRIMARY KEY)",
    f"CREATE TABLE {_TABLE} ("
    "id INTEGER PRIMARY KEY, "
    "ssp_id INTEGER NOT NULL REFERENCES ssp_plans(id) ON DELETE CASCADE, "
    "version_number INTEGER NOT NULL, "
    "image_data BLOB NOT NULL, "
    "mime_type VARCHAR(20) NOT NULL, "
    "original_filename VARCHAR(255) NOT NULL, "
    "file_size_bytes INTEGER NOT NULL, "
    "uploaded_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL, "
    "uploaded_at DATETIME NOT NULL, "
    "CONSTRAINT uq_ssp_architecture_overview_version UNIQUE (ssp_id, version_number))",
]


def _load_migration():
    spec = importlib.util.spec_from_file_location("mig_20261119_0001", _MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(conn, fn):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    with Operations.context(MigrationContext.configure(conn)):
        fn()


def _insert(conn, ssp_id, version_number, filename, uploaded_at):
    columns = "ssp_id, image_data, mime_type, original_filename, file_size_bytes, uploaded_at"
    values = ":ssp_id, x'00', 'image/png', :filename, 1, :uploaded_at"
    params = {"ssp_id": ssp_id, "filename": filename, "uploaded_at": uploaded_at}
    if version_number is not None:
        columns += ", version_number"
        values += ", :version_number"
        params["version_number"] = version_number
    conn.execute(sa.text(f"INSERT INTO {_TABLE} ({columns}) VALUES ({values})"), params)  # nosec B608


def _rows(conn, columns="ssp_id, original_filename"):
    return conn.execute(sa.text(f"SELECT {columns} FROM {_TABLE} ORDER BY ssp_id, id")).fetchall()  # nosec B608


@pytest.fixture
def migrated(caplog):
    mig = _load_migration()
    engine = sa.create_engine("sqlite://")
    caplog.set_level(logging.INFO, logger="alembic.runtime.migration")
    with engine.begin() as conn:
        for statement in _PRE_SCHEMA:
            conn.execute(sa.text(statement))
        conn.execute(sa.text("INSERT INTO ssp_plans (id) VALUES (1), (2), (3)"))
        _insert(conn, 1, 1, "a1.png", "2026-01-01 10:00:00")
        _insert(conn, 1, 2, "a2.png", "2026-02-01 10:00:00")
        _insert(conn, 1, 3, "a3.png", "2026-03-01 10:00:00")
        _insert(conn, 2, 1, "b1.png", "2026-01-15 10:00:00")
        _run(conn, mig.upgrade)
    yield mig, engine
    engine.dispose()


def test_upgrade_keeps_only_the_current_version_per_ssp(migrated):
    _mig, engine = migrated
    with engine.connect() as conn:
        assert _rows(conn) == [(1, "a3.png"), (2, "b1.png")]


def test_upgrade_drops_version_number_and_its_constraint(migrated):
    _mig, engine = migrated
    with engine.connect() as conn:
        inspector = sa.inspect(conn)
        columns = {c["name"] for c in inspector.get_columns(_TABLE)}
        constraints = {c["name"] for c in inspector.get_unique_constraints(_TABLE)}

    assert "version_number" not in columns
    assert "uq_ssp_architecture_overview_version" not in constraints


def test_upgrade_logs_how_many_versions_were_pruned(migrated, caplog):
    # The upgrade runs in the fixture, so its log lands in the setup phase.
    messages = [record.getMessage() for record in caplog.get_records("setup")]
    assert "pruned 2 historical architecture overview versions across 1 SSPs" in messages


def test_downgrade_numbers_every_row_per_ssp_by_upload_time(migrated):
    mig, engine = migrated
    with engine.begin() as conn:
        # Added after the upgrade with an earlier upload time but a higher id,
        # so the numbering must follow uploaded_at, not id.
        _insert(conn, 2, None, "b0.png", "2026-01-01 09:00:00")
        _run(conn, mig.downgrade)
        rows = _rows(conn, "ssp_id, original_filename, version_number")
        version_column = next(c for c in sa.inspect(conn).get_columns(_TABLE) if c["name"] == "version_number")
        constraints = {c["name"] for c in sa.inspect(conn).get_unique_constraints(_TABLE)}

    assert rows == [(1, "a3.png", 1), (2, "b1.png", 2), (2, "b0.png", 1)]
    assert version_column["nullable"] is False
    assert "uq_ssp_architecture_overview_version" in constraints
