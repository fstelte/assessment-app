---
type: decision
id: 20261125-0830-pg-password-checklist-gap-resolutions
date: 2026-11-25
status: accepted
supersedes: null
superseded_by: null
impacts:
  - docker/backup-db.sh
  - docker/backup/entrypoint.sh
  - docker/wait_for_db.py
  - docker/restore/restore_db.py
  - scaffold/apps/admin/backup_utils.py
  - docs/deployment.md
tags: [security, logging, postgres, backup, restore]
participants: [Ferry Stelte, Claude]
---

# Postgres password fix: resolutions for the security checklist gaps

## Context

The security checklist
(`specs/20261125-075107-postgres-passwords-visible-logging/checklists/security.md`)
found gaps in the design. The engineer asked, in `/minispec.analyze`, to resolve
them and check the list off. The resolutions below are defaults and can be
overridden before implementation.

## Decision

### Extra leaks (CHK001, CHK002, CHK003)
- `backup-db.sh`'s unsupported-scheme `fail` prints only `$SCHEME`.
- `docker/backup/entrypoint.sh` calls `pg_isready` with `$SCHEME://${rest##*@}`:
  userinfo dropped, because `pg_isready` doesn't authenticate.
- The design lists the paths reviewed without change. `ENC_KEY` as an argument
  to `encrypt_backup.py` is a known follow-up, out of scope.

### Backup script hand-off (CHK005, CHK007, CHK008)
- The password goes to `pg_dump` as a command prefix (`PGPASSWORD=… pg_dump …`)
  and is not exported, so later tools in the script don't inherit it.
- Two separate `python3 -c` calls (stripped URI; password via
  `sys.stdout.write`), both reading the URI from the environment. Embedded
  newlines survive; a trailing newline in the password is not supported.

### Helper and mask behaviour (CHK009, CHK010, CHK011, CHK012, CHK013)
- One behaviour spec for all three `pg_conn` copies (design §Shared behaviour),
  based on `urlsplit` (userinfo up to the last `@`, user up to the first `:`).
  Tests share the same cases.
- `_mask_url` results are fully specified for empty-password, no-user and
  no-password inputs.
- The parse error drops `{exc}` (it only repeats the URL). The other `{exc}`
  lines in `wait_for_db.py` are kept for debugging, masked as a precaution.
- Masking at log time is used only where the URL text itself has to be shown.
  The rejection of option B in [[20261125-0753-pg-password-via-pgpassword-env]]
  is about masking as the main mechanism, so this doesn't contradict it.

### Tests (CHK014, CHK015, CHK016, CHK022)
- Feature-wide acceptance: no sentinel in output, logs, argv, exception text or
  the state file for any inventory path.
- Sentinels: encoded `S3nt%40in%3Ael%2F%25pw` (decoded `S3nt@in:el/%pw`; both
  forms checked) and literal `p@ss-S3ntinel`.
- Accepted without a test: libpq stderr doesn't contain the password.
- Regression guard = the per-path tests. No lint rule for new code.

### Coverage (CHK006, CHK017, CHK018, CHK019, CHK020, CHK021)
- SQLite paths are unchanged.
- No password in the URI: env unchanged, so `.pgpass` and an existing
  `PGPASSWORD` keep working.
- Residual exposure and the threat model are written down in the design
  (§Out of scope) and in decision 0753.
- `.pgpass` / `PGPASSFILE` was considered and rejected (decision 0753).
- The docs give concrete rotation steps (`\password` in interactive psql, update
  every env file, recreate containers; `POSTGRES_PASSWORD` only applies on first
  volume init). They also list where old copies may remain (docker json logs,
  log shippers, `restore-state.json`).
- The docs warn that the example compose files put the raw `POSTGRES_PASSWORD`
  into `DATABASE_URL`, so the password must use URL-safe characters only.

## Consequences

### Positive
- ✅ Every inventory path has a concrete fix and a test, except `pg_dump` stderr
  (accepted assumption).

### Negative
- ⚠️ Task 2 grows by about 20 lines (entrypoint, `fail` line, extra tests).
- ⚠️ A password ending in a newline is not supported by the backup script.
