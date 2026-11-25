---
type: checklist
domain: security
feature: 20261125-075107-postgres-passwords-visible-logging
created: 2026-11-25
status: completed
---

# Security Requirements Quality Checklist

**Purpose:** Validate that the requirements for keeping the Postgres password out of logs, error text, stored state and process arguments are complete, clear and consistent.
**Feature:** 20261125-075107-postgres-passwords-visible-logging

## Completeness

- [x] CHK001 - Does the leak inventory cover every place that prints `DB_URI`/`PG_URI`, including `fail "Unsupported or unknown DB URI scheme: $DB_URI"` in `docker/backup-db.sh:101`? [Gap, Design §Leak inventory]
  → Added as inventory #7; `fail` prints only `$SCHEME` (Design §Leak inventory, §Backup container).
- [x] CHK002 - Does the design cover `pg_isready -d "$PG_URI"` in `docker/backup/entrypoint.sh:37`, which puts the password in argv on every backup container start? [Gap, Design §Leak inventory]
  → Added as inventory #8; `pg_isready` gets `$SCHEME://${rest##*@}` (Design §Backup container start).
- [x] CHK003 - Does the design list which files and code paths were reviewed for the claim "no leak found in the code paths reviewed" (backup entrypoint, restore entrypoint, `s3_upload.py`, `encrypt_backup.py`, `migrations/env.py`)? [Completeness, Design §Out of scope]
  → Reviewed paths listed under the inventory; `ENC_KEY` argv noted as follow-up.
- [x] CHK004 - Are requirements defined for every log line in `wait_for_db.py` that interpolates an exception (`database ensure timed out ...: {exc}`, `database timed out ...: {exc}`), not just the parse-error and bootstrap-failed lines? [Completeness, Design §App startup]
  → All `{exc}` lines in `wait_for_db.py` print `_mask_url(str(exc))` (Design §App startup).
- [x] CHK005 - Does the design say whether `PGPASSWORD` must stay out of tools that run after `pg_dump` in `backup-db.sh` (`encrypt_backup.py`, `s3_upload.py`, status writer)? [Gap]
  → `PGPASSWORD` is a `pg_dump` command prefix, not exported (Design §Backup container, decision 0830).
- [x] CHK006 - Is it stated that the SQLite paths (restore, backup, wait_for_db) stay unchanged? [Completeness]
  → SQLite paths unchanged, stated under the inventory.

## Clarity

- [x] CHK007 - Is the scope of `PGPASSWORD` in `backup-db.sh` stated the same way everywhere? The design says "exported for `pg_dump` only", Task 2 says "export `PGPASSWORD` only when the URI had a password" (a script-wide export). [Clarity, Design §Backup container vs Tasks §Task 2]
  → Design and Task 2 now both say: command prefix, not exported.
- [x] CHK008 - Is the shell ↔ python hand-off format defined for passwords with a newline or other characters the two-line output can't carry? [Clarity, Edge Case]
  → Two separate `python3 -c` calls; password via `sys.stdout.write`; trailing newline unsupported (decision 0830).
- [x] CHK009 - Is "the part after the last `@`" in `pg_conn` defined in terms of the raw netloc, so an encoded `%40` in the password and a literal `@` behave as intended? [Clarity, Design §Restore container]
  → Defined via `urlsplit` + `netloc.rpartition("@")` (Design §Shared behaviour of `pg_conn`).
- [x] CHK010 - Is the mask output fully specified for `user:@host` (empty password) and `:pw@host` (no user)? [Clarity, Decision 0800]
  → Results table in Design §App startup (`user:@h`, `:pw@h`, `user@h`).

## Consistency

- [x] CHK011 - Are the `pg_conn` requirements for `restore_db.py`, `backup_utils.py` and the shell snippet written as one shared behaviour spec, so the three copies can't drift (decision 0805)? [Consistency]
  → One behaviour spec + shared test cases (Design §Shared behaviour of `pg_conn`).
