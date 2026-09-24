---
feature: 20260924-061710-description-allow-update
status: implemented
created: 2026-09-24
decisions: [20260924-0620-admin-set-user-password, 20260924-0625-admin-mfa-full-reset, 20260924-0630-admin-user-manage-page]
---

# Admin User Account Management Design

## Overview
Admins get a per-user Manage page at `/admin/users/<id>/manage`. From it they can set a local user's password, reset all of the user's MFA enrollment (the user must re-enroll after next login), or delete the user. The users table gains a Manage link.

## User Stories
- As an admin, I want to set a user's password so that a locked-out user can sign in again.
- As an admin, I want to reset a user's MFA so that a user who lost their device is forced to re-enroll at next login.
- As an admin, I want a delete button on the users page so that I can remove accounts (the delete route already exists).

## Components
### Manage page (`admin.user_manage`, GET)
Template `admin/user_manage.html`, Tailwind, following the existing admin templates. It has a set-password form, a Reset MFA button and a Delete button in a danger zone, plus a link to the existing MFA page. Set-password and Reset MFA are hidden for federated (Entra) users, meaning `azure_oid` or `aad_upn` is set, and for service accounts (`is_service_account`).

### Set password (`admin.set_user_password`, POST `/users/<id>/password`)
`SetPasswordForm` with `password` and `confirm` fields, minimum 12 characters, fields must match. Calls `User.set_password`, then, when the target is not the current admin, `invalidate_user_sessions(user.id)`, then `log_event("user_password_set")`. When sessions cannot be revoked (see Session invalidation) the route flashes a warning. The password is never logged. When the target is the current admin, the form also requires `current_password`, checked with `User.check_password`. Rejects federated users and service accounts.

### Reset MFA (`admin.reset_user_mfa`, POST `/users/<id>/mfa/reset`)
Deletes the `MFASetting` row, which removes the TOTP secret and backup codes, and all `PasskeyCredential` rows. Then `invalidate_user_sessions`, then `log_event("user_mfa_reset")`. Rejected when the target is the current user (an admin cannot reset their own MFA). Rejected for federated users and service accounts. At next password login the existing local-account enforcement in `auth/routes.py` sends the user to `mfa_enroll`.

### Delete user
Existing `admin.delete_user` (self-delete and last-admin guards already there). The Manage page adds the button with a confirm prompt. Service accounts may be deleted. Many tables reference `users.id` without ON DELETE (for example control owner, threat owners, maturity, BIA author), so the database can reject a delete. The route catches `IntegrityError`, rolls back, and flashes `admin.users.flash.user_in_use` telling the admin to deactivate the user instead. No `user_deleted` audit event is written in that case.

### Session invalidation
`invalidate_user_sessions` only takes effect when server-side sessions are enabled (`SESSION_TYPE == "redis"`, which needs the server-side sessions setting and `REDIS_URL`). With cookie sessions it does nothing, so an already signed-in user stays signed in until their session expires. The password route flashes a warning in that case. Flask-Login remember-me cookies are not revoked in either mode. Changing your own password does not invalidate your own session.

### Re-enrollment scope
Forced re-enrollment applies to password sign-in, which is the only path for a local user once TOTP and passkeys are cleared. A SAML sign-in matched by email sets the Entra identity on the account and relies on the IdP for MFA, so it skips local enrollment. That is existing behaviour and is not changed.

### Users table
Add a Manage link per row (`admin.users.actions.manage`).

## Data Model
No changes and no migration.

## API/Interface
| Method | Path | Notes |
|---|---|---|
| GET | `/admin/users/<id>/manage` | New |
| POST | `/admin/users/<id>/password` | New |
| POST | `/admin/users/<id>/mfa/reset` | New |
| POST | `/admin/users/<id>/delete` | Existing |

All routes use `@login_required`, `@require_fresh_login()`, `_require_admin()` and CSRF, like the neighbouring routes. Copy goes through `_()` with en and nl keys.

## Constitution Check
- Security and audit: admin-only, fresh-login required, audit events for password set and MFA reset, sessions invalidated.
- Tests: pytest cases in `tests/test_admin_routes.py` for each route, the self-reset block, the federated and service-account blocks, the current-password check on self password change, and the login redirect to `mfa_enroll` after a reset.
- Localization: en and nl keys.
- Docs: a short note in `docs/` on the new admin actions.

## Open Questions
- None. Known limitations: sessions are not revoked without Redis sessions, and remember-me cookies are never revoked.

## Out of Scope
Temporary passwords with forced change, emailed reset links, bulk actions.





