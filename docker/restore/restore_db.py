from __future__ import annotations

import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import urlparse, urlunparse

try:  # docker client optional during linting
    import docker
    from docker.errors import DockerException
except Exception:  # pragma: no cover - docker client optional
    docker = None  # type: ignore[assignment]
    DockerException = Exception  # type: ignore[assignment]

SUPPORTED_EXTENSIONS = {".sql", ".sql.gz", ".dump", ".dump.gz", ".db", ".db.gz"}


def timestamp() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def log(message: str) -> None:
    print(f"[{timestamp()}] [restore] {message}", flush=True)


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception as exc:  # pragma: no cover - defensive
        log(f"failed to read state file {path}: {exc}; starting fresh")
        return {}


def save_state(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def get_db_uri() -> Optional[str]:
    return os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URL")


def detect_backend(db_uri: str) -> str:
    head = db_uri.split(":", 1)[0]
    return head.split("+")[0]


def normalize_postgres_uri(db_uri: str) -> str:
    if db_uri.startswith("postgresql+" ):
        return "postgresql://" + db_uri.split("://", 1)[1]
    if db_uri.startswith("postgres+"):
        return "postgresql://" + db_uri.split("://", 1)[1]
    if db_uri.startswith("postgres://"):
        return "postgresql://" + db_uri.split("://", 1)[1]
    return db_uri


def sqlite_target_path(db_uri: str) -> Path:
    raw = db_uri.split("sqlite://", 1)[1]
    raw = raw.lstrip("/")
    override = os.getenv("RESTORE_SQLITE_PATH")
    if override:
        target = Path(override)
    else:
        base = Path(os.getenv("RESTORE_SQLITE_BASE", "/app"))
        target = (base / raw).resolve()
    return target


def parse_container_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def resolve_docker_client() -> Optional[Any]:
    if docker is None:  # type: ignore[truthy-falsey]
        return None
    combined = ",".join(
        part for part in [os.getenv("RESTORE_STOP_CONTAINERS", ""), os.getenv("RESTORE_START_CONTAINERS", "")] if part
    )
    if not parse_container_list(combined):
        return None
    try:
        return docker.from_env()  # type: ignore[no-any-return]
    except Exception as exc:  # pragma: no cover - runtime dependent
        log(f"warning: could not connect to Docker API: {exc}")
        return None


def stop_containers(client: Optional[Any]) -> list[str]:
    names = parse_container_list(os.getenv("RESTORE_STOP_CONTAINERS", ""))
    stop_timeout = int(os.getenv("RESTORE_STOP_TIMEOUT", "30"))
    wait_after = int(os.getenv("RESTORE_STOP_WAIT_SECONDS", "5"))

    stopped: list[str] = []
    if not names:
        log("no containers configured to stop before restore")
        return stopped

    if client is None:
        log("docker client unavailable; cannot stop containers")
        return stopped

    for name in names:
        try:
            container = client.containers.get(name)
            container.reload()
            status = container.status
            if status not in {"created", "exited", "dead"}:
                log(f"stopping container {name} (status={status})")
                container.stop(timeout=stop_timeout)
                stopped.append(name)
            else:
                log(f"container {name} already stopped (status={status})")
        except DockerException as exc:  # pragma: no cover - runtime environment dependent
            log(f"could not stop container {name}: {exc}")
    if stopped and wait_after > 0:
        log(f"waiting {wait_after}s to drain connections")
        time.sleep(wait_after)
    return stopped


def start_containers(client: Optional[Any], names: Iterable[str]) -> None:
    names = list(names)
    if not names:
        return
    if client is None:
        log("docker client unavailable; cannot start containers")
        return
    wait_after = int(os.getenv("RESTORE_START_WAIT_SECONDS", "5"))
    for name in names:
        try:
            container = client.containers.get(name)
            log(f"starting container {name}")
            container.start()
        except DockerException as exc:  # pragma: no cover - runtime dependent
            log(f"could not start container {name}: {exc}")
    if wait_after > 0:
        log(f"waiting {wait_after}s for services to stabilise")
        time.sleep(wait_after)


def decompress_if_needed(path: Path) -> tuple[Path, bool]:
    if path.suffix == ".gz":
        tmp = Path(tempfile.mkstemp(prefix="restore-", suffix=path.with_suffix("").suffix)[1])
        log(f"decompressing {path} -> {tmp}")
        with gzip.open(path, "rb") as source, open(tmp, "wb") as target:
            shutil.copyfileobj(source, target)
        return tmp, True
    return path, False


def run_command(command: list[str], env: Optional[dict] = None) -> None:
    log(f"executing: {' '.join(command)}")
    subprocess.run(command, env=env, check=True)


def sanitize_sql_file(path: Path) -> tuple[Path, bool]:
    """Drop lines containing unsupported settings from plain SQL dumps."""

    if path.suffix.lower() != ".sql":
        return path, False

    removed = False
    with open(path, "r", encoding="utf-8") as source, tempfile.NamedTemporaryFile(
        "w",
        delete=False,
        prefix="restore-sanitized-",
        suffix=".sql",
        encoding="utf-8",
    ) as tmp:
        for line in source:
            if "transaction_timeout" in line:
                removed = True
                continue
            tmp.write(line)
    sanitized_path = Path(tmp.name)
    if not removed:
        sanitized_path.unlink(missing_ok=True)
        return path, False
    return sanitized_path, True


def restore_sqlite(db_uri: str, backup_path: Path) -> None:
    target = sqlite_target_path(db_uri)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path, was_temp = decompress_if_needed(backup_path)
    try:
        log(f"restoring SQLite database from {backup_path} -> {target}")
        shutil.copy2(temp_path, target)
    finally:
        if was_temp:
            temp_path.unlink(missing_ok=True)


def terminate_pg_sessions(pg_admin_uri: str, database: str) -> None:
    sql = (
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        "WHERE datname = %s AND pid <> pg_backend_pid();"
    )
    run_command([
        "psql",
        pg_admin_uri,
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        sql % (f"'{database}'"),
    ])


def recreate_pg_database(pg_admin_uri: str, database: str, owner: Optional[str]) -> None:
    drop_sql = f'DROP DATABASE IF EXISTS "{database}";'
    create_sql = f'CREATE DATABASE "{database}"'
    if owner:
        create_sql += f' WITH OWNER "{owner}"'
    create_sql += ';'
    run_command(["psql", pg_admin_uri, "-v", "ON_ERROR_STOP=1", "-c", drop_sql])
    run_command(["psql", pg_admin_uri, "-v", "ON_ERROR_STOP=1", "-c", create_sql])


def restore_postgres(db_uri: str, backup_path: Path) -> None:
    pg_uri = normalize_postgres_uri(db_uri)
    parsed = urlparse(pg_uri)
    database = parsed.path.lstrip("/") or "postgres"
    owner = parsed.username
    admin_path = parsed._replace(path="/postgres")
    pg_admin_uri = urlunparse(admin_path)

    terminate_pg_sessions(pg_admin_uri, database)
    recreate_pg_database(pg_admin_uri, database, owner)

    temp_path, was_temp = decompress_if_needed(backup_path)
    sanitized_path, was_sanitized = sanitize_sql_file(temp_path)
    try:
        if sanitized_path.suffix == ".dump":
            run_command([
                "pg_restore",
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
                "-d",
                pg_uri,
                str(sanitized_path),
            ])
        else:
            run_command([
                "psql",
                pg_uri,
                "-v",
                "ON_ERROR_STOP=1",
                "-f",
                str(sanitized_path),
            ])
    finally:
        if was_temp:
            temp_path.unlink(missing_ok=True)
        if was_sanitized:
            sanitized_path.unlink(missing_ok=True)


def process_backup(db_uri: str, backup_path: Path) -> None:
    backend = detect_backend(db_uri)
    if backend.startswith("sqlite"):
        restore_sqlite(db_uri, backup_path)
    elif backend in {"postgres", "postgresql"}:
        restore_postgres(db_uri, backup_path)
    else:
        raise RuntimeError(f"unsupported database backend '{backend}'")


def select_candidates(watch_dir: Path) -> list[Path]:
    if not watch_dir.exists():
        watch_dir.mkdir(parents=True, exist_ok=True)
        return []
    files: list[Path] = []
    for path in watch_dir.glob("**/*"):
        if not path.is_file():
            continue
        suffix = ''.join(path.suffixes[-2:]) if path.suffix == ".gz" else path.suffix
        if suffix not in SUPPORTED_EXTENSIONS:
            continue
        files.append(path)
    files.sort(key=lambda item: item.stat().st_mtime)
    return files


def new_backups(files: list[Path], state: dict) -> list[Path]:
    if not files:
        return []
    last = state.get("last_processed", {})
    last_mtime = last.get("mtime")
    last_path = last.get("path")
    fresh: list[Path] = []
    for path in files:
        stat = path.stat()
        if last_mtime is None:
            fresh.append(path)
        elif stat.st_mtime > float(last_mtime) + 1e-6:
            fresh.append(path)
        elif str(path) != last_path:
            fresh.append(path)
    return fresh


def main() -> None:
    watch_dir = Path(os.getenv("RESTORE_WATCH_DIR", "/restore"))
    state_file = Path(os.getenv("RESTORE_STATE_FILE", "/restore-state/restore-state.json"))
    poll_interval = int(os.getenv("RESTORE_POLL_INTERVAL", "30"))

    db_uri = get_db_uri()
    if not db_uri:
        log("No DATABASE_URL or SQLALCHEMY_DATABASE_URI configured; exiting")
        sys.exit(1)

    client = resolve_docker_client()

    state = load_state(state_file)
    log(f"watching directory {watch_dir} for new backups")

    while True:
        try:
            candidates = select_candidates(watch_dir)
            pending = new_backups(candidates, state)
            if pending:
                backup = pending[-1]
                log(f"detected backup file {backup} (pending {len(pending)})")
                stopped = stop_containers(client)
                try:
                    process_backup(db_uri, backup)
                    state["last_processed"] = {
                        "path": str(backup),
                        "mtime": backup.stat().st_mtime,
                        "completed_at": timestamp(),
                    }
                    try:
                        backup.unlink()
                        log(f"removed processed backup {backup}")
                    except Exception as cleanup_exc:  # pragma: no cover - filesystem dependent
                        log(f"warning: could not remove {backup}: {cleanup_exc}")
                    save_state(state_file, state)
                    log(f"restore completed from {backup}")
                except Exception as exc:
                    log(f"restore failed: {exc}")
                    save_state(state_file, state)
                finally:
                    restart_targets = list(stopped)
                    for name in parse_container_list(os.getenv("RESTORE_START_CONTAINERS", "")):
                        if name not in restart_targets:
                            restart_targets.append(name)
                    start_containers(client, restart_targets)
            time.sleep(poll_interval)
        except KeyboardInterrupt:  # pragma: no cover - manual shutdown
            log("restore watcher interrupted; exiting")
            break
        except Exception as exc:  # pragma: no cover - defensive
            log(f"unexpected error: {exc}")
            time.sleep(max(poll_interval, 10))


if __name__ == "__main__":
    main()
