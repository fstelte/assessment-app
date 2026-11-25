---
feature: 20261125-075107-postgres-passwords-visible-logging
status: planned
created: 2026-11-25
decisions:
  - 20261125-0753-pg-password-via-pgpassword-env
  - 20261125-0800-wait-for-db-masked-url-on-parse-error
  - 20261125-0805-pg-credential-helpers-inline-per-script
  - 20261125-0830-pg-password-checklist-gap-resolutions
---

# Postgres password no longer visible in logs Design

## Overview

The Postgres password from `DATABASE_URL` / `SQLALCHEMY_DATABASE_URI` shows up in
the restore container log, the backup container log and (when the URL can't be parsed)
the app container log. It is also saved in the restore state file and visible in `ps`
while `psql`/`pg_dump`/`pg_restore` run. The fix removes the password from the
command-line URI and gives it to the client tools through `PGPASSWORD`, so there is
nothing left to leak. The one place that prints a URL that can't be parsed masks the
userinfo instead. Security fix, no schema change, no new environment variables.

## User Stories

- As an operator, I want `docker logs` of the restore, backup and app containers to
  contain no database password, so that sharing or shipping logs doesn't leak it.
- As an operator, I want a clear hint when `DATABASE_URL` can't be parsed, without
  the password being printed, so that I can fix the URL safely.
- As an administrator, I want the restore state file and error messages to contain no
  password, so that the status shown or stored after a failed restore is safe.

## Leak inventory (what this design fixes)

| # | Where | Leak | Fix |
|---|---|---|---|
| 1 | `docker/restore/restore_db.py` `run_command` | `executing: psql postgresql://u:PW@...` (terminate sessions, drop, create, restore) | Stripped URI + `PGPASSWORD` |
| 2 | `restore_db.py` `main` `restore failed: {exc}` | `CalledProcessError` text includes argv | Fixed by #1 (argv has no password) |
| 3 | `restore_db.py` `rotate_session_tokens` → state file `session_rotation.error` | Same exception text, logged and saved | Stripped URI + `PGPASSWORD` in `psql_scalar` |
| 4 | `docker/backup-db.sh` | `running pg_dump for postgresql://u:PW@...` | Stripped URI + `PGPASSWORD` |
| 5 | `docker/wait_for_db.py` | `invalid DATABASE_URL '<raw>': <ArgumentError with raw URL>` | Masked URL + hint, exception text not printed |
| 6 | `scaffold/apps/admin/backup_utils.py` `create_postgres_backup` | Password in `pg_dump` argv (`ps` only) | Stripped URI + `PGPASSWORD` |
| 7 | `docker/backup-db.sh` `fail "Unsupported or unknown DB URI scheme: $DB_URI"` | Full URI in the log on an unsupported scheme | Print only `$SCHEME` |
| 8 | `docker/backup/entrypoint.sh` `pg_isready -d "$PG_URI"` | Password in argv (`ps` only) on every container start | Drop the userinfo; `pg_isready` doesn't authenticate |

**Reviewed, no change needed:** `docker/restore/entrypoint.sh`, `docker/s3_upload.py`,
`migrations/env.py` (puts the URL with the password in the in-memory Alembic config, never
logs it), the app itself (SQLAlchemy prints `***`), and `docker/entrypoint.sh` (the env
loader's `KEY=value` output is captured into a variable, not printed). Nothing in `scaffold/`
reads `restore-state.json`. The SQLite paths (restore, backup, wait_for_db) are unchanged.

**Found, out of scope:** `backup-db.sh` passes `ENC_KEY` to `encrypt_backup.py` as an
argument (backup encryption key visible in `ps`). Follow-up.

## Components

### Shared behaviour of `pg_conn` (all three copies)
The `restore_db.py` helper, the `backup_utils.py` copy and the `backup-db.sh` snippet must
behave identically, and their tests use the same cases:
1. `p = urlsplit(uri)`. Python takes the userinfo up to the **last** `@` of the netloc
   and the username up to the first `:`, so a literal `@` in the password works.
2. `p.password is None` → URI unchanged, `env = dict(os.environ)` (a `.pgpass` file or a
   `PGPASSWORD` already in the environment keeps working as today).
3. Otherwise: `userinfo, _, hostport = p.netloc.rpartition("@")`; the new netloc is
   `userinfo.partition(":")[0] + "@" + hostport`, or just `hostport` when the user is empty.
   The user stays percent-encoded as written. Path, query (`sslmode=…`) and fragment kept.
   `env = {**os.environ, "PGPASSWORD": unquote(p.password)}`.
4. A literal `/`, `?` or `#` in the password can't be split by `urlsplit`. Such URLs must
   be encoded (docs); the helper doesn't try to repair them.

### Restore container: `docker/restore/restore_db.py`
- New inline helper `pg_conn(uri) -> tuple[str, dict]` as specified above.
- `restore_postgres` calls it once on the normalized URI. The admin URI (`/postgres`)
  is derived from the **stripped** URI. `terminate_pg_sessions`, `recreate_pg_database`
  and the final `pg_restore`/`psql` pass `env` to `run_command` (it already accepts it).
- `psql_scalar` (used by `rotate_session_tokens`) uses the helper as well.
- `run_command` keeps logging `executing: ...`; the line is now safe.

### Backup container: `docker/backup-db.sh`
- After `PG_URI` is built: two inline `python3 -c` calls read the URI from an
  environment variable (`PG_URI_IN="$PG_URI" python3 -c …`, never argv). The first prints
  the stripped URI. The second writes the decoded password with `sys.stdout.write`, without
  a newline, and exits 1 when there is none. Two separate calls, so a password containing a
  newline survives (`$(…)` strips only trailing newlines; a password ending in a newline
  is not supported).
- `pg_dump` gets the password as a command prefix, `PGPASSWORD="$PG_PASS" pg_dump …`,
  only when there is one. It is **not exported**, so `encrypt_backup.py`, `s3_upload.py`
  and the status writer don't inherit it.
- The `running pg_dump for ...` line now prints the stripped URI.
- `fail "Unsupported or unknown DB URI scheme: $DB_URI"` prints only `$SCHEME`.

### Backup container start: `docker/backup/entrypoint.sh`
- `pg_isready` only checks whether the server accepts connections and doesn't
  authenticate. The URI becomes `$SCHEME://${rest##*@}`: everything up to the last `@` is
  dropped (POSIX parameter expansion; no `@` → unchanged). No password needed.

### App startup: `docker/wait_for_db.py`
- New inline helper `_mask_url(s)`: find `://`, then the **last** `@` after it. The part
  between is the userinfo. If it contains `:`, everything from the first `:` to the `@`
  becomes `:***`. Results: `user:pw@h` → `user:***@h`, `user:@h` → `user:***@h`,
  `:pw@h` → `:***@h`, `user@h` → unchanged, no `@` or no `://` → unchanged.
- Parse failure prints `invalid DATABASE_URL '<masked>'; URL-encode special
  characters in the password (e.g. @ -> %40)`, without `{exc}`: the exception only repeats
  the raw URL, so it adds nothing.
- Every other line that prints an exception (`database ensure timed out …: {exc}`,
  `database timed out …: {exc}`, `database bootstrap failed: {exc}`) prints
  `_mask_url(str(exc))`. Those exceptions are not known to contain the URL, so the text is
  kept for debugging and masked as a precaution.

### App manual backup: `scaffold/apps/admin/backup_utils.py`
- `create_postgres_backup` uses its own copy of the `pg_conn` helper and passes `env`
  to `subprocess.run`. The `pg_dump failed: {stderr}` message (flashed in the admin UI)
  stays: libpq error messages never repeat the password, and the password is no longer in
  the command that `pg_dump` could print. Accepted assumption, no test (it would need a
  real libpq).

### Documentation and release
- `docs/deployment.md`:
  - (a) **Password characters.** The example compose files build `DATABASE_URL` from the
    raw `POSTGRES_PASSWORD`, and Postgres uses that same raw value. So the password must
    contain only URL-safe characters (`A–Z a–z 0–9 - . _ ~`). With your own `DATABASE_URL`,
    other characters must be percent-encoded (`@` → `%40`).
  - (b) The restore and backup tools get the password through `PGPASSWORD` for the
    client process only. It's no longer in logs or process arguments.
  - (c) **After upgrading, rotate the password:** set a new password on the role with
    `\password <user>` in an interactive `psql` in the `postgres` container (not
    `ALTER ROLE … PASSWORD '…'` on the command line, which would land in shell history).
    Then update `POSTGRES_PASSWORD` / `DATABASE_URL` in every env file that the web,
    db-backup and db-restore services read, and recreate those containers.
    `POSTGRES_PASSWORD` only takes effect when the data volume is first created, so
    changing it alone doesn't change the role's password.
  - (d) **Old copies:** the password may still be in `docker logs` output (the json log files
    under `/var/lib/docker/containers/`), in any log shipper or SIEM that collected container
    logs, and in `restore-state.json` (`last_processed.session_rotation.error`). Rotating
    makes those copies worthless. Clean them up where possible.
- `specs/<branch>/release-notes.md`, a row in `docs/history.md`, and a version bump in
  `pyproject.toml` (next patch release), marked as a security fix.

## Data Model

No change. The restore state file keeps its shape; `session_rotation.error` just no
longer contains a password.

## API/Interface

- `restore_db.pg_conn(uri: str) -> tuple[str, dict[str, str]]`
- `backup_utils._pg_conn(uri: str) -> tuple[str, dict[str, str]]` (private copy)
- `wait_for_db._mask_url(value: str) -> str`
- No route, form, template or translation changes.

## Edge cases

- **No password in the URI** (peer/trust auth, or `PGPASSWORD` already set in the
  container): URI and environment unchanged.
- **Percent-encoded password** (`p%40ss`): decoded to `p@ss` for `PGPASSWORD`.
- **Empty password** (`user:@host`): `PGPASSWORD=""` set; same effect as today.
- **IPv6 host** (`[::1]:5432`): netloc rebuilt from the part after the last `@`, so
  brackets are kept.
- **`PGPASSWORD` already in the environment and a password in the URI**: the URI's
  password wins for the child, as it does today.

## Testing

**Feature-wide acceptance:** for every path in the leak inventory, no test finds either
sentinel form in stdout/stderr, logged lines, argv of a started process, exception text or
the state file.

**Sentinel passwords** (shared by all tests):
- Encoded: `S3nt%40in%3Ael%2F%25pw` in the URI, decoded `S3nt@in:el/%pw`. Tests assert
  that **neither** form appears.
- Literal `@`: `p@ss-S3ntinel` written unencoded in the URI (covers the last-`@` rule).

**Regression:** these per-path tests are the guard. There is no lint rule for new code;
accepted, see decision 0830.

- `tests/test_restore_db.py`: `pg_conn` cases (password, none, encoded, query, IPv6);
  `restore_postgres` with a fake `subprocess.run`: no argv and no log line contains
  the password, and `env["PGPASSWORD"]` is set; the rotation failure error contains no
  password.
- New test for `wait_for_db._mask_url` (password with `@`, `:`, `/`; no userinfo;
  no `://`) and for the parse-error message (capsys: no password).
- New test for `backup-db.sh`: run it with a fake `pg_dump` on `PATH` that records its
  argv and `PGPASSWORD`; assert the password is in neither argv nor stdout; a fake
  `python /app/encrypt_backup.py` step (or `ENC_KEY` unset) shows `PGPASSWORD` is not
  inherited; the unsupported-scheme `fail` line contains no password.
- `docker/backup/entrypoint.sh`: run it with `PATH` starting with a temp dir holding a fake
  `pg_isready` (records argv, exits 0) and a fake `sleep` (exits 1, so `set -e` ends the
  otherwise endless loop after one pass); assert no sentinel in the recorded argv or output.
- `create_postgres_backup` with a fake `subprocess.run`: argv has no password, env does.

## Out of scope

- Masking as a general log filter (decision A+B not chosen).
- Other secrets (S3 keys, `FIELD_ENCRYPTION_KEYS`, backup encryption keys). Not reported.
  One argv exposure found (`ENC_KEY` → `encrypt_backup.py`), left for a follow-up.
- Residual exposure, accepted: `PGPASSWORD` in `/proc/<pid>/environ` of the client process
  (readable only by the same user or root), and `DATABASE_URL` in `docker inspect`, compose
  files and env files (readable by whoever controls Docker on the host, which can read the
  database anyway). Threat model: people and systems that **read logs** or **list
  processes** should not learn the password.
- Removing already-leaked passwords from existing logs. That is an operator action
  documented in `docs/deployment.md`.

## Open Questions

- None.
