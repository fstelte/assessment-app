# SCIM 2.0 Implementation Plan

**Protocol:** SCIM 2.0 (RFC 7643 / RFC 7644)  
**Identity Provider:** Microsoft Entra ID  
**Scope:** Group-based user provisioning and deprovisioning  

---

## Overview

This platform currently provisions users via SAML JIT (just-in-time) on first login and maps Entra group OIDs to platform roles through the `AADGroupMapping` table. SCIM adds **push-based provisioning** so that Entra ID can create, update, and deprovision users and groups automatically — even before the user ever logs in — and can revoke access when users are removed from groups in the directory.

SCIM will complement (not replace) the existing SAML flow. SAML continues to handle authentication; SCIM handles lifecycle management.

---

## Architecture

```
Entra ID (IdP)
    │
    │  HTTPS SCIM 2.0 (Bearer token)
    ▼
/scim/v2/                    ← New Flask Blueprint
    ├── /ServiceProviderConfig
    ├── /Schemas
    ├── /Users
    │     ├── GET    (list / filter)
    │     ├── POST   (create)
    │     ├── GET    /{id}
    │     ├── PUT    /{id}
    │     ├── PATCH  /{id}
    │     └── DELETE /{id}
    └── /Groups
          ├── GET    (list / filter)
          ├── POST   (create — enrols group in AADGroupMapping)
          ├── GET    /{id}
          ├── PUT    /{id}
          ├── PATCH  /{id}   ← primary: add/remove members
          └── DELETE /{id}   ← removes mapping + deprovisions members

Platform models (existing)
    ├── User          ← provisioned / deprovisioned
    ├── Role          ← unchanged
    └── AADGroupMapping  ← group OID → role mapping
```

---

## New Components

### 1. `scaffold/apps/scim/` — Blueprint

| File | Responsibility |
|---|---|
| `__init__.py` | Blueprint factory, registers blueprint as `scim` |
| `routes.py` | All SCIM HTTP endpoints |
| `schemas.py` | SCIM JSON serialisation / deserialisation for User and Group resources |
| `auth.py` | Bearer token authentication decorator |
| `provisioner.py` | Business logic: create/update/deprovision users; group membership sync |
| `errors.py` | SCIM-compliant error response helpers |

### 2. Database — New Table: `scim_tokens`

```python
class SCIMToken(db.Model):
    __tablename__ = "scim_tokens"

    id          = db.Column(db.Integer, primary_key=True)
    token_hash  = db.Column(db.String(128), unique=True, nullable=False)  # SHA-256 hex
    description = db.Column(db.String(255))
    is_active   = db.Column(db.Boolean, default=True, nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)
```

Tokens are long-lived random strings (256-bit) stored only as SHA-256 hashes. Generated and managed by admins in the existing admin panel.

### 3. Extend `AADGroupMapping`

Add a `scim_display_name` column to store the Entra group display name received via SCIM, so the admin UI can show human-readable names instead of raw OIDs.

```python
scim_display_name = db.Column(db.String(255), nullable=True)
```

---

## Authentication

All `/scim/v2/*` routes are protected by a `@require_scim_token` decorator:

```python
# scaffold/apps/scim/auth.py
from functools import wraps
import hashlib
from flask import request, abort
from scaffold.apps.scim.models import SCIMToken

def require_scim_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            abort(401)
        raw_token = auth_header[7:]
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        token = SCIMToken.query.filter_by(
            token_hash=token_hash, is_active=True
        ).first()
        if not token:
            abort(401)
        token.last_used_at = datetime.utcnow()
        db.session.commit()
        return f(*args, **kwargs)
    return decorated
```

CSRF protection is bypassed for the `/scim/` prefix (same approach as the SAML ACS endpoint).

---

## SCIM Resource Mapping

### User Resource → `User` model

| SCIM attribute | Platform field |
|---|---|
| `id` | `user.azure_oid` (stable, IdP-assigned) |
| `externalId` | `user.azure_oid` |
| `userName` | `user.aad_upn` |
| `name.givenName` | `user.first_name` |
| `name.familyName` | `user.last_name` |
| `emails[primary]` | `user.email` |
| `active` | `user.status == ACTIVE` |

### Group Resource → `AADGroupMapping`

| SCIM attribute | Platform field |
|---|---|
| `id` | `group_object_id` (Entra OID, normalised to lowercase) |
| `externalId` | `group_object_id` |
| `displayName` | `scim_display_name` |
| `members[].value` | `user.azure_oid` references |

Groups are not stored as first-class entities; a SCIM Group maps to one `AADGroupMapping` row (one role). If a group has not been pre-configured with a role in the admin panel, the SCIM create/patch is accepted but no role is assigned until an admin maps it.

---

## Endpoint Specifications

