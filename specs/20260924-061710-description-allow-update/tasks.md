---
feature: 20260924-061710-description-allow-update
status: planned
created: 2026-09-24
chunk_size: adaptive
total_tasks: 4
estimated_lines: 310
---

# Admin User Account Management Tasks

## Overview
Adds a per-user Manage page at `/admin/users/<id>/manage` with set password, full MFA reset and delete. No schema change or migration.

## Task List

### Foundation

#### Task 1: Manage page shell, Manage link and delete button
- **Estimate:** ~85 lines
- **Files:** `scaffold/apps/admin/routes.py`, `scaffold/apps/admin/templates/admin/user_manage.html` (new), `scaffold/apps/admin/templates/admin/users.html`, `scaffold/translations/en.json`, `scaffold/translations/nl.json`, `tests/test_admin_routes.py`
- **Description:** Add GET `admin.user_manage` and its template with user details, a delete form with a confirm prompt posting to the existing `admin.delete_user`, and a link to the MFA page. Add a Manage link per row in the users table. Add en and nl keys. Make `delete_user` catch `IntegrityError`, roll back and flash `admin.users.flash.user_in_use` (deactivate instead).
- **Depends on:** None
- **Acceptance:** Admin sees the page, a non-admin gets 403, the delete button removes the user through the existing route, and a delete rejected by the database leaves the user in place with the flash message and no `user_deleted` event.
- **Evidence:** New tests in `tests/test_admin_routes.py` pass, including one that makes the commit raise `IntegrityError` (SQLite does not enforce foreign keys by default).

### Core Implementation

#### Task 2: Set password [P]
- **Estimate:** ~110 lines
- **Parallel:** Can run with Task 3
- **Files:** `scaffold/apps/admin/forms.py`, `scaffold/apps/admin/routes.py`, `scaffold/apps/admin/templates/admin/user_manage.html`, `scaffold/translations/en.json`, `scaffold/translations/nl.json`, `tests/test_admin_routes.py`
- **Description:** Add `SetPasswordForm` (`password`, `confirm`, minimum 12 characters, must match, plus `current_password` when the target is the current admin). Add `POST /users/<id>/password`: block federated users (`azure_oid` or `aad_upn`) and service accounts, call `User.set_password`, call `invalidate_user_sessions` only when the target is not the current admin, flash a warning when `SESSION_TYPE` is not `redis`, and log `user_password_set` without the password. Add the form to the Manage page, hidden for federated users and service accounts.
- **Depends on:** Task 1
- **Acceptance:** Password changes and the user can log in with it. Too-short and mismatched passwords are rejected. Self change needs the correct current password. Federated and service-account targets are rejected.
- **Evidence:** New tests pass, including one asserting the audit event exists and does not contain the password.

#### Task 3: Reset MFA [P]
- **Estimate:** ~90 lines
- **Parallel:** Can run with Task 2
- **Files:** `scaffold/apps/admin/routes.py`, `scaffold/apps/admin/templates/admin/user_manage.html`, `scaffold/translations/en.json`, `scaffold/translations/nl.json`, `tests/test_admin_routes.py`
- **Description:** Add `POST /users/<id>/mfa/reset`: block self-reset, federated users and service accounts, delete the `MFASetting` row and all `PasskeyCredential` rows, `invalidate_user_sessions`, log `user_mfa_reset`. Add the button with a confirm prompt to the Manage page, hidden for the current admin, federated users and service accounts.
- **Depends on:** Task 1
- **Acceptance:** After a reset the user has no MFA setting or passkeys, and the next password login redirects to `auth.mfa_enroll`. An admin cannot reset their own MFA.
- **Evidence:** New tests pass, including the login redirect test and the self-reset block.

### Polish

#### Task 4: Docs and translation check
- **Estimate:** ~25 lines
- **Files:** `scaffold/apps/admin/templates/admin/user_manage.html`, `docs/` (one file), `tests/test_admin_routes.py`
- **Description:** Document the new admin actions in `docs/`, including the session-invalidation limitation (Redis sessions only, remember-me cookies not revoked), the re-enrollment scope (password sign-in only) and that a delete can be rejected when the user owns records. Check translation keys.
- **Depends on:** Tasks 2, 3
- **Acceptance:** The docs describe the three actions and their limitations; no translation key is missing in en or nl.
- **Evidence:** Translation-key check is clean and `pytest tests/test_admin_routes.py` passes.

## Notes
- The constitution sets no review chunk size, so adaptive was used.
- Combining tasks (for example Tasks 2 and 3) is to be considered during the build.
- The federated and service-account check appears in two routes. Inline it as a small private function in `routes.py` only if it grows.
- Out of scope: temporary passwords with forced change, emailed reset links, bulk actions.

## Progress
- [x] Task 1: Manage page shell, Manage link and delete button
- [ ] Task 2: Set password
- [ ] Task 3: Reset MFA
- [ ] Task 4: Docs and translation check



