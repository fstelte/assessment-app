---
feature: 20261107-restore-session-identity
status: implemented
created: 2026-11-07
branch: 20261106-161847-description-partial-restore
decisions:
  - 20261107-0848-session-bound-to-alternative-token
  - 20261107-0855-restore-invalidates-all-sessions
  - 20261107-0905-invalidate-user-sessions-rotates-token
---

# Restore-Safe Session Identity Design

## Overview

After a full restore, a logged-in browser can act as a different user.
Flask-Login stores only the numeric `users.id` in the session and in the
remember-me cookie, and after a restore that id can belong to someone else.

The fix:

- Bind sessions and remember-me cookies to a random per-user
  `users.session_token` (Flask-Login "alternative tokens").
- Give every user a new token after every restore, which logs everyone out
  (except the admin who ran a partial restore).
- Have `invalidate_user_sessions` rotate a single user's token.
- Stabilise the session fingerprint with `sha256`, which is only safe together
  with the token.

This is built on the same branch as the partial-restore FK fix.

## User Stories

- As a user, I never end up logged in as someone else after a restore.
- As an admin, I know that after every restore no session or remember-me cookie
  from before the restore still works.
- As an admin who just ran a partial restore, I stay logged in and see the
  results page.
- As an admin who sets a password or resets MFA for a user, I know their existing
  sessions and remember-me cookies really end, including without Redis.
- As a user, I'm no longer logged out just because the app restarted.

## Components

### `User` model (`scaffold/apps/identity/models.py`)

- New column `session_token = db.Column(db.String(64), unique=True, nullable=False, index=True, default=_new_session_token)`
  with `_new_session_token() = secrets.token_hex(32)`.
- **Token format, the same in every path:** 64 lowercase hex characters, which
  is exactly `String(64)`. The app, the migration and the SQLite step in
  `restore_db.py` all use `secrets.token_hex(32)`. The PostgreSQL step in
  `restore_db.py` also produces 64 hex characters.
- `get_id(self) -> str`: returns `self.session_token`. Overrides `UserMixin.get_id`.
- `rotate_session_token(self) -> None`: `self.session_token = _new_session_token()`.
  The caller commits.

### Migration (`migrations/versions/…_users_session_token.py`)

- Add `session_token` as a nullable column, give every existing user a token
  in Python (`secrets.token_hex(32)` per row), then set NOT NULL and add a
  unique index.
- Downgrade: drop the index and the column. **Only together with rolling back
  the code:** after a downgrade, `User.get_id()` refers to a column that no
  longer exists. That's stated in the migration's docstring. After a code
  rollback, sessions use the numeric id again, which is the old behaviour and
  intended for a rollback.
- Works on PostgreSQL and SQLite (with `batch_alter_table` for SQLite).

### User loader (`scaffold/extensions.py`, `_load_user`)

- `User.query.filter_by(session_token=user_id).one_or_none()`. An empty or
  unknown token returns `None`, so the user isn't logged in. No `int()` anymore.
- An old cookie with a numeric id finds nothing. That's the one-time logout at
  deployment.

### Session fingerprint (`scaffold/core/security.py`)

- `generate_session_fingerprint() -> str`:
  `hashlib.sha256(user_agent.encode()).hexdigest()`.
- Only together with the token: sessions now survive a restart, and the token
  makes that safe.
- Existing sessions with an `int` fingerprint fail the check once and get logged
  out, which coincides with the deployment logout.

### `invalidate_user_sessions(user_id)` (`scaffold/core/security.py`)

- Load the user, `rotate_session_token()`, commit. The Redis scan goes.
- `scaffold/apps/admin/routes.py`: the 2 `flash("…sessions_not_revoked")` calls
  go, and the 3 call sites stay the same: **deactivating a user** (around line
  1516), **an admin setting a password** (around line 1612) and **an MFA reset**
  (around line 1648). The existing rule that an admin doesn't log themselves out
  stays at the call sites.
- `en.json` / `nl.json`: the key `admin.users.flash.sessions_not_revoked` goes.

### Full restore (`docker/restore/restore_db.py`)

- New step `rotate_session_tokens(db_uri)`, called in `process_backup` after
  the restore and **before** `start_containers`:
  - First check that `users.session_token` exists (PostgreSQL:
    `information_schema.columns`; SQLite: `PRAGMA table_info(users)`).
    If it doesn't, log it and do nothing; the migration fills the column when
    the app starts.
  - PostgreSQL (through `psql -c`):
    `WITH u AS (UPDATE users SET session_token = replace(gen_random_uuid()::text || gen_random_uuid()::text, '-', '') RETURNING 1) SELECT count(*) FROM u`
    (C2: `gen_random_uuid()` is a cryptographic random generator, built in since PostgreSQL 13).
  - SQLite (through Python's `sqlite3` module; the image has no `sqlite3`
    command-line tool): read all `id`s, and per row
    `UPDATE users SET session_token = ? WHERE id = ?` with `secrets.token_hex(32)`,
    in one transaction. That's the same format and the same random source as
    the app.
