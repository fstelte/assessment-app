# Deployment Guide

This guide outlines deployment options for the scaffold application, focusing on the PostgreSQL backend.

## Containerised Deployment (Docker Compose)

1. Build image: `docker build -t scaffold-app .`
2. Configure environment variables in `docker/.env` (copy from `.env.example`).
3. Start services: `docker compose up -d`.
4. Run migrations: `docker compose exec web poetry run flask --app scaffold:create_app db upgrade`.

The reference Compose file runs the web application alongside PostgreSQL.

### Maintenance Gateway & Fallback Page

- The production compose file now includes an Nginx `gateway` service listening on port 8000. It proxies requests to the Flask `web` container and serves the generated maintenance page whenever the upstream is unavailable (container starting, restarting, or database temporarily offline).
- Customise the message/branding by editing `docker/templates/maintenance.html.tmpl`; the rendered output is shared by Flask (for 503 responses) and Nginx (for upstream failures).
- Because the `web` container no longer exposes a host port, target `http://localhost:8000` via the `gateway` service. Continue using `docker compose exec web ...` for CLI tasks.
- Configure contact information via `.env.production` using `MAINTENANCE_CONTACT_EMAIL` (with optional `MAINTENANCE_CONTACT_LABEL` and `MAINTENANCE_CONTACT_LINK`). The entrypoint renders the HTML before database checks, keeping the page available even if the app fails to boot.

## Kubernetes (Optional)

- Package the application with a Deployment + Service.
- Use a StatefulSet for the database (or managed service).
- Mount secrets via Kubernetes Secrets or an external secret store.
- Configure liveness/readiness probes hitting `/healthz` (to be implemented).

## PostgreSQL Notes

- `psycopg[binary]` ships with the project dependencies; install `psycopg[c]` if your environment allows compiled wheels and you require additional performance.
- Connection string format: `postgresql+psycopg://user:password@host:port/database`.
- Run migrations through `flask db upgrade` as usual.
- Backup strategy: `pg_dump -Fc scaffold > scaffold.dump`.
- Tune `pool_size` and `max_overflow` via `SQLALCHEMY_ENGINE_OPTIONS` if needed.

### Database Backups via Docker Compose

The backup helper in `docker/compose.backup.yml` expects a fully qualified `DATABASE_URL` (or `SQLALCHEMY_DATABASE_URI`). When you start the compose file, make sure Docker Compose reads the same `.env.production` that the container uses:

```bash
cd /Users/ferry/Documents/assessment-app
docker compose --env-file .env.production -f docker/compose.backup.yml up -d db-backup
```

Without the `--env-file` flag, `${DATABASE_URL}` remains empty during compose parsing and the backup loop fails with “No database URI found”. Alternatively, export `DATABASE_URL` in your shell before invoking `docker compose` or hard-code the DSN in the compose file.

### Automated Restore Companion

- `docker/compose.backup.yml` also defines a `db-restore` service that watches a queue directory (default `/restore/incoming`).
- When a dump file appears (`.sql`/`.sql.gz`, `.dump`/`.dump.gz`, `.db`/`.db.gz`), the service stops the containers listed in `RESTORE_STOP_CONTAINERS`, restores the configured database, and restarts those containers (plus any names in `RESTORE_START_CONTAINERS`).
- Mount both `./backups:/backups` and `./restore:/restore` when running the overlay so backups and queued restores persist.
- Provide Docker API access (`/var/run/docker.sock`) and populate the relevant environment variables in `.env.production`:
  - `RESTORE_STOP_CONTAINERS` — comma-separated container names to stop before the restore (for example `assessment-app-web-1`).
  - `RESTORE_START_CONTAINERS` — optional additional containers to start afterwards.
  - `RESTORE_WATCH_DIR`, `RESTORE_STATE_FILE`, `RESTORE_POLL_INTERVAL`, `RESTORE_STOP_TIMEOUT`, `RESTORE_STOP_WAIT_SECONDS`, `RESTORE_START_WAIT_SECONDS`, and `RESTORE_SQLITE_PATH` for advanced configuration.
- Bring the helper services online with:

  ```bash
  docker compose --env-file .env.production \
    -f docker/compose.prod.yml \
    -f docker/compose.backup.yml \
    up -d db-backup db-restore
  ```

## Secrets and Configuration

