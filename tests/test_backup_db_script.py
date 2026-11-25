"""The backup container keeps the Postgres password out of argv and logs (decisions 20261125-0753, -0830)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_BACKUP_SCRIPT = _ROOT / "docker/backup-db.sh"
_ENTRYPOINT = _ROOT / "docker/backup/entrypoint.sh"

_ENCODED = "S3nt%40in%3Ael%2F%25pw"
_DECODED = "S3nt@in:el/%pw"
_LITERAL = "p@ss-S3ntinel"
_SENTINELS = (_ENCODED, _DECODED, _LITERAL)

pytestmark = pytest.mark.skipif(shutil.which("sh") is None, reason="needs a POSIX sh")


def _leaks(text: str) -> list[str]:
    return [s for s in _SENTINELS if s in text]


def _write_exe(path: Path, body: str) -> None:
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)


@pytest.fixture
def fakebin(tmp_path):
    """pg_dump records argv and PGPASSWORD; python records PGPASSWORD and runs the real one."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    record = tmp_path / "record.txt"
    _write_exe(
        bin_dir / "pg_dump",
        f'''printf 'pg_dump PGPASSWORD=%s ARGV=%s\\n' "${{PGPASSWORD-<unset>}}" "$*" >> "{record}"
for arg in "$@"; do
  case "$arg" in --file=*) printf 'dump\\n' > "${{arg#--file=}}" ;; esac
done
''',
    )
    _write_exe(
        bin_dir / "python",
        f'''printf 'python PGPASSWORD=%s\\n' "${{PGPASSWORD-<unset>}}" >> "{record}"
exec "{sys.executable}" "$@"
''',
    )
    return bin_dir, record


def _run_backup(tmp_path, bin_dir, database_url, **extra_env):
    env = {
        "PATH": f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin",
        "HOME": str(tmp_path),
        "BACKUP_DIR": str(tmp_path / "backups"),
        "DATABASE_URL": database_url,
        **extra_env,
    }
    return subprocess.run(["sh", str(_BACKUP_SCRIPT)], env=env, capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize(
    ("password", "expected"),
    [(_ENCODED, _DECODED), (_LITERAL, _LITERAL)],
)
def test_pg_dump_gets_password_via_env_only(tmp_path, fakebin, password, expected):
    bin_dir, record = fakebin
    result = _run_backup(tmp_path, bin_dir, f"postgresql+psycopg://app:{password}@db:5432/app")

    assert result.returncode == 0, result.stderr
    lines = record.read_text().splitlines()
    dumps = [line for line in lines if line.startswith("pg_dump ")]
    assert len(dumps) == 1
    pgpassword, _, argv = dumps[0].removeprefix("pg_dump PGPASSWORD=").partition(" ARGV=")
    assert pgpassword == expected
    assert not _leaks(argv) and "postgresql://app@db:5432/app" in argv
    # Not exported: no python call (URI split, status writer) inherits it.
    assert all(line == "python PGPASSWORD=<unset>" for line in lines if line.startswith("python "))
    assert not _leaks(result.stdout + result.stderr)
    assert list((tmp_path / "backups").glob("pg_dump-*.sql.gz"))


def test_uri_without_password_keeps_existing_pgpassword(tmp_path, fakebin):
    bin_dir, record = fakebin
    result = _run_backup(tmp_path, bin_dir, "postgresql://app@db/app", PGPASSWORD="from-env")

    assert result.returncode == 0, result.stderr
    assert "pg_dump PGPASSWORD=from-env ARGV=postgresql://app@db/app " in record.read_text()


def test_unsupported_scheme_error_has_no_password(tmp_path, fakebin):
    bin_dir, _ = fakebin
    result = _run_backup(tmp_path, bin_dir, f"mysql://app:{_ENCODED}@db/app")

    assert result.returncode == 1
    assert "Unsupported or unknown DB URI scheme: mysql" in result.stderr
    assert not _leaks(result.stdout + result.stderr)


def test_entrypoint_pg_isready_gets_no_credentials(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    record = tmp_path / "pg_isready.txt"
    _write_exe(bin_dir / "pg_isready", f'printf \'%s\\n\' "$*" >> "{record}"\nexit 0\n')
    _write_exe(bin_dir / "sleep", "exit 1\n")  # ends the endless backup loop after one pass (set -e)
    env = {
        "PATH": f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin",
        "HOME": str(tmp_path),
        "DATABASE_URL": f"postgresql+psycopg://app:{_LITERAL}@db:5432/app",
    }
    result = subprocess.run(["sh", str(_ENTRYPOINT)], env=env, capture_output=True, text=True, timeout=60)

    argv = record.read_text()
    assert argv.startswith("-d postgresql://db:5432/app ")
    assert not _leaks(argv + result.stdout + result.stderr)
