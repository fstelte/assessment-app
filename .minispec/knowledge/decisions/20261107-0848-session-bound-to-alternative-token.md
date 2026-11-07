---
type: decision
id: 20261107-0848-session-bound-to-alternative-token
date: 2026-11-07
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/identity/models.py
  - scaffold/extensions.py
  - scaffold/core/security.py
  - migrations/
tags: [security, auth, session, restore]
participants: [Ferry Stelte, Claude]
---

# Bind sessions to a per-user alternative token instead of the numeric user id

## Context

After a full restore, a logged-in browser can end up acting as a different
user. Flask-Login stores only `users.id` in the session and in the remember-me
cookie (`UserMixin.get_id()`), and the user loader
(`scaffold/extensions.py`, `_load_user`) does `User.query.get(int(user_id))`.
A restore can give that id to someone else.

The fingerprint in `scaffold/core/security.py` uses `hash(user_agent)`. Python
randomises string hashes per process, so after a restart every session fails
the fingerprint check. That accidental logout currently limits the damage, and
moving to a stable hash on its own would make the problem worse.

## Options Considered

- **A: alternative token (chosen).** `User.get_id()` returns a random per-user
  token stored in a new column, and the user loader looks users up by that
  token. Flask-Login calls these "alternative tokens".
- B: store OID/email in the session and compare it with `current_user` on every
  request: rejected. A session rebuilt from the remember-me cookie only has the
  numeric id, so there's nothing to compare against, and the check would accept
  the wrong user. Logging everyone out after a restore would also need a
  separate mechanism that works without Redis.

## Decision

- `users.session_token`: a random, unique, NOT NULL string
  (`secrets.token_hex(32)`, 64 hex characters, the same format in every path), filled
  for existing users by an Alembic migration. The downgrade only works together
  with rolling back the code.
- `User.get_id()` returns `session_token`. `_load_user` looks up by
  `session_token`. An unknown token means not logged in.
- `User.rotate_session_token()` sets a new token. That ends every session and
  remember-me cookie of that user, with cookie sessions as well as Redis.
- `generate_session_fingerprint()` uses `hashlib.sha256(user_agent)`, **only
  together with** this decision, so the fingerprint survives a restart without
  reopening the problem.

## Consequences

### Positive
- ✅ A session or remember-me cookie can never map to another user after a
  restore or an id change.
- ✅ "Log out everywhere" works without Redis, for one user (rotate one token)
  or for everyone (rotate all tokens).
- ✅ Sessions survive an app restart, because the fingerprint is stable.

### Negative
- ⚠️ Schema change: migration plus a backfill.
- ⚠️ All existing sessions end once at deployment.
- ⚠️ `invalidate_user_sessions` searches Redis for `"_user_id": "<id>"` and has
  to search for the token instead, or be replaced by rotating the token.
- ⚠️ Backups now contain session tokens. A token alone isn't enough to forge a
  cookie (that needs `SECRET_KEY`), but tokens are rotated after every restore
  anyway (see the restore-invalidation decision).

## Related Decisions

- [[20261107-0855-restore-invalidates-all-sessions]]
