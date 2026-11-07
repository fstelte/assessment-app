---
type: decision
id: 20261107-0905-invalidate-user-sessions-rotates-token
date: 2026-11-07
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/core/security.py
  - scaffold/apps/admin/routes.py
  - scaffold/translations/en.json
  - scaffold/translations/nl.json
tags: [security, auth, session, admin]
participants: [Ferry Stelte, Claude]
---

# `invalidate_user_sessions` rotates the user's session token

## Context

`invalidate_user_sessions(user_id)` (`scaffold/core/security.py`) is called by
three admin actions in `scaffold/apps/admin/routes.py`: deactivating a user
(around line 1516), setting a password (around line 1612) and resetting MFA
(around line 1648). SCIM deprovisioning doesn't call it; that's a follow-up. Today it only works with Redis
sessions, by searching the stored sessions for `"_user_id": "<id>"`. With cookie
sessions it does nothing, and remember-me cookies are never revoked. That
limitation is recorded in [[20260924-0620-admin-set-user-password]].

After [[20261107-0848-session-bound-to-alternative-token]], the session holds
the token instead of the id, so the Redis search would no longer find anything.

## Options Considered

- **A: rotate the user's token (chosen).**
- B: change the Redis search to look for the token: rejected. Nothing would
  happen without Redis, and remember-me cookies still wouldn't be revoked, while
  the token solves both.

## Decision

- `invalidate_user_sessions(user_id)` gives that user a new `session_token` and
  commits. The Redis scan goes.
- The call sites keep their existing rules, such as an admin not logging
  themselves out.
- The warning `admin.users.flash.sessions_not_revoked`, its flash calls and its
  EN/NL keys go, because sessions are now always ended.
- [[20260924-0620-admin-set-user-password]] is partly superseded on the point
  "only with Redis, remember-me cookies are not revoked".

## Consequences

### Positive
- ✅ The admin's "log this user out" works with every session backend and also
  ends remember-me cookies.
- ✅ Less code: no Redis scan over every session.

### Negative
- ⚠️ Stale sessions stay in Redis until they expire. They can't be loaded
  anymore (unknown token), so this is only a storage matter.
- ⚠️ The behaviour of the three admin actions changes (for the better), and the
  tests for them need checking.

## Related Decisions

- [[20261107-0848-session-bound-to-alternative-token]]
- [[20260924-0620-admin-set-user-password]] (partly superseded)
