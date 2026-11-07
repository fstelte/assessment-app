---
feature: 20261107-restore-session-identity
status: completed
created: 2026-11-07
chunk_size: medium
total_tasks: 5
estimated_lines: 250
---

# Restore-Safe Session Identity Tasks

## Overview

Bind sessions and remember-me cookies to `users.session_token` instead of
`users.id`. Every restore gives everyone a new token (partial restore: except
the admin who ran it). `invalidate_user_sessions` rotates one user's token, and
the fingerprint moves to `sha256`. See [design.md](design.md) and decisions
`20261107-0848`, `20261107-0855` and `20261107-0905`.

## Task List

### Foundation

#### Task 1: Session token, migration and user loader
- **Estimate:** ~85 lines (just above medium; can't be split, because the test login helpers have to change in the same change)
- **Files:** `scaffold/apps/identity/models.py`, `scaffold/extensions.py`,
  `migrations/versions/20261107_0001_users_session_token.py` (new, `down_revision = "20260925_0001"`),
  `tests/conftest.py`, `tests/test_admin_backup_crypto.py`, `tests/test_admin_partial_restore.py`,
  `tests/test_admin_routes.py`, `tests/test_bia_component_tier.py` (and check `tests/test_scim_users.py`),
  `tests/test_session_identity.py` (new)
- **Description:**
  - `User.session_token` (`String(64)`, NOT NULL, unique, index, default `secrets.token_hex(32)`, 64 hex characters).
  - `get_id()` returns the token; `rotate_session_token()` sets a new one.
  - `_load_user` looks up by `session_token`, without `int()`.
  - Migration: add the column as nullable → fill it per row with `secrets.token_hex(32)` → NOT NULL plus a unique index (`batch_alter_table` for SQLite) → downgrade. The migration docstring says the downgrade only works together with rolling back the code.
  - Test login helpers: `sess["_user_id"] = user.get_id()`.
- **Depends on:** None
- **Acceptance:** Login by token works. An unknown token, or the old numeric id, gives an anonymous user.
- **Evidence:** New tests in `tests/test_session_identity.py`:
  - (a) logged in through the token;
  - (b) the old numeric `_user_id` isn't logged in;
  - (c) **SC-001**: two users swap ids, and the browser that was logged in as id 5 isn't logged in as the other user;
  - (d) **SC-001 remember-me**: a remember cookie from before the token rotation doesn't log in;
  - (e) the migration on SQLite fills unique, NOT NULL tokens.

  The full `pytest` run has no new failures compared with the baseline: the 11 known admin failures stay the same.

### Core Implementation

#### Task 2: Fingerprint and `invalidate_user_sessions`
- **Estimate:** ~45 lines
- **Files:** `scaffold/core/security.py`, `scaffold/apps/admin/routes.py`,
  `scaffold/translations/en.json`, `scaffold/translations/nl.json`, `tests/test_session_identity.py`
- **Description:**
  - `generate_session_fingerprint()` → `hashlib.sha256(ua.encode()).hexdigest()`.
  - `invalidate_user_sessions(user_id)` → `rotate_session_token()` plus a commit. The Redis scan goes.
  - Remove the 2 `sessions_not_revoked` flashes and the key from EN and NL.
- **Depends on:** Task 1
- **Acceptance:** Sessions survive a restart. The admin's set-password and MFA reset end the target's sessions with cookie sessions too.
- **Evidence:** Tests:
  - **SC-004**: the fingerprint is the same in two processes, checked by computing it in a subprocess;
  - **SC-003**: the target is logged in on client B, the admin sets a password on client A, and client B's next request is no longer logged in.

  `test_translation_keys.py` passes.

#### Task 3: Rotation after a partial restore [P]
- **Estimate:** ~40 lines
- **Parallel:** Can run with Task 4
- **Files:** `scaffold/apps/admin/backup_utils.py`, `scaffold/translations/en.json`,
  `scaffold/translations/nl.json`, `tests/test_admin_partial_restore.py`
- **Description:** At the end of `orchestrate_partial_restore`, if `run.status != "failed"`, every user except `user_id` gets a new token. If that fails, add a warning to `run.warnings` (EN/NL key) and log it. The run status doesn't change.
- **Depends on:** Task 1
- **Acceptance:** **SC-002**.
- **Evidence:** Tests (SQLite, no Postgres needed):
  - the other user's token changes and the admin's stays the same;
  - a fully failed run rotates nothing;
  - a rotation error gives a warning and the run keeps its status.

#### Task 4: Rotation in the restore container [P]
- **Estimate:** ~55 lines
- **Parallel:** Can run with Task 3
- **Files:** `docker/restore/restore_db.py`, `tests/test_restore_db.py` (new)
- **Description:**
  - `rotate_session_tokens(db_uri)` is called at the end of `process_backup`, before `start_containers`.
  - Check that the column exists first: PostgreSQL via `information_schema.columns`, SQLite via `PRAGMA table_info`. If it doesn't, log it and skip.
  - PostgreSQL via `psql -c "UPDATE users SET session_token = …"`.
  - SQLite via Python's `sqlite3` module (the image has no `sqlite3` command-line tool), with `secrets.token_hex(32)` per row in one transaction.
  - A failure is logged and recorded in the state file. The restore itself counts as successful.
- **Depends on:** Task 1 (for the column name)
- **Acceptance:** After a full restore, every token is different and unique.
- **Evidence:** `tests/test_restore_db.py`:
  - SQLite for real: tokens change, stay unique and are 64 hex characters;
  - no column: nothing happens and it's logged;
  - PostgreSQL: `run_command` is mocked and the SQL checked;
  - failure: the restore still counts as successful and the warning is recorded.

### Integration & Polish

#### Task 5: Operations docs
- **Estimate:** ~25 lines
- **Files:** `docs/deployment.md`
- **Description:** Document:
  - every restore logs everyone out (partial: except the admin who ran it);
  - the deployment of this change logs everyone out once;
  - the manual fallback when rotation fails (rotate by hand; **not** "restart the app", which no longer logs anyone out since the stable fingerprint of Task 2);
  - `invalidate_user_sessions` now works without Redis.
- **Depends on:** Tasks 2, 3, 4
- **Acceptance:** Constitution V is met.
- **Evidence:** The `docs/deployment.md` diff in the PR.

## Notes
- The setup script isn't used, because it would overwrite the tasks.md of the
  partial-restore feature (same branch). Everything is on branch
  `20261106-161847-description-partial-restore`.
- Known baseline, measured per file (each test file separately, 5-minute
  limit): **160 failing tests on `fb0aea5`**, from before this feature. Evidence
  is "no new failures compared with that baseline". The full suite in one run
  hangs (stopped after more than 2 hours); whether that also happens on the
  baseline hasn't been checked.
- Out of scope: rotating the token when users change their own password, an
  audit event per rotation, cleaning up stale Redis sessions, and the STRIDE-LM
  question.

## Progress
- [x] Task 1: Session token, migration and user loader — *including C1 (MFA/passkey steps before login use the token). Evidence: `tests/test_session_identity.py` 6/6 passed. **Correction (2026-11-07):** the earlier claim "full `pytest`: the same 11 known failures" was wrong: it was based on an old result file. The full run didn't finish (it hung for more than 2 hours and was stopped). Replacement evidence: every test file run separately (5-minute limit), compared with the same run on `fb0aea5` (before the session work): **exactly the same 160 failing tests, no new ones**; `test_session_identity.py` passes. Migration tested on SQLite only, not on PostgreSQL.*
- [x] Task 2: Fingerprint and `invalidate_user_sessions` — *evidence: `tests/test_session_identity.py` 8/8 passed (SC-003, SC-004); per-file run of every test file compared with `fb0aea5`: the same 160 failing tests, no new ones. `test_auth_login_audit::test_password_login_records_audit_entry` fails alone also on `fb0aea5` (order-dependent, existing).*
- [x] Task 3: Rotation after a partial restore — *including the partial-restore half of C3 (`sessions_rotated` and `sessions_kept_user_id` in the `partial_restore_execute` audit event). Rotates only on `completed`/`partial` (not on `failed`/`blocked`, which change nothing). Evidence: `TestSessionRotationAfterRestore` 3/3 (SC-002, failed run, rotation error); per file compared with `fb0aea5`: `test_admin_partial_restore` 0/0, `test_admin_routes` 10/10, `test_translation_keys` 0/0, `test_no_eager_translations` 1/1, `test_session_identity` 0, no new failures. Not tested: the audit fields in `routes.py` (no route test).*
- [x] Task 4: Rotation in the restore container — *including C2 (`gen_random_uuid()` instead of `random()`) and the full-restore half of C3 (log line plus `last_processed.session_rotation` in the state file). Evidence: `tests/test_restore_db.py` 5/5 (SQLite for real, no column, PostgreSQL SQL with mocked `psql`, failure without an exception, order restore → rotate). Not tested: real `psql` against PostgreSQL.*
- [x] Task 5: Operations docs — *`docs/deployment.md`: new section "Sessions after a restore" (full/partial restore, admin actions, restart no longer logs anyone out, manual fallback), plus references in the restore companion, partial restore and release checklist. While writing it, fixed the outdated "restart the app" fallback in the EN/NL warning and in `restore_db.py`. Evidence: the diff; affected tests 10/10. Not tested: the `python -c` fallback command.*
