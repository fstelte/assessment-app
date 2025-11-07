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

## Observability

- Consider integrating Sentry or OpenTelemetry for error/trace capture.
- Expose structured logs (JSON) to support centralised logging pipelines.

## Zero-Downtime Deployment Checklist

- Run database migrations before routing traffic to the new release.
- Warm up application instances by preloading caches or performing health checks.
- Monitor login and MFA flows closely after release.
- Keep rollback plan ready: revert to previous container image and re-run migrations if needed.
