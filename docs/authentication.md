# Authentication & Authorisation

The scaffold now relies exclusively on SAML 2.0 single sign-on provided by
Microsoft Entra ID (Azure AD). The Python application acts as the service
provider, provisions users on the fly, synchronises role membership, and still
reuses the hardened session helpers inherited from the legacy BIA/CSA apps.

## Microsoft Entra Setup Checklist

1. **Create the enterprise application** – In Entra ID go to *Enterprise
   applications → New application → Create your own application* and choose the
   non-gallery SAML option.
2. **Import service provider metadata** – Download
   `https://<your-host>/auth/login/saml/metadata` and use it to populate the
   Entity ID, ACS, and SLO URLs. Substitute the host when testing locally.
3. **Configure required claims** – Issue email address, given name, surname,
   display name, object ID, and user principal name. Add the groups claim in the
   *Token configuration* tab and set `groupMembershipClaims` to *Security
   groups* or *Groups assigned to the application* for large tenants.
4. **Map attributes** – Align the Entra claims with the `SAML_ATTRIBUTE_*`
   values listed below. NameID should usually be the user principal name but
   email works when it is unique across the tenant.
5. **Provide IdP details to the app** – Export the Entra signing certificate and
   copy the SSO/SLO URLs into `SAML_IDP_CERT`, `SAML_IDP_SSO_URL`, and
   `SAML_IDP_SLO_URL`. Enable request or response signing if required.
6. **Assign pilot users or groups** – Grant access to the enterprise application
   and, if needed, limit application-side access with `SAML_ALLOWED_GROUP_IDS`.
   Ensure every group you expect to sync appears in `SAML_ROLE_MAP` or the
   database mapping table.
7. **Decide on AuthN context** – Adjust `SAML_REQUESTED_AUTHN_CONTEXT` and
   `SAML_REQUESTED_AUTHN_CONTEXT_COMPARISON` to reflect your MFA posture. Leave
   them empty when Conditional Access already enforces MFA.
8. **Validate logout and RelayState** – Set `SAML_LOGOUT_RETURN_URL` to the page
   users should see after SLO and confirm RelayState survives the IdP round trip
   if you rely on deep-linking.

### Environment Variable Reference

| Setting | Purpose |
| --- | --- |
| `SAML_SP_ENTITY_ID` | Identifier for this service provider (also in metadata). |
| `SAML_SP_ACS_URL` / `SAML_SP_SLS_URL` | Assertion consumer and single logout service URLs. |
| `SAML_SP_CERT` / `SAML_SP_PRIVATE_KEY` | PEM material for signing or decrypting SAML messages. |
| `SAML_IDP_ENTITY_ID` | Issuer value provided by Entra ID. |
| `SAML_IDP_SSO_URL` / `SAML_IDP_SLO_URL` | Login and logout endpoints exposed by Entra. |
| `SAML_IDP_CERT` | IdP certificate used to verify SAML responses. |
| `SAML_ATTRIBUTE_EMAIL` / `FIRST_NAME` / `LAST_NAME` / `DISPLAY_NAME` / `OBJECT_ID` / `UPN` | Attribute names for user provisioning. |
| `SAML_ATTRIBUTE_GROUPS` | Attribute emitting Entra group object IDs. |
| `SAML_ALLOWED_GROUP_IDS` | Comma-separated list of group IDs authorised to sign in. |
| `SAML_ROLE_MAP` | JSON mapping of group IDs to internal role slugs. |
| `SAML_REQUESTED_AUTHN_CONTEXT` | JSON array of requested AuthN context class references. |
| `SAML_REQUESTED_AUTHN_CONTEXT_COMPARISON` | Comparison mode (`exact`, `minimum`, `better`, or `maximum`). |
| `SAML_LOGOUT_RETURN_URL` | Optional absolute URL for redirecting after SLO. |
| `FORWARDED_ALLOW_IPS` | Enables `ProxyFix` to trust reverse proxy headers. |
| `PASSWORD_LOGIN_ENABLED` | Toggles the break-glass password form. |

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
  the ability to impersonate your service provider. Refer to the runbook below
  when rotating certificates or shared secrets.

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

