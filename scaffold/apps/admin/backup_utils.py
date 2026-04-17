"""Python backup logic invoked by admin routes."""

from __future__ import annotations

import gzip
import json
import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from .backup_crypto import encrypt_bytes


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def get_backup_dir(app) -> Path:
    return Path(app.config.get("BACKUP_DIR", "/backups"))


def get_configured_key(app) -> str | None:
    """Return key from config setting, or from .encryption_key file, or None."""
    key = app.config.get("BACKUP_ENCRYPTION_KEY") or None
    if not key:
        key_file = get_backup_dir(app) / ".encryption_key"
        if key_file.exists():
            key = key_file.read_text().strip() or None
    return key


def save_encryption_key(backup_dir: Path, key: str) -> None:
    """Write key to .encryption_key file in the backup dir (shared volume)."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    key_file = backup_dir / ".encryption_key"
    key_file.write_text(key)
    key_file.chmod(0o600)


def read_backup_status(backup_dir: Path) -> dict:
    """Read backup-status.json if present."""
    status_file = backup_dir / "backup-status.json"
    if status_file.exists():
        try:
            return json.loads(status_file.read_text())
        except Exception:
            pass
    return {}


def write_backup_status(backup_dir: Path, last_file: Path) -> None:
    """Update backup-status.json after a manually triggered backup."""
    status_file = backup_dir / "backup-status.json"
    try:
        existing = json.loads(status_file.read_text()) if status_file.exists() else {}
    except Exception:
        existing = {}

    all_files = []
    try:
        all_files = sorted(
            [f for f in os.listdir(backup_dir)
             if os.path.isfile(os.path.join(backup_dir, f))
             and f not in {"backup-status.json", ".encryption_key"}],
            key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)),
            reverse=True,
        )
    except Exception:
        pass

    existing["last_backup"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    existing["last_file"] = str(last_file)
    existing["backups"] = all_files

    tmp = status_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(existing, indent=2))
    tmp.replace(status_file)


def create_sqlite_backup(db_uri: str, backup_dir: Path, encryption_key: str | None = None) -> Path:
    """
    Create a gzip-compressed SQLite backup. If encryption_key is provided,
    the .gz file is Fernet-encrypted and saved as .gz.enc.
    Returns the final backup file path.
    """
    db_path_str = db_uri.split("sqlite:///", 1)[-1] if "sqlite:///" in db_uri else db_uri.split("sqlite://", 1)[-1]
    db_path = Path(db_path_str)
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite DB not found at {db_path}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = _timestamp()
    out_gz = backup_dir / f"sqlite-manual-{stamp}.db.gz"

    with open(db_path, "rb") as f_in, gzip.open(out_gz, "wb", compresslevel=9) as f_out:
        shutil.copyfileobj(f_in, f_out)

    if encryption_key:
        data = out_gz.read_bytes()
        encrypted = encrypt_bytes(data, encryption_key)
        out_enc = out_gz.with_suffix(".gz.enc")
        out_enc.write_bytes(encrypted)
        out_gz.unlink()
        return out_enc

    return out_gz


def create_postgres_backup(db_uri: str, backup_dir: Path, encryption_key: str | None = None) -> Path:
    """
    Create a gzip-compressed pg_dump backup. If encryption_key is provided,
    the .gz file is Fernet-encrypted and saved as .gz.enc.
    Returns the final backup file path.
    """
    # Normalize SQLAlchemy URI to plain postgres://
    if "+" in db_uri.split("://")[0]:
        scheme, rest = db_uri.split("://", 1)
        db_uri = "postgresql://" + rest
    elif db_uri.startswith("postgres://"):
        db_uri = "postgresql://" + db_uri[len("postgres://"):]

    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = _timestamp()
    out_sql = backup_dir / f"pg_dump-manual-{stamp}.sql"
    out_gz = out_sql.with_suffix(".sql.gz")

    result = subprocess.run(
        ["pg_dump", db_uri, "--format=plain", "--no-owner", "--no-privileges", f"--file={out_sql}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {result.stderr}")

    with open(out_sql, "rb") as f_in, gzip.open(out_gz, "wb", compresslevel=9) as f_out:
        shutil.copyfileobj(f_in, f_out)
    out_sql.unlink()

    if encryption_key:
        data = out_gz.read_bytes()
        encrypted = encrypt_bytes(data, encryption_key)
        out_enc = out_gz.with_suffix(".gz.enc")
        out_enc.write_bytes(encrypted)
        out_gz.unlink()
        return out_enc

    return out_gz
