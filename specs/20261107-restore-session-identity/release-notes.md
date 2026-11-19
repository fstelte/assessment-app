# Release notes: restore-safe session identity (2026.11.3)

## What's new

- **A restore can no longer make a browser act as a different user.** Sessions
  and remember-me cookies used to store the numeric user id. After a full
  restore, that id could belong to someone else. Sessions are now bound to a
  random per-user token (`users.session_token`).
- **Every restore logs everyone out.** All users get a new token after a full
  or partial restore. The administrator who ran a partial restore stays signed
  in.
- **Admin password set and MFA reset always end the user's sessions,** with or
  without Redis, including remember-me cookies.

## Who can do what

Nothing changes.

## Behaviour changes to be aware of

- After deploying this release, and after every restore, users have to sign in
  again.
- A partial restore that includes the identity tables keeps existing users as
  they are. New users from the backup get a fresh token.
- A fully failed partial restore changes nothing and logs nobody out.

## Upgrade

1. Run `flask db upgrade`. Migration `20261107_0001` adds `session_token` to
   `users`, gives every existing user a token, and adds a unique index. It
   works on PostgreSQL and SQLite.
2. Everyone is logged out once.

**Downgrade** drops the column and the index. Only do this together with
rolling back the code, because the new code reads the column.

## Known limitations and follow-ups

- Redis sessions from before a rotation stay in Redis until they expire, but
  they can no longer be loaded.
