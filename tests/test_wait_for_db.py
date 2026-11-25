"""wait_for_db never prints the Postgres password (decisions 20261125-0800, -0830)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError

_PATH = Path(__file__).resolve().parents[1] / "docker/wait_for_db.py"
_spec = importlib.util.spec_from_file_location("wait_for_db", _PATH)
wait_for_db = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wait_for_db)

_ENCODED = "S3nt%40in%3Ael%2F%25pw"
_DECODED = "S3nt@in:el/%pw"
_LITERAL = "p@ss-S3ntinel"
_SENTINELS = (_ENCODED, _DECODED, _LITERAL)


def _leaks(text: str) -> list[str]:
    return [s for s in _SENTINELS if s in text]


@pytest.mark.parametrize(
    ("value", "masked"),
    [
        ("postgresql://user:pw@h/db", "postgresql://user:***@h/db"),
        ("postgresql://user:@h/db", "postgresql://user:***@h/db"),
        ("postgresql://:pw@h/db", "postgresql://:***@h/db"),
        ("postgresql://user@h/db", "postgresql://user@h/db"),
        ("postgresql://h/db", "postgresql://h/db"),
        ("not a url", "not a url"),
        (f"postgresql+psycopg://app:{_ENCODED}@db:5432/app", "postgresql+psycopg://app:***@db:5432/app"),
        (f"postgresql+psycopg://app:{_LITERAL}@db/app", "postgresql+psycopg://app:***@db/app"),
        (f"error for 'postgresql://app:{_ENCODED}@db/app'", "error for 'postgresql://app:***@db/app'"),
    ],
)
def test_mask_url(value, masked):
    assert wait_for_db._mask_url(value) == masked


@pytest.mark.parametrize(
    "database_url",
    [
        f"postgresql+psycopg://app:{_LITERAL}@db:5432/app",  # SQLAlchemy would split at the first '@'
        f"postgresql+psycopg://app:{_ENCODED}@db:notaport/app",  # make_url raises
    ],
)
def test_invalid_url_is_rejected_without_password(monkeypatch, capsys, database_url):
    monkeypatch.setenv("DATABASE_URL", database_url)
    with pytest.raises(SystemExit) as exc_info:
        wait_for_db.main()

    assert exc_info.value.code == 1
    out = capsys.readouterr().out
    assert "invalid DATABASE_URL 'postgresql+psycopg://app:***@db" in out
    assert "URL-encode special characters" in out
    assert not _leaks(out)


def test_timeout_error_is_masked(monkeypatch, capsys):
    class FakeEngine:
        def connect(self):
            raise OperationalError("SELECT 1", {}, Exception(f"bad postgresql://app:{_ENCODED}@db/app"))

        def dispose(self):
            pass

    monkeypatch.setattr(wait_for_db, "create_engine", lambda url: FakeEngine())
    monkeypatch.setattr(wait_for_db, "DEFAULT_TIMEOUT", 0)

    with pytest.raises(OperationalError):
        wait_for_db.wait_for_database(make_url("postgresql+psycopg://app@db/app"))
    out = capsys.readouterr().out
    assert "database ensure timed out" in out and "postgresql://app:***@db/app" in out
    assert not _leaks(out)
