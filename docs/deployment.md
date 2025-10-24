# Deployment Guide

This guide outlines deployment options for the scaffold application, focusing on PostgreSQL and MariaDB backends.

## Containerised Deployment (Docker Compose)

1. Build image: `docker build -t scaffold-app .`
2. Configure environment variables in `docker/.env` (copy from `.env.example`).
3. Start services: `docker compose up -d`.
4. Run migrations: `docker compose exec web poetry run flask --app scaffold:create_app db upgrade`.

The reference Compose file defines separate services for PostgreSQL or MariaDB. Enable the database you need and disable the other.

## Kubernetes (Optional)

- Package the application with a Deployment + Service.
- Use a StatefulSet for the database (or managed service).
- Mount secrets via Kubernetes Secrets or an external secret store.
- Configure liveness/readiness probes hitting `/healthz` (to be implemented).

## PostgreSQL Notes

- Install dependencies with `poetry install --extras postgresql`.
- Recommended driver: `psycopg[binary]`. For production, consider `psycopg[c]`.
- Connection string format: `postgresql+psycopg://user:password@host:port/database`.
- Run migrations through `flask db upgrade` as usual.
- Backup strategy: `pg_dump -Fc scaffold > scaffold.dump`.
- Tune `pool_size` and `max_overflow` via `SQLALCHEMY_ENGINE_OPTIONS` if needed.

## MariaDB Notes

- Install dependencies with `poetry install --extras mariadb`.
- Driver: `pymysql`. For better performance, you can add `mysqlclient` if your environment supports compilation.
- Connection string format: `mariadb+pymysql://user:password@host:port/database`.
- Ensure the database uses `utf8mb4` character set for full Unicode support.
- When using JSON columns, prefer `LONGTEXT` with application-level serialisation if strict JSON types are not required.
- Backup strategy: `mariadb-dump scaffold > scaffold.sql`.

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
