# MFA Operations Manual

This manual explains how administrators and end-users enable, verify, and maintain multi-factor authentication (MFA) in the Control Self-Assessment platform.

## Overview

- MFA uses Time-based One-Time Passwords (TOTP) compatible with standard authenticator apps (Microsoft Authenticator, Google Authenticator, Authy, 1Password, etc.).
- Secrets are generated per user and stored encrypted in the database via the `MFASetting` model.
- Verification occurs during login, using `pyotp.TOTP` with 30-second intervals and a ±1 step validation window.

## User Enrollment Flow

1. User registers via `/auth/register` or is provisioned by an administrator.
2. After activation, the user clicks **MFA instellen** (nav button served by `/auth/mfa/manage`).
3. The page displays a QR code (rendered using the provisioning URI) and a manual code fallback.
4. The user scans the QR code with an authenticator app.
5. The user enters the generated 6-digit code. The backend verifies it with `MFASetting.verify_token`.
6. Upon success, the `enrolled_at` timestamp is set to the current UTC time and future logins require MFA.

## Login Challenge

1. User submits credentials at `/auth/login`.
2. If the user has MFA enabled, the backend stores `mfa_user_id` in the session and redirects to `/auth/mfa/verify`.
3. The user enters their current 6-digit code.
4. Verification uses the same tolerance window as enrollment. On success, `last_verified_at` is updated and the user session is finalised.
5. After three consecutive failures the session is cleared; the user must restart the login flow.

## Admin Management

- Navigate to `/admin/manage_user_mfa/<user_id>` to review the status of any user.
- Admins can:
  - Enable MFA for a user and hand over the provisioning URI manually.
  - Reset a secret, forcing the user to re-enroll on next login.
  - Disable MFA entirely (recorded with an audit note in roadmap items).
- The admin view surfaces `enrolled_at` and `last_verified_at` timestamps for auditing.

## CLI Utilities

- `poetry run flask --app autoapp create-admin`: Creates a new admin user (MFA disabled by default).
- `poetry run flask --app autoapp rotate-mfa --user <email>`: _Roadmap_ command to rotate secrets via CLI.

## Troubleshooting

| Symptom | Resolution |
|---------|------------|
| Codes keep failing | Ensure the authenticator device has correct time; allow a ±1 step drift via configuration. |
| Lost device | Admin resets MFA via `/admin/manage_user_mfa/<user_id>`; user re-enrolls with new device. |
| No QR code displayed | Verify that Flask can generate the provisioning URI; fall back to manual code entry. |

## Security Considerations

- Secrets are generated using `secrets.token_hex` and stored with rotational history (planned feature).
- Enforce HTTPS in production so provisioning URIs and verification codes are exchanged securely.
- Never share raw secrets over insecure channels; prefer QR codes or secure messaging.
- Audit logs for MFA events are planned under the assessments reporting roadmap.
