---
type: decision
id: 20261107-0855-restore-invalidates-all-sessions
date: 2026-11-07
status: accepted
supersedes: null
superseded_by: null
impacts:
  - docker/restore/restore_db.py
  - scaffold/apps/admin/backup_utils.py
  - docs/deployment.md
tags: [security, auth, session, restore, backup]
participants: [Ferry Stelte, Claude]
---

# Every restore rotates all session tokens; partial restore keeps the initiating admin

## Context

[[20261107-0848-session-bound-to-alternative-token]] binds sessions and
remember-me cookies to `users.session_token`. After a restore, every session
should end, so that no browser carries on with state from before the restore.

There are two restore paths:

- **Full restore.** `/admin/backup/restore` only puts the file in
  `RESTORE_WATCH_DIR`. The restore container (`docker/restore/restore_db.py`)
  stops the app containers, recreates the database with `psql` (or replaces the
  SQLite file), and starts them again.
- **Partial restore.** It runs inside the app (`orchestrate_partial_restore`)
  with skip-existing: it never overwrites existing rows.

## Options Considered

- **A: give every user a new token in the database right after the restore
  (chosen).**
- B: a global "session generation" outside the database (a file or Redis key):
  rejected. It needs storage that survives a restore and is shared between
  containers, and it adds a second mechanism next to the token.
- A1: also log out the admin who ran a partial restore: rejected. A partial
  restore can't change who an existing id belongs to, so it adds no safety and
  only costs the admin the results page.

## Decision

- **Full restore:** `restore_db.py` runs, after the restore and **before**
  starting the app containers again:
  - PostgreSQL:
    `UPDATE users SET session_token = replace(gen_random_uuid()::text || gen_random_uuid()::text, '-', '')`
    (C2, 2026-11-07: `gen_random_uuid()` uses a cryptographic random generator and is built in since
    PostgreSQL 13; the earlier `md5(random()…)` did not and was rejected). The number of rotated
    users is logged and stored in the state file under `last_processed.session_rotation` (C3).
  - SQLite (Python's `sqlite3` module; the image has no `sqlite3` command-line tool):
    per row `secrets.token_hex(32)`, in one transaction, the same format and random
    source as the app.
  - Only if `users.session_token` exists. A backup from before the migration
    gets the column, with fresh tokens, from the migration when the app starts,
    which also logs everyone out.
  - Every user is logged out, the admin who started the restore included.
- **Partial restore:** at the end of `orchestrate_partial_restore`, when the
  run didn't fail completely, every user gets a new token **except the admin who
  ran it**. Their token is written back, so their session stays valid and they
  see the results page.
- If rotating fails, the restore itself doesn't fail. A warning is logged and
  shown, and the run gets a warning, because silently skipping it would leave
  sessions alive (constitution II).
- `docs/deployment.md` describes that every restore logs everyone out.

## Consequences

### Positive
- ✅ Works with cookie sessions and with Redis sessions; no session has to be
  found and deleted.
- ✅ No state outside the database and no extra service.
- ✅ Tokens from a leaked or old backup are worthless after a restore.

### Negative
- ⚠️ The restore container knows about the `users.session_token` column, which
  links the restore script to the app's schema.
- ⚠️ After a full restore, everyone has to log in again.

## Related Decisions

- [[20261107-0848-session-bound-to-alternative-token]]
