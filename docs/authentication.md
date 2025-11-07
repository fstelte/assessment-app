# Authentication & Authorisation

The scaffold now relies exclusively on SAML 2.0 single sign-on provided by
Microsoft Entra ID (Azure AD). The Python application acts as the service
provider, provisions users on the fly, synchronises role membership, and still
reuses the hardened session helpers inherited from the legacy BIA/CSA apps.

## SAML Single Sign-On Flow

1. **Initiation** – Visiting `/auth/login` immediately redirects to
   `/auth/login/saml`, issuing an AuthN request built from the configured
   `SAML_SP_*` values. Request IDs are stored in the session to defend against
   replay attacks.
2. **Assertion Consumer Service** – The identity provider posts the SAML
   response to `/auth/login/saml/acs`. The handler validates the signature,
   NameID, and attributes before provisioning or updating the local user record.
3. **Role synchronisation** – Group claims are compared with
   `SAML_ALLOWED_GROUP_IDS` and translated via `SAML_ROLE_MAP` plus database
   mappings. Users outside the allowed set are rejected before a session is
   issued.
4. **Session issuance** – `finalise_login` applies the established MFA/session
   fingerprinting rules and the response header hardening provided by
   `scaffold.core.security_headers`.

Additional endpoints include `GET /auth/login/saml/metadata` to publish service
provider metadata and `/auth/login/saml/sls` for single logout. When IdP logout
metadata is supplied the logout route will cascade through Entra and clear local
session state once the SAML logout response is confirmed.

## Attribute Mapping & Provisioning

- Email, first name, last name, display name, directory object ID, and UPN are
  read from the attributes configured via the `SAML_ATTRIBUTE_*` environment
  variables. Missing email addresses cause the login to fail.
- Group claims default to
  `http://schemas.microsoft.com/identity/claims/groups`. Supply additional
  attributes when you need different identifiers (for example, roles or
  department codes) and make sure they are issued in the IdP claim set.
- New users are activated automatically and receive a random break-glass
  password so CLI tasks such as `create-admin` keep functioning. Updating
  profile information is idempotent: the handler only overwrites fields when the
  assertion delivers new values.
- `SAML_ROLE_MAP` accepts a JSON object mapping group IDs to internal role
  slugs. The `RoleSyncService` also honours records in the `aad_group_mappings`
  table so administrators can maintain additional relationships through the UI.

## Reusable Utilities

| Location | Responsibility |
| --- | --- |
| `scaffold.apps.auth.flow` | Queues MFA prompts, finalises logins, and exposes `ensure_mfa_provisioning`/`clear_mfa_state`. |
| `scaffold.apps.auth.mfa` | Generates PyOTP secrets and validates tokens for the break-glass password flow. |
| `scaffold.core.security` | Provides session fingerprint validation and the `require_fresh_login` decorator. |
| `scaffold.core.security_headers` | Injects frame/XSS protections, CSP, and conditional HSTS. |
| `scaffold.apps.admin` | Surfaces MFA management tooling and enforces fresh-login policies. |

These modules are safe to import from scripts or APIs that need to bootstrap
users, manage MFA, or apply the same security posture outside the web routes.

## Session Security & MFA

- `finalise_login` continues to anchor the session to the user-agent and idle
  timeout. Defaults mirror the historic 12-hour inactivity limit.
- MFA enrolment (`/auth/mfa/enroll`) and verification (`/auth/mfa/verify`) still
  operate for local accounts. SAML sign-ins bypass local MFA because Entra is
  expected to enforce tenant-level MFA policies.
- `require_fresh_login` remains available for sensitive actions. It forces
  callers to reauthenticate (via SAML) before destructive operations continue.
- Cookies stay locked down (`Secure`, `HttpOnly`, `SameSite=Lax`). Override them
  through `Settings` only when absolutely necessary.

## Secret Management

- Generate `SECRET_KEY` with `openssl rand -hex 32` (or a managed secret store)
  so Flask sessions and CSRF tokens remain unpredictable.
- Store SAML credentials in secrets management tooling. The Ansible playbooks
  expect values to arrive via `vault_saml_*` variables (see
  `ansible/group_vars/all.yml` for the complete list). Mirror the same keys in
  `.env.production` for container deployments.
- Keep PEM-encoded certificates private. Access to `SAML_SP_PRIVATE_KEY` grants
  the ability to impersonate your service provider.

### Certificate Rotation

1. Issue new signing and encryption certificates for the service provider.
2. Update the secret store entries (`vault_saml_sp_cert`,
   `vault_saml_sp_private_key`, container secrets, CI variables, etc.) with the
   new PEM material while keeping the old values in place.
3. Redeploy the application so the refreshed certificates are loaded into
   memory. You can overlap the rollout with the previous metadata to avoid
   downtime.
4. Regenerate the metadata via `GET /auth/login/saml/metadata` and upload it to
   Entra or any other identity provider tracking the integration.
5. Decommission the previous certificates once federated sign-in succeeds with
   the rotated keys.

## Microsoft Entra SAML Configuration

- Register an **Enterprise Application** in Microsoft Entra ID and configure it
  for SAML-based single sign-on. Use the service provider metadata endpoint to
  populate the Entity ID, ACS, and SLO URLs.
- Issue the following claim set: email address, given name, surname, display
  name, object identifier, user principal name, and group membership (or an
  equivalent attribute that matches `SAML_ATTRIBUTE_GROUPS`).
- Assign users or groups to the enterprise application and, if needed, scope the
  integration further by listing allowed group IDs in `SAML_ALLOWED_GROUP_IDS`.
- Provide the IdP certificate, SSO URL, and SLO URL via `SAML_IDP_CERT`,
  `SAML_IDP_SSO_URL`, and `SAML_IDP_SLO_URL`. Enable request signing or response
  validation flags (`SAML_SIGN_*`, `SAML_WANT_*`) to satisfy your security
  posture.
- Publish the application to end users. They will be redirected through Entra
  when visiting `/auth/login`, and successful assertions will provision/update
  their local accounts automatically.

## Break-Glass Local Login

- The unified scaffold keeps a guarded password form for emergency access and
  automated tests. Toggle it with the `PASSWORD_LOGIN_ENABLED` environment
  variable (legacy aliases `SAML_PASSWORD_LOGIN_ENABLED` /
  `ENTRA_PASSWORD_LOGIN_ENABLED` / `AZURE_PASSWORD_LOGIN_ENABLED` still work).
- When disabled (default), `/auth/login` immediately redirects to the SAML
  handshake. When enabled, the page renders both the password form and the SAML
  button; successful password sign-ins still call the shared helpers so MFA can
  be enforced per user.
