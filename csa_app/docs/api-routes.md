# API & Route Catalog

This document summarizes the key routes exposed by the Control Self-Assessment application. All paths are relative to the application root. Unless noted otherwise, responses render HTML templates. JSON APIs will be added as part of the assessments roadmap.

## Authentication Blueprint (`/auth`)

| Route | Method | Description | Auth | Notes |
|-------|--------|-------------|------|-------|
| `/auth/register` | GET/POST | Registration form for new users. | Public | Sends activation email placeholder; pending admin approval. |
| `/auth/login` | GET/POST | Username/password authentication. | Public | Initiates MFA challenge when user is enrolled. |
| `/auth/logout` | POST | Ends the current session. | Logged-in | CSRF-protected form submission. |
| `/auth/mfa/setup` | GET/POST | Guides enrolled users through MFA activation. | Logged-in | Displays QR code, verifies TOTP. |
| `/auth/mfa/verify` | GET/POST | Completes MFA challenge after password login. | Pending MFA | Requires `mfa_user_id` in session. |
| `/auth/mfa/reset` | POST | Resets MFA secret for the current user. | Logged-in | Optional self-service, feature-flagged. |

## Admin Blueprint (`/admin`)

| Route | Method | Description | Auth | Notes |
|-------|--------|-------------|------|-------|
| `/admin/` | GET | Landing page for administrators. | Admin role | Displays outstanding registrations and MFA status. |
| `/admin/activate/<int:user_id>` | POST | Activates a pending user. | Admin role | Marks `User.status = active`. |
| `/admin/manage_user_mfa/<int:user_id>` | GET/POST | View, enable, disable, or reset MFA for a user. | Admin role | Produces new secrets and provisioning URIs. |

## Assessment Blueprint (`/assessments`)

_Assessment CRUD endpoints are under development (Section 3 roadmap). Placeholder routes include:_

| Route | Method | Description |
|-------|--------|-------------|
| `/assessments/` | GET | List assessments available to the logged-in user (pending implementation). |
| `/assessments/<int:assessment_id>` | GET | Detailed view with assigned controls and responses. |
| `/assessments/assign` | GET/POST | Assign an assessment template to an active user (role: manager/admin). |

## Service Endpoints

| Route | Method | Description |
|-------|--------|-------------|
| `/healthz` | GET | Lightweight application health check. |

## CLI Commands

| Command | Description |
|---------|-------------|
| `flask --app autoapp create-admin` | Prompts for credentials and creates an admin user with MFA disabled. |
| `flask --app autoapp import-controls iso_27002_controls.json` | Imports control definitions from the provided JSON payload. |
| `flask --app autoapp db upgrade` | Applies database migrations using Alembic. |

## Planned API Extensions

- JSON-based endpoints for assessments, controls, and responses to support SPA or external integrations.
- Webhook callbacks for control import status.
- Admin reporting APIs for compliance dashboards.