- A failure in this step is logged and recorded in the state file. The restore
  itself counts as successful (decision 0855). The error message tells the
  operator to rotate manually (a restart doesn't sign anyone out since the fingerprint is stable, Task 2).

### Partial restore (`scaffold/apps/admin/backup_utils.py`, `orchestrate_partial_restore`)

- After the run, if `run.status != "failed"`: give every user a new token
  except `user_id` (the admin who ran it), using one `UPDATE … WHERE id != :uid`
  with a new token per row from Python. Commit.
- If it fails: add a warning to `run.warnings` (shown on the results page) and
  log it. The run status doesn't change.

### Docs (`docs/deployment.md`)

- Under "Partial Restore" and under the full-restore section, explain that every
  restore logs everyone out (partial: except the admin who ran it), and that
  the deployment of this change logs everyone out once.

### Test login helpers

- 5 helpers set `sess["_user_id"] = str(user.id)`:
  `tests/conftest.py`, `test_admin_backup_crypto.py`,
  `test_admin_partial_restore.py`, `test_admin_routes.py`,
  `test_bia_component_tier.py`, plus a check of `test_scim_users.py`.
  They change to `sess["_user_id"] = user.get_id()`.

## Data Model

| Table | Column | Type | Constraints |
|-------|--------|------|-------------|
| `users` | `session_token` | `String(64)` | NOT NULL, UNIQUE, index; default `secrets.token_hex(32)` (64 hex) |

## API/Interface

No new routes. Behaviour changes:

- Sessions and remember-me cookies contain the token, not the id.
- After every restore, all sessions end (partial: except the admin who ran it).
- The admin's set-password and MFA reset always end the target's sessions and
  remember-me cookies, with or without Redis.

## Edge Cases

- **Backup from before the migration:** `restore_db.py` finds no column, and the
  migration fills it with fresh tokens when the app starts. Everyone is
  logged out.
- **Restored database contains the same tokens as before** (backup of the same
  database): they're rotated straight away, so old cookies still don't work.
- **Partial restore that restores the identity group:** users who already exist
  stay the same (skip-existing). New users get the backup's token, which is
  then rotated in the same step. The admin who ran it keeps their token.
- **Token collision:** 256 bits of randomness, so negligible. The unique
  constraint would make the `UPDATE` fail, which is then logged as a failed
  rotation.
- **Fully failed partial restore:** no rotation. Nothing changed, so there's
  nothing to protect.
- **Redis sessions after rotation:** they stay in Redis until they expire, but
  can't be loaded (unknown token).
- **SCIM / SSO login:** both go through `finalise_login` → `login_user`, which
  uses `get_id()`, so they need no change.

## Success Criteria

- **SC-001:** After a full restore in which `users.id = 5` belongs to someone
  else, a browser that was logged in as id 5 before the restore is **not**
  logged in afterwards. The same holds for a remember-me cookie.
- **SC-002:** After a partial restore, the admin who ran it is still logged in;
  every other session and remember-me cookie has stopped working.
- **SC-003:** After an admin password set or MFA reset, the target's existing
  sessions end with cookie sessions too.
- **SC-004:** A user stays logged in across an app restart (same User-Agent).

## Constitution Check

| Principle | Confirmation |
|-----------|--------------|
| I. Module boundaries | Identity changes in `identity/models.py`, session logic in `core/security.py` and `extensions.py` (cross-cutting, already there). The restore step lives in `admin/backup_utils.py` and `docker/restore/`. No new cross-domain imports. |
| II. Security & audit | Who can log in doesn't change; who is logged in becomes stricter. Risk: everyone is logged out once at deployment, and everyone after every full restore. A failed rotation is logged and shown, never silently skipped. The existing audit events for password set and MFA reset stay. |
| III. Test & migration | Alembic migration with backfill and downgrade, tested on SQLite and PostgreSQL. Regression tests for SC-001 to SC-004 and for the migration. Test login helpers updated. |
| IV. UI & localization | No new UI. The `sessions_not_revoked` key goes from EN and NL. A rotation warning after a partial restore goes through `_()` with EN and NL keys. |
| V. Operational readiness | `docs/deployment.md`: logout after a restore, the one-time logout at deployment, and the manual fallback when rotation fails. The restore container needs no new environment variables. |

## Security Notes

Answers to the clarification questions from `checklists/security.md`.

- **Token stored as is in the database (CHK002, CHK019).** Acceptable: a
  session or remember-me cookie is signed with `SECRET_KEY`, so someone with
  only database or backup access can't forge a cookie. If `SECRET_KEY` has
  leaked too, everything is lost anyway, because sessions can then also be
  forged without a token. Leaked tokens from an old backup become worthless at
  the next restore (rotation). Storing a hash is rejected: it makes rotating in
  SQL harder and protects nothing extra while `SECRET_KEY` stays secret.
- **Failed rotation during a full restore (CHK006).** Tokens follow the person,
  not the id. With a backup of the same database, each token still points to the
  same person, so no wrong identity, but sessions from before the restore stay
  valid. With a backup from another environment, foreign tokens don't match, so
  people are logged out. The fallback is in `docs/deployment.md`.
- **"Admin who ran it" (CHK007).** That's `user_id` passed to
  `orchestrate_partial_restore` (`current_user.id`). If that user no longer
  exists after the run, every user is rotated without an exception.
- **Admin's own session (CHK009).** `invalidate_user_sessions` itself has no
  exception. The call sites keep their existing checks: an admin can't
  deactivate themselves or reset their own MFA. For their own password, the call
  is skipped as it is today.
- **Failure rules (CHK010).** Consistent: the restore never fails because of
  rotation, but a failure is always visible. The restore container logs it and
  records it in the state file. The partial restore puts it in `run.warnings`
  (results page) and logs it.
- **Timing of the fingerprint (CHK012).** `sha256` goes into Task 2, which is
  merged together with Task 1 (same PR or release). It's never deployed without
  the token.
- **Reproducible SC-001 (CHK013).** Scenario: user A (id 5) and user B (id 6)
  exist, and A is logged in. Swap their ids and give everyone a new token (a
  simulated restore). A's next request is anonymous, not B.
- **Remember-me without a browser (CHK014).** Test: log in with `remember=True`,
  keep the `remember_token` cookie, clear the session cookie, rotate tokens, then
  request a page. It's anonymous.
- **SC-004 across processes (CHK015).** Compute the fingerprint in two
  separate Python processes (`subprocess`) for the same User-Agent; they're
  equal. With `hash()` they weren't, because of per-process randomisation.
- **Concurrent requests during a partial restore (CHK016).** A request between
  the restore and the rotation still loads a session with a token that's correct
  for that person (partial restore never overwrites existing users), so no wrong
  identity. Its next request after the rotation is anonymous.
- **One-time logout at deployment (CHK018).** It applies to everyone: password,
  SSO (Azure) and passkey users log in again. SSO users usually get through
  automatically through their identity provider's session. SCIM and service
  tokens (`scim_tokens`) aren't sessions and aren't affected.
- **Remember-me cookie settings (CHK005).** Out of scope. No
  `REMEMBER_COOKIE_*` is configured, so Flask-Login's defaults apply (365 days,
  not `Secure`). That's a separate hardening follow-up.

