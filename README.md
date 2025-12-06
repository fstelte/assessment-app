# Scaffold App

Unified scaffold that layers the existing `bia_app` and `csa_app` domains into a single Flask platform managed by Poetry. The project ships with a shared application factory, merged dependencies, and opinionated defaults so new domain apps can plug into the platform with minimal effort.

## Features

- Consolidated SQLAlchemy metadata spanning BIA and CSA domains.
- Unified authentication with MFA, role management, and session security hardening.
- SAML single sign-on via Microsoft Entra ID (Azure AD) with automatic user provisioning and group gates.
- Bootstrap dark-mode layout, navigation partials, and reusable components.
- Accessible, CSS-only form tooltips via a shared macro and `tooltip-wrapper` utility classes.
- BIA component workflows capture environment-specific authentication methods, surface them in the UI, and provide exportable CSV/SQL payloads for audit teams.
- Risk assessment workspace with dashboard cards, CSA-linked mitigation plans, and configurable severity thresholds.
- DPIA / FRIA module linked to BIA components with editable risk registers, mitigating measures, colored risk severity badges, and a four-state workflow (in progress, in review, finished, abandoned).
- Dynamic registry for discovering and wiring additional app blueprints.
- Alembic migrations, pytest suite, and lint scripts ready for CI pipelines.

## Recent DPIA Enhancements

- Risk register rows now include likelihood/impact badges that reuse the BIA color palette.
- Users can edit or delete risks and mitigating measures inline via modal forms.
- Assessment details include a status selector with colored badges (blue, amber, green, black) that track progress through "In progress", "In review", "Finished", and "Abandoned" states.

## Risk Assessment Workspace

- `/risk` exposes a dashboard for administrators and assessment managers showing weighted scores, severity pills, treatment owners, CSA control summaries, and component coverage across every recorded risk.
- `/risk/new` and `/risk/<id>/edit` reuse the shared `RiskForm`, provide chance/impact selectors, and enforce at least one CSA control selection whenever "Mitigate" is chosen.
- `/admin/risk-thresholds` lets administrators tune the severity matrix via guarded forms that prevent overlapping ranges.
- `/api/risks` keeps automation in sync with the UI, returning the same serialized payloads (score, severity, linked components, and CSA control metadata).
- See `docs/risk.md` for prerequisites, best practices when selecting CSA controls, and a troubleshooting checklist.

## Setup Guide