## Troubleshooting

- **403 after login** – Review `scaffold.apps.auth.routes` logs for "Access
  denied" warnings. The user is usually outside `SAML_ALLOWED_GROUP_IDS` or the
  mapped role is missing. Confirm the groups claim delivers object IDs and that
  `SAML_ROLE_MAP` (or the database mapping table) contains them.
- **Missing groups claim** – Ensure `groupMembershipClaims` is enabled on the
  enterprise application. For users in many groups, prefer the *Groups assigned
  to the application* mode or enable the Microsoft Graph callout so Entra emits
  the claim consistently.
- **Signature validation failed** – Refresh `SAML_IDP_CERT` with the latest IdP
  certificate and verify the signing algorithms align with the app settings.
  Expired or rotated certificates are the most common cause.
- **Invalid requested AuthnContext** – Relax
  `SAML_REQUESTED_AUTHN_CONTEXT` or change the comparison mode to `minimum` when
  Entra cannot satisfy the request. Leave the array empty if Conditional Access
  already guarantees MFA.
- **RelayState lost after logout** – Set `SAML_LOGOUT_RETURN_URL` to the desired
  landing page and disable Entra's default return URL so the RelayState value
  survives the round trip.
- **Clock skew errors** – Ensure the servers synchronise with NTP. SAML allows
  only a few minutes of drift.

## Operational Runbooks

### Rotate SAML Certificates and Secrets

1. Generate new service provider certificates (signing and encryption when
  applicable) and store them securely.
2. Update the secret stores used by Ansible, Docker, and CI with the new PEM
  material while keeping the old values until the cutover succeeds.
3. Deploy to staging first. Confirm the logs show
  `Loaded SAML service provider certificate` and perform an end-to-end login
  and logout.
4. Regenerate `/auth/login/saml/metadata` and upload it to Entra. Validate that
  Entra recognises the new certificate.
5. Roll the change into production. After a successful smoke test, remove the
  retired certificates from every secret store.

### Enable a New Entra Group

1. Capture the group's object ID and add pilot members. Verify the group is
  assigned to the enterprise application.
2. Update `SAML_ALLOWED_GROUP_IDS` (if access is gated) and extend
  `SAML_ROLE_MAP` with the new mapping. Commit the change alongside your
  configuration.
3. Ensure the target role exists in the database (`Role` table). Seed it via the
  admin UI or CLI helpers if required.
4. Redeploy. Ask a member of the new group to sign in and review the logs for
  `Role sync` entries confirming the mapping.

### Break-Glass Login Access

1. Set `PASSWORD_LOGIN_ENABLED=true` in the deployment environment and redeploy.
2. Rotate or reset the break-glass account with
  `flask --app scaffold:create_app create-admin`. Share credentials securely
  with the incident handler.
3. Once normal operations resume, set `PASSWORD_LOGIN_ENABLED=false`, redeploy,
   and confirm `/auth/login` redirects straight to SAML.
4. Rotate the break-glass password again and document the event in the incident
  timeline.

---

## SCIM 2.0 Automated Provisioning

SCIM (System for Cross-domain Identity Management, RFC 7643/7644) adds
**push-based** lifecycle management on top of the SAML JIT flow. Entra ID calls
the platform's SCIM endpoint to create, update, and deprovision users and groups
automatically — even before a user ever logs in.

SCIM **complements** SAML. SAML continues to handle authentication and
session issuance; SCIM handles lifecycle events (create, disable, group
membership changes).

### Overview

```
Microsoft Entra ID  ──HTTPS SCIM 2.0 (Bearer token)──▶  /scim/v2/
                                                             │
                                                      Bearer token validated
                                                      against scim_tokens table
                                                             │
                                                      Provisioner
                                                       ├── User create/update/disable
                                                       └── Group → AADGroupMapping
                                                               └── Role assignment
```

