"""Utility used by Docker entrypoint to wait until the database is ready."""

from __future__ import annotations

import os
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.exc import OperationalError, ProgrammingError

DEFAULT_TIMEOUT = int(os.getenv("DB_STARTUP_TIMEOUT", "60"))
SLEEP_INTERVAL = int(os.getenv("DB_STARTUP_INTERVAL", "2"))


def _log(message: str) -> None:
    print(f"[wait-for-db] {message}", flush=True)


def _ensure_database(url: URL, deadline: float) -> None:
    backend = url.get_backend_name()
    database_name = url.database
    if not database_name:
        return

    admin_url: URL | None = None
    create_statement: str | None = None

    if backend in {"postgresql", "postgres"}:
        admin_url = url.set(database="postgres")
        create_statement = f'CREATE DATABASE "{database_name}"'
    else:
        return

    engine = create_engine(admin_url)
    try:
        while True:
            try:
                with engine.connect() as conn:
                    conn.execution_options(isolation_level="AUTOCOMMIT")
                    conn.execute(text(create_statement))
                _log(f"database '{database_name}' ensured on {backend}")
                break
            except OperationalError as exc:
                if time.time() >= deadline:
                    _log(f"database ensure timed out after {DEFAULT_TIMEOUT}s: {exc}")
                    raise
                _log("waiting for admin connection to ensure database...")
                time.sleep(SLEEP_INTERVAL)
            except ProgrammingError as exc:  # pragma: no cover - defensive runtime guard
                orig = getattr(exc, "orig", None)
                if backend in {"postgresql", "postgres"} and getattr(orig, "pgcode", None) == "42P04":
                    _log(f"database '{database_name}' already exists")
                    break
                if backend in {"postgresql", "postgres"} and str(exc).lower().startswith("(psycopg.errors.duplicatedatabase)"):
                    _log(f"database '{database_name}' already exists")
                    break
                raise
    finally:
        engine.dispose()


def wait_for_database(url: URL) -> None:
    if url.get_backend_name().startswith("sqlite"):
        _log("sqlite backend detected; no startup checks required")
        return

    deadline = time.time() + DEFAULT_TIMEOUT
    _ensure_database(url, deadline)
    engine = create_engine(url)

    while True:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                _log("database connection established")
                break
        except OperationalError as exc:
            if time.time() >= deadline:
                _log(f"database timed out after {DEFAULT_TIMEOUT}s: {exc}")
                raise SystemExit(1)
            _log("waiting for database to be ready...")
            time.sleep(SLEEP_INTERVAL)
        finally:
            engine.dispose()


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        _log("DATABASE_URL not set; falling back to sqlite")
        return

    try:
        url = make_url(database_url)
    except Exception as exc:  # pragma: no cover - defensive
        _log(f"invalid DATABASE_URL '{database_url}': {exc}")
        raise SystemExit(1)

    wait_for_database(url)
if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        _log(f"database bootstrap failed: {exc}")
        raise SystemExit(1)