- [x] CHK012 - Does the parse-error decision ("exception text not printed") agree with the bootstrap-failed line, which still prints `{exc}`, masked? [Consistency, Decision 0800]
  → Parse error drops `{exc}` (repeats the URL); other lines keep it, masked (Design §App startup).
- [x] CHK013 - Does the decision's rejection of "mask at log time" stay consistent now that `wait_for_db.py` (and possibly `backup-db.sh:101`) do mask at log time? [Consistency, Decision 0753]
  → Decision 0753 clarified: masking only where URL text must be shown.

## Measurability

- [x] CHK014 - Is there a single objective acceptance criterion for the feature, such as "no test captures the password in stdout/stderr, argv, exception text or the state file for any covered path"? [Measurability]
  → Feature-wide acceptance added (Design §Testing).
- [x] CHK015 - Is a sentinel password defined for the tests (for example one with `@`, `:`, `/`, `%`), so "contains no password" can't pass by accident with a simple value? [Measurability, Tasks §Acceptance]
  → Sentinels `S3nt%40in%3Ael%2F%25pw` / `p@ss-S3ntinel` (Design §Testing, Tasks §Overview).
- [x] CHK016 - Is the claim "libpq stderr does not contain the password" (`pg_dump failed: {stderr}`, flashed in the admin UI) backed by a requirement or a test, not an assumption? [Measurability, Design §App manual backup]
  → Accepted assumption, written down in Design §App manual backup.

## Coverage

- [x] CHK017 - Does the design define what happens when the URI has no password but `PGPASSWORD` or a `.pgpass` file is already present in the container? [Coverage, Design §Edge cases]
  → No password in URI → env unchanged, so `.pgpass`/`PGPASSWORD` keep working (Design §Shared behaviour).
- [x] CHK018 - Is the residual exposure (`/proc/<pid>/environ`, `docker inspect` showing `DATABASE_URL`, compose files) stated as an accepted risk with its threat model (who can read logs vs. who can read env)? [Coverage, Decision 0753]
  → Residual exposure and threat model in Design §Out of scope and decision 0753.
- [x] CHK019 - Was `.pgpass` / `PGPASSFILE` considered and rejected as an alternative to `PGPASSWORD`? [Coverage, Decision 0753 §Options]
  → Option C (`.pgpass`) added and rejected in decision 0753.
- [x] CHK020 - Do the upgrade requirements say what "rotate the Postgres password" involves for this deployment (`POSTGRES_PASSWORD` volume behaviour, `ALTER USER`, updating `DATABASE_URL` in every service's env file)? [Coverage, Design §Documentation]
  → Concrete rotation steps in Design §Documentation (c), Task 3.
- [x] CHK021 - Are log destinations other than `docker logs` (log shippers, CrowdSec/fail2ban reading container logs) named as places where already-leaked passwords may remain? [Coverage, Design §Documentation]
  → Docker json logs, log shippers/SIEM, `restore-state.json` listed in Design §Documentation (d).
- [x] CHK022 - Is there a regression requirement that stops new code from putting a password-bearing URI in argv or logs again (a test or a review rule)? [Coverage]
  → Per-path sentinel tests are the guard; no lint rule (accepted, decision 0830).

## Summary

- **Total Items:** 22
- **Focus Areas:** leak inventory completeness, `PGPASSWORD` scope in the backup script, helper consistency across three copies, test measurability, upgrade/rotation guidance
- **Status:** all 22 items resolved in /minispec.analyze (2026-11-25); see decision `20261125-0830-pg-password-checklist-gap-resolutions`.
- **Key Gaps Identified (now resolved):**
  - `backup-db.sh:101` logs the full `DB_URI` on an unsupported scheme (CHK001).
  - `docker/backup/entrypoint.sh:37` passes the password-bearing URI to `pg_isready` (CHK002).
  - Design and Task 2 disagree on how widely `PGPASSWORD` is exported in `backup-db.sh` (CHK005, CHK007).
  - No sentinel password or single feature-wide "no leak" criterion is defined for the tests (CHK014, CHK015).
