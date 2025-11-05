# Docker Setup for Business Impact Assessment Tool

This directory contains Docker configuration files to run the BIA Tool with Docker Compose. The default stack runs SQLite inside the container, but you can target any SQL backend by setting `DATABASE_URL`.

## Quick Start

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Git (for cloning the repository)

### Development Setup (SQLite)

1. **Navigate to the docker directory:**

  ```bash
  cd docker
  ```

1. **Start the application:**

  ```bash
  docker-compose up --build
  ```

1. **Access the application:** open <http://localhost:5001> and log in with the default admin credentials from `.env.docker`.

1. **Stop the application:**

  ```bash
  docker-compose down
  ```

## Configuration Options

### Environment Variables

Create a `.env.docker.local` file in the docker directory based on `.env.docker`:

```bash
cp .env.docker .env.docker.local
```

Edit the file with your settings. Typical entries include:

```bash
# Application settings
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Admin user credentials
ADMIN_EMAIL=your-admin@example.com
ADMIN_PASSWORD=YourSecurePassword123!

# Optional: point to an external database (PostgreSQL recommended)
# DATABASE_URL=postgresql+psycopg://user:password@postgres:5432/bia_tool
```

## Deployment Scenarios

1. **Development with SQLite (default)**

  ```bash
  docker-compose up --build
  docker-compose logs -f bia-app
  ```

1. **Production deployment**

  ```bash
  cp .env.docker .env.prod
  # edit .env.prod to set secrets and DATABASE_URL
  docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
  ```

## Helper Scripts

Use the scripts in `../scripts/` for quick management:

```bash
../scripts/docker-dev.sh start
../scripts/docker-dev.sh start-bg
../scripts/docker-dev.sh stop
../scripts/docker-dev.sh logs
../scripts/docker-dev.sh clean
```

## Maintenance

- **Back up SQLite:**

  ```bash
  docker-compose exec bia-app cp /app/instance/bia_tool.db /app/backup_$(date +%Y%m%d_%H%M%S).db
  ```

- **External database backups:** use the tooling provided by your managed database (for example `pg_dump` for PostgreSQL).

## Troubleshooting

1. **Port already in use**

  ```bash
  lsof -i :5001
  ```

  Update the `ports` mapping in `docker-compose.yml` if another process uses the port.

1. **Database connection issues**

   - Verify `DATABASE_URL` credentials and network access.
   - Test the connection inside the container: `docker-compose exec bia-app python -c "from sqlalchemy import create_engine; create_engine('<dsn>').connect()"`.

1. **Permission issues**

  ```bash
  sudo chown -R $USER:$USER ../instance
  ```