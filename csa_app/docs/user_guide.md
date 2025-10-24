# User Guide

This guide covers the end-to-end workflow for users of the Control Self-Assessment platform.

## Registration & Activation

1. Navigate to `/auth/register`.
2. Provide name, email address, and a password that meets the policy (minimum length 8, complexity enforced by form validators).
3. Await administrator approval. Pending users cannot log in until activated.
4. After activation, log in via `/auth/login`.

## Multi-Factor Authentication (MFA)

1. After first login, click **MFA instellen** in the top navigation.
2. Scan the QR code with an authenticator app (Microsoft Authenticator, Google Authenticator, 1Password, etc.).
3. Enter the six-digit verification code to complete enrollment.
4. Future logins require both password and MFA code.
5. If you lose your device, contact an administrator to reset your MFA secret.

## Profiel beheren

- Open **Beheer & MFA → Mijn profiel** om persoonlijke voorkeuren aan te passen.
- Kies een thema (donker of licht); wijzigingen worden direct opgeslagen na bevestiging.
- Stel een nieuw wachtwoord in door het huidige wachtwoord en vervolgens twee keer het nieuwe wachtwoord in te voeren.
- Vanuit dezelfde pagina start u MFA inschakelen of resetten via de knop **MFA inschakelen** respectievelijk **MFA opnieuw instellen**.

## Working with Assessments

- Access available assessments from the dashboard (placeholder UI until Section 3 rollout).
- Each assessment lists assigned controls and allows recording evidence or status notes.
- Use the **Save** action to persist updates; audit timestamps track modifications automatically.

## Importing Controls

- Administrators can import control sets via the CLI:
  ```shell
  poetry run flask --app autoapp import-controls iso_27002_controls.json
  ```
- The importer validates structure, reports duplicates, and persists data with timestamps.

## Administrative Actions

- Admin dashboard (`/admin/users`) lists all users with status, roles, and MFA progress.
- Activate users with a single click; deactivation flow is planned for a future release.
- Manage MFA for any user via `/admin/manage_user_mfa/<user_id>`.
- Import control catalogues via `/admin/controls/import`.
- Managers (rol `manager`) gebruiken `/assessments/assign` om zelf-assessments toe te wijzen aan actieve gebruikers.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Unable to log in | Ensure your account is activated and MFA is verified. Contact admin if still blocked. |
| MFA code rejected | Confirm device time sync; request reset if device lost. |
| 500 Internal Server Error | Check whether the database is reachable; review container logs if running in Docker. |

## Support Channels

- **Developers**: open an issue in the repository or contact the engineering Slack channel.
- **Security**: escalate MFA or account-related incidents to the security operations mailbox.
- **Operations**: deployment playbooks and on-call rotation documented in the internal runbook (link placeholder).
