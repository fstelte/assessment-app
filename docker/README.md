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
