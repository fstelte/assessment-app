---
feature: 20261125-075107-postgres-passwords-visible-logging
status: planned
created: 2026-11-25
chunk_size: adaptive
total_tasks: 3
estimated_lines: 295
---

# Postgres password no longer visible in logs Tasks

## Overview

Implements [design.md](design.md): Postgres client tools get the password through
`PGPASSWORD` instead of the URI argument (restore container, backup script, app manual
backup), and `wait_for_db.py` prints a masked URL when `DATABASE_URL` can't be parsed.
Decisions: `20261125-0753-pg-password-via-pgpassword-env`,
`20261125-0800-wait-for-db-masked-url-on-parse-error`,
`20261125-0805-pg-credential-helpers-inline-per-script`,
`20261125-0830-pg-password-checklist-gap-resolutions`.

**Shared test sentinels** (design §Testing): encoded `S3nt%40in%3Ael%2F%25pw`
(decoded `S3nt@in:el/%pw`; assert neither form appears) and literal `p@ss-S3ntinel`.
Helper behaviour for all `pg_conn` copies: design §Shared behaviour of `pg_conn`.

## Task List

### Foundation

#### Task 1: Restore container passes the password through PGPASSWORD
- **Estimate:** ~80 lines
- **Files:** `docker/restore/restore_db.py`, `tests/test_restore_db.py`
- **Description:**
  1. Add `pg_conn(uri) -> tuple[str, dict]` per design §Shared behaviour of `pg_conn`.
  2. `restore_postgres`: call `pg_conn` once on the normalized URI; derive the
     `/postgres` admin URI from the **stripped** URI; pass `env` through
     `terminate_pg_sessions`, `recreate_pg_database` and the final `pg_restore`/`psql`
     to `run_command`.
  3. `psql_scalar`: use `pg_conn` and pass `env` to `subprocess.run`.
- **Depends on:** None
- **Acceptance:**
  - `pg_conn` cases: both sentinels, no password, empty password, no user (`:pw@h`),
    `?sslmode=require` kept, IPv6 `[::1]:5432` host.
  - With a fake `subprocess.run`, a full `restore_postgres` run: no argv and no
    captured log line contains the password; every call got `PGPASSWORD`.
  - `rotate_session_tokens` failure: `result["error"]` contains no password.
- **Evidence:** `pytest tests/test_restore_db.py` passes.

### Core Implementation

#### Task 2: Backup script, backup entrypoint, wait_for_db and app manual backup
- **Estimate:** ~165 lines
- **Files:** `docker/backup-db.sh`, `docker/backup/entrypoint.sh`, `docker/wait_for_db.py`,
  `scaffold/apps/admin/backup_utils.py`, new `tests/test_backup_db_script.py`,
  new `tests/test_wait_for_db.py`, `tests/test_admin_backup_crypto.py`
- **Description:**
  1. **backup-db.sh:** after `PG_URI` is built, two inline `python3 -c` calls read the
     URI from an environment variable (never argv): one prints the stripped URI, the
     other writes the decoded password with `sys.stdout.write` (exit 1 when none).
     Run `PGPASSWORD="$PG_PASS" pg_dump …` as a command prefix, only when there is a
     password; **do not export it**. The `running pg_dump for ...` line prints the
     stripped URI. The unsupported-scheme `fail` prints only `$SCHEME`.
  2. **backup/entrypoint.sh:** `pg_isready -d "$SCHEME://${rest##*@}"` (userinfo dropped).
  3. **wait_for_db.py:** add `_mask_url(value)` per design §App startup (results table).
     Parse failure prints
     `invalid DATABASE_URL '<masked>'; URL-encode special characters in the password (e.g. @ -> %40)`
     without `{exc}`. The three other `{exc}` lines print `_mask_url(str(exc))`.
  4. **backup_utils.py:** private `_pg_conn` (same behaviour as Task 1's helper) in
     `create_postgres_backup`; pass `env` to `subprocess.run`.
- **Depends on:** None (same helper behaviour as Task 1; do Task 1 first so the
  semantics are settled)
- **Acceptance:**
  - Backup script test: run `backup-db.sh` (sh) with a temp `BACKUP_DIR` and a fake
    `pg_dump` on `PATH` that writes its argv and `$PGPASSWORD` to a file and creates
    the output file; assert the decoded password is in `PGPASSWORD`, and no sentinel form
    is in argv or stdout, for both sentinels. `PGPASSWORD` is not visible to a later
    step (for example a fake `python` on `PATH` that records its env). An unsupported
    scheme with a sentinel password: the `fail` output has no sentinel. Skip when `sh`
    isn't available.
  - `backup/entrypoint.sh`: fake `pg_isready` (records argv, exits 0) and fake `sleep`
    (exits 1) on `PATH`; recorded argv and output contain no sentinel.
  - `_mask_url`: every row of the design's results table, plus both sentinels.
  - `main()` with an unparseable `DATABASE_URL` (capsys): exits 1, output contains the
    masked URL and the hint, no password.
  - `create_postgres_backup` with a fake `subprocess.run`: argv has no password,
    `env["PGPASSWORD"]` is set.
- **Evidence:** `pytest tests/test_backup_db_script.py tests/test_wait_for_db.py tests/test_admin_backup_crypto.py` passes.
  The entrypoint test can live in `test_backup_db_script.py`.

### Integration & Polish

#### Task 3: Documentation, release notes and version
- **Estimate:** ~50 lines
- **Files:** `docs/deployment.md`, `specs/20261125-075107-postgres-passwords-visible-logging/release-notes.md`,
  `docs/history.md`, `pyproject.toml`
- **Description:**
  1. `docs/deployment.md`: items (a)–(d) of design §Documentation and release: URL-safe
     password characters with the example compose files (percent-encode with your own
     `DATABASE_URL`); `PGPASSWORD` for the client process only; rotation steps
     (`\password` in interactive psql, update every env file, recreate web/db-backup/
     db-restore; `POSTGRES_PASSWORD` only applies on first volume init); where old copies
     remain (docker json logs, log shippers, `restore-state.json`).
  2. `release-notes.md` with What's new, Who can do what, Behaviour changes, Upgrade,
     Known limitations; marked as a security fix.
  3. New top row in `docs/history.md` linking
     `[Release notes](../specs/20261125-075107-postgres-passwords-visible-logging/release-notes.md)`;
     first check that every `specs/*/release-notes.md` newer than the last row is linked.
  4. `pyproject.toml` version `2026.11.6` → `2026.11.7`.
- **Depends on:** Tasks 1, 2
- **Acceptance:** Docs describe the behaviour as implemented; history row links resolve.
- **Evidence:** Full `pytest` run passes; `graphify update .` run.

## Notes

- The feature branch was created from `20261119-073747-affected-assets-list-add-overlay`,
  not `main`; rebase before the PR if this fix should ship on its own.
- The Python helper exists twice (`restore_db.py`, `backup_utils.py`) plus a shell
  snippet; the tests keep the behaviour aligned (decision 0805).
- Not in scope: general log masking filter, other secrets, removing passwords that already leaked.
- Follow-up: `backup-db.sh` passes `ENC_KEY` to `encrypt_backup.py` as an argument
  (backup encryption key visible in `ps`).

## Progress
- [x] Task 1: Restore container passes the password through PGPASSWORD
- [ ] Task 2: Backup script, backup entrypoint, wait_for_db and app manual backup
- [ ] Task 3: Documentation, release notes and version
