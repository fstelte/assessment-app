# Authentication & Authorisation

The scaffold combines the hardening rules from both `bia_app` and `csa_app`:
password-based sign-in, mandatory multi-factor authentication (MFA), anchored
session metadata, and strict response headers.

## Flow Overview

1. **Password validation** – Accounts must be `ACTIVE`, mirroring CSA's status
   enum. Dormant accounts are blocked prior to issuing any session state.
2. **MFA challenge** – `queue_mfa_enrolment` and `queue_mfa_verification`
   (from `scaffold.apps.auth.flow`) store the user ID plus remember-me flag in
   the session, deferring completion until a TOTP token is confirmed.
3. **Session issuance** – `finalise_login` applies the same fingerprinting and
   idle timeouts that BIA enforced, reusing helpers from
   `scaffold.core.security`.
4. **Response hardening** – `scaffold.core.security_headers` attaches CSP,
   HSTS, and other secure headers after each response, matching the legacy BIA
   deployment profile.

## Reusable Utilities

| Location | Responsibility |
| --- | --- |
| `scaffold.apps.auth.flow` | Queues MFA states, finalises logins, and exposes `ensure_mfa_provisioning` + `clear_mfa_state`. |
| `scaffold.apps.auth.mfa` | Generates PyOTP secrets and validates tokens. |
| `scaffold.core.security` | Provides session fingerprint validation and the `require_fresh_login` decorator. |
| `scaffold.core.security_headers` | Injects frame/XSS protections, CSP, and conditional HSTS. |
| `scaffold.apps.admin` | Uses the shared helpers for user MFA management and enforces fresh-login policies. |

These modules are import-safe for CLI scripts or API blueprints that need to
reuse the same guarantees without touching the UI routes directly.

## User Model & Roles

- Based on CSA's `User` entity with status enum (`pending`, `active`, `disabled`).
- Carries BIA fields (first/last name, theme preference) and links to MFA and
  assessment relationships.
- Roles live in `roles` with a many-to-many association to users; migrate BIA's
  string role column by seeding `Role` rows and linking via `user_roles`.
- Prefer role checks (e.g. `current_user.has_role("admin")`) over bespoke
  booleans.

## MFA Lifecycle

- `ensure_mfa_provisioning` creates or resets `MFASetting` entries and returns
  the provisioning URI for QR code display.
- `mfa_enroll` and `mfa_verify` both end by calling `finalise_login`, so all
  session guards (fingerprint, timestamps) apply uniformly.
- Remember-device behaviour mirrors CSA: the remember flag survives the MFA
  challenge and is consumed on successful verification.

## Session Security

- `init_session_security` enforces a 12-hour idle timeout (configurable) and
  compares the stored fingerprint with the current request's user-agent.
- `require_fresh_login` decorates destructive actions (BIA used it for delete
  flows) to demand a recent password entry.
- Cookies default to `Secure`, `HttpOnly`, and `SameSite=Lax`; override via
  `Settings` if a different profile is needed.

## Backward Compatibility

- Password hashes remain Werkzeug-compatible; migrating users does not require
  re-hashing.
- Existing MFA secrets map directly to `MFASetting.secret`; mark
  `enabled/enrolled_at` during migration to skip forced re-enrolment.
- External integrations that referenced unprefixed BIA tables should now target
  the `users`, `mfa_settings`, and `bia_*/csa_*` tables or consume compatibility
  views.

## Future Enhancements

- Add WebAuthn or FIDO2 routes that still delegate to `finalise_login` once the
  assertion passes.
- Persist remember-device approvals server-side rather than in the session for
  better auditability.
- Surface an admin console for role assignment and MFA enforcement policies.