### Step 1 — Run the Database Migration

The SCIM feature requires two schema changes:

- A new `scim_tokens` table to store hashed bearer tokens.
- A `scim_display_name` column on `aad_group_mappings` to store human-readable
  Entra group names received via SCIM.

Apply the migration before enabling the connector:

```bash
flask --app scaffold:create_app db upgrade
```

### Step 2 — Generate a Bearer Token

1. Sign in to the platform as an administrator.
2. Navigate to **Admin → SCIM Tokens** (`/admin/scim/tokens`).
3. Enter a description (e.g. `Entra SCIM connector`) and click **Generate Token**.
4. **Copy the token immediately** — it is shown only once. The platform stores
   only the SHA-256 hash; the raw value cannot be recovered.
5. Keep the token in a secrets manager (key vault, Ansible vault, or equivalent).
   Treat it as a long-lived credential with the same sensitivity as a service
   account password.

To revoke a token (e.g. after a rotation), return to the same page and click
**Revoke**. The old token stops working immediately on the next request.

### Step 3 — Configure the Entra ID Enterprise Application

The SCIM connector is added to the **same** enterprise application that handles
SAML SSO. Within the application:

1. Go to **Provisioning** → set the provisioning mode to **Automatic**.
2. Under **Admin Credentials**:
   - **Tenant URL**: `https://<your-domain>/scim/v2`
   - **Secret Token**: the value generated in Step 2.
3. Click **Test Connection** to verify connectivity. Entra will call
   `GET /scim/v2/ServiceProviderConfig` with the Bearer token.
4. Under **Mappings**, enable both:
   - **Provision Azure Active Directory Users**
   - **Provision Azure Active Directory Groups**
5. Configure **User attribute mappings** to align with the platform fields:

   | Entra attribute | SCIM attribute |
   |---|---|
   | `objectId` | `id` (matching property) |
   | `objectId` | `externalId` |
   | `userPrincipalName` | `userName` |
   | `mail` | `emails[type eq "work"].value` |
   | `givenName` | `name.givenName` |
   | `surname` | `name.familyName` |
   | `accountEnabled` | `active` |

6. Under **Scope**, set to **Assigned users and groups** so that only users
   and groups explicitly assigned to the application are synced.
7. Assign the groups that should have platform access to the enterprise
   application.
8. Save and set the provisioning status to **On**.

### Step 4 — Map Groups to Roles

Groups are registered automatically when Entra first pushes them. Until an
administrator maps a group to a role, members are provisioned as active users
but receive no role.

**To map a group to a role:**

1. Navigate to **Admin → SCIM Groups** (`/admin/scim/groups`) to see all groups
   registered via SCIM and their `scim_display_name` (populated automatically
   from Entra).
2. The actual role assignment is managed in the **Entra Group Mapping** section
   of the user administration panel. Find the group by its OID and select the
   target platform role.

Once mapped, all users Entra subsequently adds to that group (via
`PATCH /scim/v2/Groups/{id}`) will automatically receive the corresponding role.
Removing a user from the group in Entra removes the role immediately.

### SCIM Endpoint Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/scim/v2/ServiceProviderConfig` | Returns SP capabilities (used by Entra during test connection) |
| `GET` | `/scim/v2/Schemas` | Schema discovery |
| `GET` | `/scim/v2/Users` | List users; supports `filter=userName eq "…"` and `filter=externalId eq "…"` |
| `POST` | `/scim/v2/Users` | Provision a new user |
| `GET` | `/scim/v2/Users/{id}` | Fetch a user by Entra OID |
| `PUT` | `/scim/v2/Users/{id}` | Replace all user attributes |
| `PATCH` | `/scim/v2/Users/{id}` | Partial update (active, name, emails, userName) |
| `DELETE` | `/scim/v2/Users/{id}` | Disable user and clear roles (no hard delete) |
| `GET` | `/scim/v2/Groups` | List groups; supports `filter=externalId eq "…"` |
| `POST` | `/scim/v2/Groups` | Register a group / upsert AADGroupMapping |
| `GET` | `/scim/v2/Groups/{id}` | Fetch a group by OID |
| `PUT` | `/scim/v2/Groups/{id}` | Replace group attributes and member list |
| `PATCH` | `/scim/v2/Groups/{id}` | Add/remove members or update displayName |
| `DELETE` | `/scim/v2/Groups/{id}` | Remove group mapping and revoke managed roles |

