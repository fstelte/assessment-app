"""Session token rotation in the restore container (decision 20261107-0855, Task 4)."""

from __future__ import annotations

import importlib.util
import re
import sqlite3
import subprocess
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "docker/restore/restore_db.py"
_spec = importlib.util.spec_from_file_location("restore_db", _PATH)
restore_db = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(restore_db)


@pytest.fixture
def sqlite_db(tmp_path, monkeypatch):
    path = tmp_path / "app.db"
    monkeypatch.setenv("RESTORE_SQLITE_PATH", str(path))
    return path, "sqlite:///app.db"


def _tokens(path: Path) -> list[str]:
    with sqlite3.connect(path) as conn:
        return [row[0] for row in conn.execute("SELECT session_token FROM users ORDER BY id")]


def test_sqlite_tokens_are_rotated(sqlite_db):
    path, uri = sqlite_db
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, session_token TEXT UNIQUE NOT NULL)")
        conn.executemany("INSERT INTO users (session_token) VALUES (?)", [("a" * 64,), ("b" * 64,), ("c" * 64,)])
    before = _tokens(path)

    assert restore_db.rotate_session_tokens(uri) == {"status": "rotated", "users": 3}
    after = _tokens(path)
    assert not set(before) & set(after) and len(set(after)) == 3
    assert all(re.fullmatch(r"[0-9a-f]{64}", t) for t in after)


def test_backup_without_token_column_is_skipped(sqlite_db):
    path, uri = sqlite_db
    with sqlite3.connect(path) as conn:  # a backup from before migration 20261107_0001
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)")
        conn.execute("INSERT INTO users (email) VALUES ('a@x')")

    result = restore_db.rotate_session_tokens(uri)
    assert result["status"] == "skipped"


def test_postgres_uses_cryptographic_random(monkeypatch):
    calls: list[str] = []

    def fake_run(cmd, **kwargs):
        sql = cmd[-1]
        calls.append(sql)
        out = "1\n" if "information_schema" in sql else "4\n"
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

    monkeypatch.setattr(restore_db.subprocess, "run", fake_run)
    result = restore_db.rotate_session_tokens("postgresql+psycopg://u:p@db/app")

    assert result == {"status": "rotated", "users": 4}
    update = calls[-1]
    assert "gen_random_uuid()" in update and "random()" not in update.replace("gen_random_uuid()", "")


def test_rotation_failure_is_reported_not_raised(monkeypatch):
    def failing_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(2, cmd, stderr="connection refused")

    monkeypatch.setattr(restore_db.subprocess, "run", failing_run)
    result = restore_db.rotate_session_tokens("postgresql://u:p@db/app")
    assert result["status"] == "failed" and "error" in result


def test_process_backup_rotates_after_restore(sqlite_db, monkeypatch):
    path, uri = sqlite_db
    order: list[str] = []
    monkeypatch.setattr(restore_db, "restore_sqlite", lambda *a: order.append("restore"))
    monkeypatch.setattr(
        restore_db, "rotate_session_tokens", lambda u: order.append("rotate") or {"status": "rotated", "users": 0}
    )

    assert restore_db.process_backup(uri, path) == {"status": "rotated", "users": 0}
    assert order == ["restore", "rotate"]