### `GET /scim/v2/ServiceProviderConfig`

Returns SP capabilities. Key flags:

```json
{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
  "patch": { "supported": true },
  "bulk": { "supported": false },
  "filter": { "supported": true, "maxResults": 200 },
  "changePassword": { "supported": false },
  "sort": { "supported": false },
  "etag": { "supported": false },
  "authenticationSchemes": [
    { "type": "oauthbearertoken", "name": "OAuth Bearer Token", "primary": true }
  ]
}
```

---

### User Endpoints

#### `POST /scim/v2/Users` — Provision user

1. Parse SCIM User JSON.
2. Look up existing user by `azure_oid` / UPN / email.
3. If not found, create `User` with `status=ACTIVE`, random `password_hash`, and `azure_oid` populated.
4. If found, update profile fields.
5. If `active=false` in payload, set `status=DISABLED`.
6. Return `201 Created` with SCIM User representation.

#### `PATCH /scim/v2/Users/{id}` — Update user

Supports `replace` operations on `active`, `name.*`, `emails`, `userName`.  
Setting `active=false` sets `status=DISABLED` and calls `flask_login.logout_user()` to terminate any active session (via forced session invalidation).

#### `DELETE /scim/v2/Users/{id}` — Deprovision user

Sets `status=DISABLED` and clears all roles. Does **not** hard-delete the row (preserves audit trail). Returns `204 No Content`.

#### `GET /scim/v2/Users` — List / filter

Supports `filter=userName eq "upn@domain.com"` and `filter=externalId eq "oid"` (Entra uses these to check for existence before creating).

---

### Group Endpoints

#### `POST /scim/v2/Groups` — Register group

1. Parse group OID from `id` or `externalId`.
2. Upsert `AADGroupMapping` row (create if absent, preserving any existing role mapping).
3. Store `displayName` in `scim_display_name`.
4. Process initial `members` list: for each member `azure_oid`, look up `User` and call `RoleSyncService.apply()`.
5. Return `201 Created`.

#### `PATCH /scim/v2/Groups/{id}` — Sync membership (primary operation)

This is the most important endpoint. Entra sends this when a user is added to or removed from a group.

Supported operations:

```json
{ "op": "add",    "path": "members", "value": [{ "value": "<azure_oid>" }] }
{ "op": "remove", "path": "members[value eq \"<azure_oid>\"]" }
{ "op": "replace","path": "displayName", "value": "New Name" }
```

Implementation:
- For `add members`: look up user(s) by `azure_oid`, assign the role mapped by `AADGroupMapping`.
- For `remove members`: remove the role for that group from the user. Other roles (from other groups or manual assignment) are untouched.
- Delegate to `RoleSyncService` to maintain consistency with the SAML-time sync logic.

#### `DELETE /scim/v2/Groups/{id}` — Unregister group

1. Remove the `AADGroupMapping` row.
2. For all users who had their role *only* via this group, remove that role.
3. Return `204 No Content`.

---

## Group-Based Role Assignment Flow

```
Entra: User added to Group "Assessment Managers" (OID: abc-123)
    │
    ▼
PATCH /scim/v2/Groups/abc-123
  { "op": "add", "path": "members", "value": [{ "value": "<user-oid>" }] }
    │
    ▼
provisioner.py: add_member_to_group(group_oid="abc-123", user_oid="<user-oid>")
    │
    ├── Look up AADGroupMapping WHERE group_object_id = "abc-123"
    │       → role_id = 2 (manager)
    ├── Look up User WHERE azure_oid = "<user-oid>"
    └── Call user.ensure_role("manager")  →  writes to user_roles

Entra: User removed from group
    │
    ▼
PATCH /scim/v2/Groups/abc-123
  { "op": "remove", "path": "members[value eq \"<user-oid>\"]" }
    │
    ▼
provisioner.py: remove_member_from_group(group_oid="abc-123", user_oid="<user-oid>")
    └── Remove role mapped by AADGroupMapping from user (if user not in another
        group that maps to the same role)
```

---

## Admin Panel Integration

Add a new section to the existing admin panel (`scaffold/apps/admin/`):

### Token Management (`/admin/scim/tokens`)

- List active SCIM tokens (show description, `last_used_at`, creation date — never show raw token value again after creation).
- Generate new token: show once, confirm copied.
- Revoke token (set `is_active=False`).

### Group-to-Role Mapping (`/admin/scim/groups`)

Reuse / extend the existing Entra group mapping UI (`AADGroupMapping`) to also show `scim_display_name` and whether the group was registered via SCIM vs manually.

---

## Error Handling

All error responses must conform to the SCIM error schema:

```json
{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
  "status": "400",
  "scimType": "invalidValue",
  "detail": "Attribute 'userName' is required."
}
```