All requests must include `Authorization: Bearer <token>`. CSRF protection is
not applied to `/scim/v2/*` routes; authentication is handled entirely by the
bearer token.

### How SCIM and SAML Coexist

| Event | SAML JIT (existing) | SCIM (new) |
|---|---|---|
| User added to Entra group | Nothing until first login | User provisioned immediately |
| User logs in via SSO | Profile updated; roles synced | No action (user already exists) |
| User removed from group in Entra | Role removed at next login | Role removed immediately |
| `accountEnabled=false` in Entra | No effect until next login attempt | `active=false` PATCH → account disabled immediately |
| Admin manually assigns a role | Persisted | Preserved; SCIM only touches roles it manages |

### Security Considerations

- **Token strength** — Tokens are 256-bit random strings generated with
  `secrets.token_urlsafe(32)`. Only the SHA-256 hash is persisted; the raw
  value is irrecoverable after the creation page is closed.
- **HTTPS only** — The SCIM endpoint must be behind TLS. Never expose it over
  plain HTTP; enforce this at the reverse proxy (nginx) level.
- **Least privilege** — Scope the Entra provisioning credentials to the dedicated
  enterprise application, not to a personal user account.
- **Rate limiting** — SCIM routes are limited to 100 requests per minute per
  source IP (via `flask-limiter`). Entra's provisioning service stays well within
  this bound under normal operation.
- **Audit trail** — Every provisioning action (user created, user disabled, role
  assigned, role revoked, group registered, group deleted) is written to the
  platform audit log. Review it at **Admin → Audit Trail**.
- **No hard deletes** — `DELETE /scim/v2/Users/{id}` disables the account and
  clears roles but never removes the database row, preserving audit history.

### Troubleshooting

- **Test Connection fails (401)** — Confirm the Secret Token in Entra matches
  the value generated on the token management page. Tokens are case-sensitive.
  Check that the token has not been revoked in **Admin → SCIM Tokens**.
- **Test Connection fails (connection error)** — Verify `https://<your-domain>/scim/v2/ServiceProviderConfig`
  is reachable from the internet (or from Entra's egress IPs). Check the nginx
  reverse proxy configuration and any firewall rules.
- **Users provisioned but have no role** — The group has been registered but
  not yet mapped to a role. Complete Step 4 above. Once mapped, trigger a
  re-sync in Entra (Provisioning → Provision on demand).
- **Role not revoked when user removed from group** — Check the audit log for
  `scim_role_revoked` entries. If absent, confirm the PATCH operation reached
  the application by reviewing nginx access logs. Entra may retry failed
  operations after a backoff period.
- **Provisioning cycle stuck** — Entra's provisioning service can pause after
  repeated errors. Review the provisioning logs in Entra (Provisioning →
  Provisioning logs) and ensure the platform returned appropriate 2xx/4xx
  responses rather than 5xx errors.
- **Duplicate `scim_display_name` after group rename** — The display name is
  updated whenever Entra sends a `PATCH /scim/v2/Groups/{id}` with
  `op: replace, path: displayName`. If the name appears stale, trigger
  **Provision on demand** for the affected group in Entra.

### Rotate a SCIM Token

1. Generate a new token in **Admin → SCIM Tokens** and copy its value.
2. Update the **Secret Token** in the Entra provisioning configuration and save.
3. Click **Test Connection** to confirm the new token is accepted.
4. Return to **Admin → SCIM Tokens** and revoke the old token.
