# Deployment Guide

This guide outlines deployment options for the scaffold application, focusing on the PostgreSQL backend.

## Containerised Deployment (Docker Compose)

1. Build image: `docker build -t scaffold-app .`
2. Configure environment variables in `docker/.env` (copy from `.env.example`).
3. Start services: `docker compose up -d`.
4. Run migrations: `docker compose exec web poetry run flask --app scaffold:create_app db upgrade`.

The reference Compose file runs the web application alongside PostgreSQL.

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

## Secrets and Configuration

- Store secrets in environment variables or a secret manager (Vault, AWS Secrets Manager, etc.).
- Use `SECRET_KEY` rotation policies and update sessions carefully when rotating.
- Configure TLS termination at the load balancer or reverse proxy layer.

## Observability

- Consider integrating Sentry or OpenTelemetry for error/trace capture.
- Expose structured logs (JSON) to support centralised logging pipelines.

## Zero-Downtime Deployment Checklist

- Run database migrations before routing traffic to the new release.
- Warm up application instances by preloading caches or performing health checks.
- Monitor login and MFA flows closely after release.
- Keep rollback plan ready: revert to previous container image and re-run migrations if needed.