| Scenario | HTTP Status | `scimType` |
|---|---|---|
| Missing required field | 400 | `invalidValue` |
| Resource not found | 404 | — |
| Duplicate resource | 409 | `uniqueness` |
| Invalid filter | 400 | `invalidFilter` |
| Auth failure | 401 | — |
| Unsupported operation | 501 | — |

---

## Entra ID Configuration (SCIM Connector)

In the Entra ID Enterprise Application:

1. Navigate to **Provisioning → Automatic**.
2. Set **Tenant URL** to `https://<your-domain>/scim/v2`.
3. Set **Secret Token** to the value generated in the admin panel.
4. Under **Mappings**, enable both **Provision Azure Active Directory Users** and **Provision Azure Active Directory Groups**.
5. Configure **Attribute Mappings**:
   - `objectId` → `id` (matching property)
   - `userPrincipalName` → `userName`
   - `mail` → `emails[type eq "work"].value`
   - `givenName` → `name.givenName`
   - `surname` → `name.familyName`
   - `AccountEnabled` → `active`
6. Under **Scope**, set to **Assigned users and groups**.
7. Assign only the groups that should have access to the platform.

---

## Coexistence with SAML JIT

| Event | SAML JIT | SCIM |
|---|---|---|
| New user added to group in Entra | Nothing until first login | User provisioned immediately |
| User logs in via SSO | Profile updated; roles synced | No action (user already exists) |
| User removed from group | Role removed at next login | Role removed immediately |
| User disabled in Entra | No effect until next login attempt | `active=false` PATCH → `DISABLED` immediately |
| Admin manually assigns a role | Persisted; SCIM won't remove it (out-of-band) | Preserved; only SCIM-managed roles are touched |

The `RoleSyncService` already distinguishes between roles under `AADGroupMapping` control and manually assigned roles. SCIM provisioning should call the same service to maintain this invariant.

---

## Security Considerations

- **Token strength:** Tokens must be cryptographically random (256-bit / 32 bytes from `secrets.token_urlsafe(32)`). Store only the SHA-256 hash.
- **HTTPS only:** Block SCIM over plain HTTP (`SAML_STRICT`-equivalent check or reverse-proxy enforcement).
- **No CSRF:** SCIM endpoints are server-to-server; add the `/scim/` prefix to the CSRF exemption list.
- **Rate limiting:** Apply `flask_limiter` to SCIM endpoints to prevent abuse (e.g., `100/minute`).
- **Audit logging:** All provisioning actions (create, disable, role change) must write to the existing audit log using the same pattern as SAML login events.
- **Principle of least privilege:** The Entra SCIM connector credentials should be scoped to a dedicated Enterprise Application, not a personal user account.
- **Hard delete prevention:** SCIM DELETE must never hard-delete user rows; audit trails must be preserved.

---

## Migration Steps

1. **Create migration:** Add `scim_tokens` table and `scim_display_name` column to `aad_group_mapping`.
2. **Implement `scaffold/apps/scim/`** blueprint (all files listed above).
3. **Register blueprint** in `scaffold/__init__.py` with URL prefix `/scim/v2`.
4. **Add CSRF exemption** for `/scim/` in `scaffold/extensions.py`.
5. **Add admin routes** for token management in `scaffold/apps/admin/routes.py`.
6. **Add admin templates** for token management and group visibility.
7. **Write tests** in `tests/test_scim_*.py` covering:
   - Token auth acceptance and rejection
   - User create / update / disable / delete
   - Group create / member add / member remove / delete
   - Filter queries (`userName eq`, `externalId eq`)
   - Role assignment and revocation via group membership

---

## File Creation Checklist

```
scaffold/
└── apps/
    └── scim/
        ├── __init__.py
        ├── auth.py          (bearer token decorator)
        ├── errors.py        (SCIM error helpers)
        ├── models.py        (SCIMToken model)
        ├── provisioner.py   (create/update/deprovision logic)
        ├── routes.py        (all SCIM endpoints)
        └── schemas.py       (SCIM JSON serialise/deserialise)

migrations/
└── versions/
    └── xxxx_add_scim_tokens_and_group_display_name.py

scaffold/apps/admin/
├── routes.py               (extend: token management)
└── templates/admin/
    ├── scim_tokens.html
    └── scim_groups.html     (extend existing group mapping page)

tests/
├── test_scim_auth.py
├── test_scim_users.py
└── test_scim_groups.py
```

---

## Dependencies

No new third-party libraries are required. The implementation uses only:

- `secrets` (stdlib) — token generation
- `hashlib` (stdlib) — token hashing
- Flask JSON responses — SCIM payloads are plain JSON
- Existing `db`, `User`, `Role`, `AADGroupMapping`, `RoleSyncService`
