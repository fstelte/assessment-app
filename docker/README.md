# Docker Tooling

This directory centralises containerisation assets for the combined scaffold application.

## Images

- `Dockerfile` builds a production-ready image with Gunicorn.
- `entrypoint.sh` waits for the configured database, applies migrations, and starts the app.

Build locally:

```bash
docker build -t assessment-app -f docker/Dockerfile .
```

## Compose environments

### Development (SQLite)

```bash
cp .env.example .env  # if you have not configured it yet
docker compose -f docker/compose.dev.yml up --build
```

The service exposes <http://localhost:5000> and uses the SQLite database defined in `.env`.

### Production (PostgreSQL)

```bash
cp docker/.env.production.example .env.production
# adjust secrets inside the file
docker compose -f docker/compose.prod.yml --profile postgres up --build -d
```

The entrypoint script waits for the database container, ensures the database exists, performs `flask db upgrade`, and then launches Gunicorn.

### Operational Helpers (Backup & Restore)

- `docker/compose.backup.yml` extends the production stack with:
	- `db-backup`: creates compressed snapshots on a schedule (`BACKUP_INTERVAL_SECONDS`) and optional S3 upload.
	- `db-restore`: watches a directory for new dump files, stops the configured application containers, restores the database, and brings the services back online.
- Mount host directories so files persist outside the container lifecycle:
	- `./backups:/backups` (written by `db-backup`).
	- `./restore:/restore` (watched by `db-restore`; drop `.sql[.gz]`, `.dump[.gz]`, or `.db[.gz]` files into `/restore/incoming`).
- Control the automation with environment variables in `.env.production`:
	- `RESTORE_STOP_CONTAINERS` comma-separated list of container names to stop (for example `assessment-app-web-1`).
	- `RESTORE_START_CONTAINERS` optional list of extra containers to start after restoration (defaults to the ones that were stopped).
	- `RESTORE_WATCH_DIR`, `RESTORE_STATE_FILE`, `RESTORE_POLL_INTERVAL`, and `RESTORE_SQLITE_PATH` for fine-grained tuning.
- The restore container needs access to the Docker API to stop/start services: mount `/var/run/docker.sock` read-write into the container and ensure the names you provide exist (run `docker compose ps` to confirm).
- Start both helpers alongside the main stack once the environment variables are in place:

```bash
docker compose --env-file .env.production \
  -f docker/compose.prod.yml \
  -f docker/compose.backup.yml \
  up -d db-backup db-restore
```
