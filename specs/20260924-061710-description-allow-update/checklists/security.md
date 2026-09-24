---
type: checklist
domain: security
feature: 20260924-061710-description-allow-update
created: 2026-09-24
status: completed
---

# Security Requirements Quality Checklist

**Purpose:** Validate that the security requirements for admin password set, MFA reset and user delete are complete, clear and consistent.
**Feature:** 20260924-061710-description-allow-update

## Completeness

- [x] CHK001 - Are the fields recorded in the `user_password_set`, `user_mfa_reset` and `user_deleted` audit events specified (actor, target, reason)? [Gap, Design §Components]
- [x] CHK002 - Is it specified whether the acting admin's own session survives when they change their own password? [Gap, Design §Set password]
- [x] CHK003 - Are throttling or lockout requirements defined for repeated wrong `current_password` attempts on self password change? [Gap]
- [x] CHK004 - Is a maximum password length, or any rule beyond the 12-character minimum, specified? [Gap, Design §Set password]
- [x] CHK005 - Is it specified whether the affected user is notified after their password or MFA is changed by an admin? [Gap]
- [x] CHK006 - Are requirements defined for deleting a user who owns assessments, assignments or BIA contexts (foreign keys)? [Gap, Design §Delete user]
- [x] CHK007 - Is behavior defined for resetting MFA or setting a password on a user whose status is `PENDING` or `DISABLED`? [Gap]

## Clarity

- [x] CHK008 - Is "federated user" defined as exactly one condition (`azure_oid` or `aad_upn` set, or both)? [Clarity, Design §Manage page]
- [x] CHK009 - Is "blocked" defined for each rejected case (HTTP status, flash message, or hidden control only)? [Clarity, Design §Reset MFA]
- [x] CHK010 - Is "forced to re-enroll" defined by an observable outcome, such as the redirect to `auth.mfa_enroll` with no access to other pages first? [Clarity, Design §Reset MFA]
- [x] CHK011 - Is the confirm prompt on delete and reset stated as a UI convenience only, with the server as the enforcement point? [Clarity]

## Consistency

- [x] CHK012 - Do the new reset requirements and the existing `disable` and `regenerate` actions on the MFA page agree on what happens to passkeys and backup codes? [Consistency, Design §Reset MFA]
- [x] CHK013 - Is the last-admin guard applied consistently to delete, and is it stated that it does not apply to password set or MFA reset? [Consistency]
- [x] CHK014 - Are the service-account rules consistent across the design and decisions (blocked for password and MFA reset, allowed for delete)? [Consistency, Decisions]
- [x] CHK015 - Do all three new routes state the same guard set (`login_required`, fresh login, admin role, CSRF)? [Consistency, Design §API]

## Coverage

- [x] CHK016 - Is forced re-enrollment specified for every login path a local user can take, not only password login? [Coverage, Design §Reset MFA]
- [x] CHK017 - Are requirements defined for a user with an active session at the moment of reset or password change, including remember-me cookies? [Coverage]
- [x] CHK018 - Is the case where password login is disabled (`PASSWORD_LOGIN_ENABLED` off) addressed for the set-password action? [Coverage, Edge Case]
- [x] CHK019 - Are requirements defined for two admins acting on the same target at the same time? [Coverage, Edge Case]
- [x] CHK020 - Is failure handling defined for validation errors on the Manage page (re-render with errors versus redirect and flash)? [Coverage]

## Measurability

- [x] CHK021 - Can "password is never logged" be objectively verified, for example by a test on the audit record? [Measurability, Design §Set password]
- [x] CHK022 - Are acceptance criteria defined for the fresh-login requirement on each new route? [Measurability, Tasks]

## Summary

- **Total Items:** 22 (22 checked, 0 open)
- **Focus Areas:** audit detail, session handling, forced re-enrollment coverage, delete side effects, notification
- **Key Gaps Identified:** none open; answers are in design.md under Security Behaviour