- Store secrets in environment variables or a secret manager (Vault, AWS Secrets Manager, etc.).
- Use `SECRET_KEY` rotation policies and update sessions carefully when rotating.
- Provision Microsoft Entra SAML metadata via the shared secret store so Ansible and Docker builds stay aligned. Populate the `SAML_SP_*` keys (entity ID, ACS, SLS, certificates) together with the IdP values (`SAML_IDP_*`), attribute mappings, and toggles such as `SAML_SIGN_AUTHN_REQUESTS` or `SAML_WANT_ASSERTION_SIGNED`.
- When enabling SSO, either import the generated metadata from `https://<host>/auth/login/saml/metadata` or copy the ACS/SLO URLs into the Entra enterprise application configuration.
- Leave `PASSWORD_LOGIN_ENABLED` set to `false` in production. Switch it on temporarily only for break-glass operations or automated tests that rely on the legacy email/password form.
- Configure TLS termination at the load balancer or reverse proxy layer.

## Microsoft Entra SSO Preparation

- **Enterprise application** – Create a non-gallery Entra enterprise application, switch it to SAML, and import the service provider metadata from `/auth/login/saml/metadata`.
- **Claim set** – Issue email, given name, surname, display name, object ID, UPN, and the groups claim. For large tenants enable *Groups assigned to the application* or the Microsoft Graph callout so the claim populates reliably.
- **Attribute mapping** – Align Entra claim names with the environment variables (`SAML_ATTRIBUTE_*`), choose a NameID format, and decide whether to request specific AuthN contexts (control via `SAML_REQUESTED_AUTHN_CONTEXT`).
- **Group and role gating** – Capture the object IDs for the Entra groups allowed to access the app. Add them to `SAML_ALLOWED_GROUP_IDS` and mirror role mappings in `SAML_ROLE_MAP` and the database (`Role` table).
- **Certificates and logout** – Export the IdP signing certificate and upload it via `SAML_IDP_CERT`. Provide SSO/SLO URLs and configure `SAML_LOGOUT_RETURN_URL` so the application redirects users to a friendly page once Entra completes SLO.
- **Proxy awareness** – If the app sits behind a load balancer, set `FORWARDED_ALLOW_IPS` (or the equivalent `WERKZEUG_RUNSERVER_WITH_RELOADER=0` for local testing) so `ProxyFix` trusts forwarded headers.

Refer to `docs/authentication.md` for the full end-to-end setup guide, troubleshooting matrix, and operational runbooks.

## Observability

- Consider integrating Sentry or OpenTelemetry for error/trace capture.
- Expose structured logs (JSON) to support centralised logging pipelines.

## Deployment Troubleshooting

- **SSO failures on first request** – Confirm all `SAML_*` environment variables
  are present in the runtime. Missing values surface as 500 errors when the app
  builds SAML settings.
- **Users see 403 after login** – Review the authentication logs for `Access
  denied` messages. The user either falls outside `SAML_ALLOWED_GROUP_IDS` or
  the group is not mapped in `SAML_ROLE_MAP` / the `aad_group_mappings` table.
- **`assertion consumer service not found`** – Check the externally visible URL
  matches `SAML_SP_ACS_URL`. Behind a proxy, verify `FORWARDED_ALLOW_IPS` and
  related header settings are correct so Flask reconstructs the original URL.
- **Logout loops to maintenance page** – Ensure `SAML_LOGOUT_RETURN_URL` points
  to a reachable URL and that the maintenance gateway is healthy.
- **Unexpected password login form** – Set `PASSWORD_LOGIN_ENABLED=false` after
  break-glass tests to return to SSO-only mode.

## Release Management Checklist

- Validate new migrations locally or in staging, then run `flask db upgrade`
  (or the equivalent task) before exposing the new release to users.
- Confirm environment variable changes (including `SAML_ALLOWED_GROUP_IDS`,
  `SAML_ROLE_MAP`, `SAML_REQUESTED_AUTHN_CONTEXT`, and `SAML_LOGOUT_RETURN_URL`)
  are committed to infrastructure configuration and secrets stores.
- Build and deploy the application containers or packages. For container flows,
  ensure the image tag is unique per release.
- Execute an SSO smoke test: navigate to `/auth/login`, complete the Entra
  handshake, verify role synchronisation, and perform logout to validate RelayState.
- Exercise a core business path (for example viewing `/bia/components`) to
  confirm pagination, permissions, and static assets still function.
- Monitor logs and metrics for at least one full login/logout cycle. Keep the
  previous release artefact available for quick rollback if regressions appear.