1. **Install dependencies**
   - Install [Poetry](https://python-poetry.org/docs/#installation).
   - Run `poetry install` in this repository to create the virtual environment.
2. **Configure environment**
   - Copy `.env.example` to `.env` and adjust values as needed.
   - Default database points to `sqlite:///instance/scaffold.db`; override for production deployments.
   - Update `SCAFFOLD_APP_MODULES` when enabling additional domains.
   - Capture Microsoft Entra ID SAML metadata once the enterprise application is created. Populate `SAML_SP_ENTITY_ID`, `SAML_SP_ACS_URL`, and `SAML_SP_SLS_URL` for the service provider; store signing material in `SAML_SP_CERT` and `SAML_SP_PRIVATE_KEY` when requests or responses must be signed.
   - Configure the identity provider section with `SAML_IDP_ENTITY_ID`, `SAML_IDP_SSO_URL`, `SAML_IDP_SLO_URL`, and `SAML_IDP_CERT`. Optional toggles include `SAML_SIGN_AUTHN_REQUESTS`, `SAML_SIGN_LOGOUT_REQUESTS`, `SAML_SIGN_LOGOUT_RESPONSES`, `SAML_WANT_MESSAGE_SIGNED`, and `SAML_WANT_ASSERTION_SIGNED`.
   - Map directory attributes via `SAML_ATTRIBUTE_EMAIL`, `SAML_ATTRIBUTE_FIRST_NAME`, `SAML_ATTRIBUTE_LAST_NAME`, `SAML_ATTRIBUTE_DISPLAY_NAME`, `SAML_ATTRIBUTE_OBJECT_ID`, `SAML_ATTRIBUTE_UPN`, and `SAML_ATTRIBUTE_GROUPS`. Restrict access with `SAML_ALLOWED_GROUP_IDS` (comma-separated) and align application roles with `SAML_ROLE_MAP` (JSON mapping of group IDs to role names).
   - Configure structured audit logging by pointing `AUDIT_LOG_PATH` to a writable directory (defaults to `<BACKUP_DIR>/logs/audit.log`) and tuning `AUDIT_LOG_RETENTION_DAYS`/`AUDIT_LOG_PRUNE_INTERVAL_HOURS`. Set `AUDIT_LOG_MODEL_EVENTS` to a JSON mapping when you want to extend the automatic ORM listeners beyond the defaults—the parser now accepts either Flask's JSON loader or standard JSON, reducing startup warnings in containerised environments.
   - For break-glass access or automated tests you can expose the legacy password form by setting `PASSWORD_LOGIN_ENABLED=true` (aliases `SAML_PASSWORD_LOGIN_ENABLED`, `ENTRA_PASSWORD_LOGIN_ENABLED`, and `AZURE_PASSWORD_LOGIN_ENABLED` remain recognised).
3. **Initialise local database**
   - Run `poetry run flask --app scaffold:create_app db upgrade` to apply migrations.
4. **Create an administrator account**
   - Run the interactive helper: `poetry run flask --app scaffold:create_app create-admin`.
   - Supply an email address and password when prompted; the command will either create the admin user or reset the credentials if the account already exists.
   - Pass command-line flags (for example `--email foo@example.com`) to skip prompts when scripting the setup.
   - Re-run the command whenever you need to rotate credentials, activate a suspended admin, or seed an additional administrator.
5. **Start the development server**
   - Execute `poetry run run` to launch the Flask development server (debug mode on by default).
   - Visit `http://127.0.0.1:5000` and log in using seeded credentials.
6. **Quality checks**
   - Run `poetry run lint` for Ruff and Black in check mode.
   - Run `poetry run test` for the pytest suite.

Detailed SSO setup steps, troubleshooting tips, and operational runbooks live in
`docs/authentication.md`. Deployment-specific guidance (including release
checklists) is captured in `docs/deployment.md`.

## Internationalisation

The platform offers lightweight JSON-driven localisation that allows text to be translated without duplicating templates.

- **Translation files** live under `scaffold/translations/<locale>.json`. The default locale is `en`; add additional locales by dropping a new JSON file beside it. Nested keys mirror their usage in code, for example:

  ```json
  {
    "app": {
      "title": "Assessment Platform"
    }
  }
  ```

- **Lookup helper**: use the `_()` function in templates (`{{ _('app.title') }}`) and the `gettext` helper in Python modules (`from scaffold.core.i18n import gettext as _`). Placeholders follow Python `str.format` semantics (`"Welcome {name}"`).

- **Active locale detection** happens per request: a `lang=<locale>` query parameter overrides the session preference which is stored under the key reported by `session_storage_key()`. The selected locale is exposed to templates via the `current_locale` variable along with `available_locales` for building selectors.

- **Extending translations**: when adding new UI copy, prefer wrapping strings with `_()` and creating matching entries in each locale JSON file. Missing keys gracefully fall back to the default locale, and unresolved keys render the original identifier to aid debugging.

- **Reloading**: translation files are read when the app starts. Reload the server after editing JSON files or call `TranslationManager.reload()` if hot-swapping translations programmatically.

## Deployment

- **Server process**: run `poetry run gunicorn 'scaffold:create_app()'` behind a reverse proxy such as Nginx. Set `FLASK_DEBUG=0` and terminate TLS at the proxy when `SESSION_COOKIE_SECURE=true`.
- **Configuration**: manage secrets with environment variables or a platform-specific secret store. At minimum set `SECRET_KEY`, `DATABASE_URL`, and restrict `SCAFFOLD_APP_MODULES` to the deployed domains.
- **Static assets**: Bootstrap is loaded from a CDN by default. If offline assets are required, build them and mount under `scaffold/static`.
- **Migrations**: execute `poetry run flask --app scaffold:create_app db upgrade` during deployment. Integrate with release pipelines or infrastructure hooks so migrations run before the new code serves traffic.
- **Observability**: configure logging handlers in `scaffold/config.py` or via `LOGGING_CONFIG`. Add health endpoints as lightweight blueprints registered through the module registry.

## Operations & SSO

- `docs/authentication.md` walks through Microsoft Entra configuration, maps
   environment variables, and documents runbooks for certificate rotation, new
   group enablement, and break-glass access.
- `docs/deployment.md` covers infrastructure touchpoints, backup helpers, and a
   release management checklist with SSO smoke-test reminders.
- Use `poetry run flask --app scaffold:create_app audit-retention` to perform an immediate cleanup of stale audit rows and rotated log files (handy for scripted maintenance windows); the web process also prunes the data on a schedule based on `AUDIT_LOG_PRUNE_INTERVAL_HOURS`. The same helper now tracks removed rows/files in the logs for easier monitoring.

## License

Licensed under the Apache License, Version 2.0. Include the copyright notice
for Ferry Stelte in redistributions; see the `LICENSE` file for details.

### Docker

- Build the production image via `docker build -t assessment-app -f docker/Dockerfile .`.
- Development stack (SQLite): `docker compose -f docker/compose.dev.yml up --build` after copying `.env.example` to `.env`.
- Production stack: copy `docker/.env.production.example` to `.env.production` and run `docker compose --env-file .env.production -f docker/compose.prod.yml --profile postgres up --build -d`.
- The container entrypoint waits for the configured database, ensures it exists, applies `flask db upgrade`, then starts Gunicorn.
- To create the first administrator inside the running container, execute `docker compose -f docker/compose.prod.yml --profile postgres exec web flask --app scaffold:create_app create-admin`.
- A lightweight `gateway` service (Nginx) now terminates client traffic on port 8000, proxies to the `web` container, and serves a dedicated maintenance page whenever the app is starting or the database is unreachable. Customise the markup via `docker/templates/maintenance.html.tmpl`, and tune the contact details with `MAINTENANCE_CONTACT_EMAIL`, `MAINTENANCE_CONTACT_LABEL`, and `MAINTENANCE_CONTACT_LINK` in `.env.production`.

### Ansible Pipeline

- The `ansible/` directory contains a CI-friendly playbook (`playbooks/deploy.yml`). Toggle `deployment_mode` between `default` and `docker` to switch strategies.
- Global defaults live in `ansible/group_vars/all.yml`; override secrets and `app_database_url` per inventory.
- Run `ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/deploy.yml --check` for a dry run.
- Docker deployments rely on the `community.docker` collection and the provided Compose file; default deployments install the app into a Python virtualenv and configure a `systemd` unit.

## Database Configuration

### PostgreSQL Restore

- `psycopg[binary]` is installed by default via Poetry and provides the required driver.
- Connection string example: `postgresql+psycopg://user:password@host:5432/scaffold`.
- Append `?sslmode=require` for managed services that enforce TLS.
- Grant `CREATE`, `ALTER`, and `DROP` privileges if Alembic migrations will manage schema changes.

### Migration Workflow

1. Update models in `scaffold/apps/<domain>/models.py`.
2. Generate a revision with `poetry run flask --app scaffold:create_app db revision --autogenerate -m "Describe change"`.
3. Review the new file under `migrations/versions/` and adjust as needed.
4. Apply using `poetry run flask --app scaffold:create_app db upgrade`.

## Integrating Additional Apps

1. **Create a module**
   - Use `scaffold/apps/template` as a foundation. Copy the package, rename it, and update imports.
   - Implement `register(app: Flask)` or expose a `blueprints` iterable so the registry can attach routes.
2. **Expose navigation**
   - Define a `NAVIGATION` list (see `scaffold/apps/template/__init__.py`) so menu links render automatically.
3. **Add configuration**
   - Read required settings from environment variables or add defaults in `scaffold/config.py`.
4. **Register the module**
   - Append the dotted path (for example `scaffold.apps.reports`) to `SCAFFOLD_APP_MODULES` in your `.env` file or deployment configuration.
   - Restart the application; the registry will discover and register the blueprint.
5. **Validate the integration**
   - Extend the test suite under `tests/` for new routes, models, and forms.
   - Run `poetry run test` before shipping changes.

The `docs/` directory contains deeper dives into architecture, security, and operational playbooks. Use this README as the primary entry point for provisioning environments, deploying updates, and extending the platform with additional domain apps.

## Backups

We provide a small backup service that creates compressed backups of the application's database and stores them outside of Docker volumes (host mount). Features:

- Supports SQLite and PostgreSQL (uses `pg_dump`) and creates gzipped backups.
- Retention: backups older than 2 days are removed automatically (configurable via `BACKUP_RETENTION_DAYS`).
- Optional offsite upload to S3 using `AWS_S3_BUCKET` / AWS credentials.
- Health and monitoring: a lightweight HTTP status endpoint is available on port 9090 and a Docker healthcheck validates the most recent backup timestamp.

Files added in `docker/`:

- `backup-db.sh` — main backup script (creates backups, retention, optional S3 upload).
- `s3_upload.py` — optional S3 uploader used by the backup script.
- `serve-status.py` — small HTTP server exposing `/status` for monitoring.
- `healthcheck.sh` — script used by the Dockerfile to report container health.
- `backup/Dockerfile` and `backup/entrypoint.sh` — image and entrypoint for the backup container.
- `compose.backup.yml` — example compose snippet for running the backup service.

Quick start (one-off backup):

```powershell
docker run --rm -v C:\path\to\backups:/backups -e SQLALCHEMY_DATABASE_URI="sqlite:///instance/scaffold.db" assessment-app /app/docker/backup-db.sh
```

Run the backup container via Compose (recommended):

1. Add or merge `docker/compose.backup.yml` into your `docker-compose.yml` or include it when starting compose.
2. Ensure you mount a host path to `./backups` (or change the volume target) so backups live outside Docker-managed volumes.
3. Configure environment variables as needed: `DATABASE_URL`, `BACKUP_RETENTION_DAYS`, `BACKUP_INTERVAL_SECONDS`, `AWS_S3_BUCKET`, etc.

Example Compose service (already available in `docker/compose.backup.yml`):

```yaml
services:
  db-backup:
    build:
      context: ..
      dockerfile: docker/backup/Dockerfile
      image: assessment-app-db-backup:latest
      environment:
         - DATABASE_URL=${DATABASE_URL}
         - BACKUP_RETENTION_DAYS=2
         - BACKUP_INTERVAL_SECONDS=86400
         - AWS_S3_BUCKET=${AWS_S3_BUCKET:-}
      volumes:
         - ./backups:/backups
      restart: unless-stopped
      ports:
         - "9090:9090"
```

Start the application and the backup service together using the following command:

```bash
docker compose -f docker/compose.prod.yml -f docker/compose.backup.yml --profile postgres up --build --force-recreate
```

If you use `${DATABASE_URL}` placeholders in `compose.backup.yml`, make sure Docker Compose reads your production environment file during startup:

```bash
docker compose --env-file .env.production -f docker/compose.backup.yml up -d db-backup
```

Without the `--env-file` flag (or exporting `DATABASE_URL` in your shell), the backup container starts but fails with “No database URI found”. You can also hard-code the DSN in the compose file if you prefer.

Notes:

- For Postgres backups the container must be able to reach the database host and credentials must be valid.
- For consistent SQLite backups consider briefly stopping the app or scheduling backups during low traffic.
- S3 upload requires `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (or an attached IAM role in your platform).

### Automated Restore Service

- The same compose overlay also ships a `db-restore` service. It polls a configurable directory (default `/restore/incoming`) for new files with extensions `.sql[.gz]`, `.dump[.gz]`, or `.db[.gz]`.
- When a file appears, the service stops the containers listed in `RESTORE_STOP_CONTAINERS`, restores the database from the dump, and restarts the containers (plus any entries in `RESTORE_START_CONTAINERS`).
- Provide the same `.env.production` file it uses for backups so the service can read `DATABASE_URL`. Configure extra behaviour via:
  - `RESTORE_STOP_CONTAINERS` — comma-separated container names (for example `assessment-app-web-1`).
  - `RESTORE_START_CONTAINERS` — optional extra containers to start after the restore.
  - `RESTORE_WATCH_DIR`, `RESTORE_STATE_FILE`, `RESTORE_POLL_INTERVAL`, `RESTORE_STOP_TIMEOUT`, `RESTORE_STOP_WAIT_SECONDS`, `RESTORE_START_WAIT_SECONDS`, and `RESTORE_SQLITE_PATH` for advanced tuning.
- Mount host directories when running the compose overlay so backups and queued restore files persist:
  - `./backups:/backups`
  - `./restore:/restore`
- The container needs to control the Docker engine; mount `/var/run/docker.sock` and ensure the container names in `RESTORE_STOP_CONTAINERS` match `docker compose ps` output.
Start both helpers alongside production once configured:

```bash
docker compose --env-file .env.production \
   -f docker/compose.prod.yml \
   -f docker/compose.backup.yml \
   up -d db-backup db-restore
```

## Restore Procedures

When you need to roll back to a backup created by `backup-db.sh`, make a fresh snapshot of the current state first, then follow the workflow for your database engine.

### PostgreSQL

1. Stop the web container or place the app in maintenance mode to prevent writes during the restore.
2. Choose the backup file (default naming: `pg_dump-YYYYMMDDTHHMMSSZ.sql.gz`).
3. Run the restore command from the project root, adjusting credentials if you changed the defaults:

    ```powershell
    gunzip -c docker/backups/pg_dump-20250101T020000Z.sql.gz |
       docker compose -f docker/compose.prod.yml exec -T postgres \
       psql -U scaffold -d scaffold
    ```

    If you want a clean schema, drop and recreate it before piping the dump:

    ```powershell
    docker compose -f docker/compose.prod.yml exec postgres \
       psql -U scaffold -d scaffold -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    ```

4. Restart the web container and confirm the application works. Re-run migrations (`flask db upgrade`) when restoring an older dump that predates your current schema version.

### SQLite Restore

1. Stop the application container.
2. If the file is compressed (suffix `.gz`), unzip it: `gunzip sqlite-20250101T020000Z.db.gz`.
3. Replace the live database file:

    ```powershell
    Copy-Item docker/backups/sqlite-20250101T020000Z.db instance/scaffold.db -Force
    ```

4. Restart the web container and run migrations if the restored file is behind the current schema.

### Restoring From S3

Backups synced to S3 follow the same naming scheme. Download the target object to `docker/backups/` (or any directory) and apply the PostgreSQL or SQLite steps above.

Always verify the restored environment by logging in and exercising critical flows before returning the system to normal operation.

