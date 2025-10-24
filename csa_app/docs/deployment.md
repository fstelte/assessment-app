# Deployment Guide

This guide explains how to run the Control Self-Assessment application in different environments using the provided Docker assets.

## Prerequisites

- Docker Engine 24+
- Docker Compose V2 (`docker compose` or `docker-compose`)
- Access to environment secrets (see `.env.example` for required values).

## Development (SQLite)

1. Copy `.env.example` to `.env` and adjust variables as needed.
2. Build and start the container:
   ```shell
   docker-compose up --build
   ```
3. The Flask dev server listens on `http://localhost:5000`. Autosave and reload work because the project directory is mounted as a volume.
4. Database data persists in the named volume `dev-instance`.

### Common Tasks

- Run tests inside the container:
  ```shell
  docker-compose run --rm app poetry run pytest
  ```
- Apply migrations:
  ```shell
  docker-compose run --rm app poetry run flask --app autoapp db upgrade
  ```
- Tail logs:
  ```shell
  docker-compose logs -f app
  ```

## Production (Postgres)

1. Export required secrets:
   ```shell
   export SECRET_KEY="<generate secure value>"
   export POSTGRES_PASSWORD="<secure password>"
   ```
2. Build and launch the production stack:
   ```shell
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
   ```
3. Run migrations once services are healthy:
   ```shell
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml run --rm app poetry run flask --app autoapp db upgrade
   ```
4. Access the application at `http://localhost:5000`. Gunicorn serves the app with four workers by default.

### Data Management

- PostgreSQL data lives in the `prod-db-data` volume. Configure backups or map to a cloud storage solution for production.
- To inspect the database, run:
  ```shell
  docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec db psql -U csa -d csa
  ```

## Image Publishing (Optional)

1. Build a release image:
   ```shell
   docker build --build-arg INSTALL_DEV=false -t ghcr.io/<org>/csa:0.2.0 .
   ```
2. Push the image to the registry of choice.
3. Update deployment manifests (Kubernetes, ECS, etc.) to reference the new tag.

## Health & Monitoring

- The `/healthz` route returns `200 OK` when the app is ready.
- Add reverse proxy (nginx, Traefik) or cloud load balancer in front of the container for TLS termination.
- Configure observability hooks (Prometheus, OpenTelemetry) using middleware as described in `docs/architecture.md` roadmap.