## Out of Scope

- Rotating the token when users change their own password.
- Cleaning up stale Redis sessions.
- **SCIM deprovisioning** (`scim/provisioner.py`, `scim/routes.py`) sets
  `status = DISABLED` but doesn't call `invalidate_user_sessions`. Existing
  sessions then depend on `is_active`, which Flask-Login doesn't check again when
  it reloads a user. That's a follow-up: call `invalidate_user_sessions` on SCIM
  deactivation.
- Hardening the remember-me cookie (`REMEMBER_COOKIE_SECURE`, duration,
  `SAMESITE`).
- The STRIDE-LM question ("affected assets always shown"), which is still open.

## Open Questions

- None for the warnings. The SQLite question is settled: Python's `sqlite3`
  module (the image only has `postgresql-client-18`).
- **Still open (critical, from `/minispec.analyze`):**
  - ~~**C1:** MFA and passkey steps before login use the numeric `user.id`.~~ Settled in Task 1: `mfa_pending_user_id`, `mfa_enroll_user_id` and `passkey_reg_user_id` store `user.get_id()` and are looked up with `User.find_by_session_token`.
  - ~~**C2:** PostgreSQL `random()` in the token SQL.~~ Settled in Task 4: `gen_random_uuid()`.
  - ~~**C3:** no audit record of "all sessions ended".~~ Settled: partial restore in the audit event (Task 3), full restore in the log and `last_processed.session_rotation` in the state file (Task 4).
