---
title: Admin sets a user's password directly
date: 2026-09-24
status: accepted
---

## Context

Admins on `/admin/users` need to update a local user's password. There is no admin password route, no mail or reset-token infrastructure and no `must_change_password` flag.

## Decisions

The admin types a new password (minimum 12 characters, with a confirm field). It is applied with `User.set_password` and an audit event is logged without the password.

- Service accounts and federated (Entra) users are blocked.
- Changing your own password also requires the current password.
- Sessions of the target are invalidated with `invalidate_user_sessions`, except when the target is the current admin. This only works with Redis sessions, so a warning is flashed otherwise. Remember-me cookies are not revoked.

Security checklist decisions (2026-09-24): the route is limited to 10 requests per minute; there is no maximum length; the user is not notified (no mail infrastructure); any user status is allowed.

## Alternatives considered

- Temporary password with forced change at next login: needs a new column, a migration and a login-flow change.
- Emailed reset link: needs mail and token infrastructure that does not exist.

## Consequences

- The admin knows the user's password until the user changes it.
- No schema change or migration.
