---
title: Admin MFA reset clears all methods
date: 2026-09-24
status: accepted
---

## Context

The existing "regenerate" action on `/admin/users/<id>/mfa` only replaces the TOTP secret. A user with a passkey stays enrolled and is never forced to re-enroll.

## Decisions

A new `POST /admin/users/<id>/mfa/reset` deletes the `MFASetting` row (TOTP secret and backup codes) and all passkeys, invalidates the user's sessions and logs `user_mfa_reset`. The existing local-account enforcement in `auth/routes.py` then sends the user to `mfa_enroll` at the next password login.

- An admin cannot reset their own MFA.
- Service accounts and federated (Entra) users are blocked.
- A SAML sign-in relies on the IdP for MFA and does not force local enrollment (existing behaviour).

Security checklist decisions (2026-09-24): the user is not notified (no mail infrastructure); any user status is allowed; the existing enable, regenerate and disable actions are unchanged.

## Alternatives considered

- Clear TOTP only: a user with a passkey would not be forced to re-enroll.

## Consequences

- No schema change.
- Signed-in sessions survive the reset when Redis sessions are not enabled.
