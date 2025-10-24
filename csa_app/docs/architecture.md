# Architecture Overview

## System Context

The Control Self-Assessment platform is a Flask 3 application backed by SQLAlchemy ORM and Alembic migrations. The web tier exposes HTML templates rendered through Jinja2, while background operations (imports, administration) are exposed via Flask CLI commands. The application is designed to start on SQLite for local development and scale to PostgreSQL in production.

## Core Components

- **Application Factory (`app/__init__.py`)**: Creates the Flask app, loads configuration objects, registers extensions, and wires blueprints.
- **Extensions (`app/extensions.py`)**: Centralises SQLAlchemy, Migrate, LoginManager, CSRF, and security headers via Talisman.
- **Blueprints (`app/blueprints/`)**:
  - `auth`: Registration, login, MFA flows.
  - `admin`: Administrative dashboards such as MFA management.
  - `assessments`: CRUD endpoints for assessments, assignments, and responses (assignment workflow live; detailed CRUD roadmap).
- **Models (`app/models/`)**: SQLAlchemy ORM models with UTC-aware timestamp mixins and relationship helpers.
- **Services (`app/services/`)**: Long-running or reusable workflows such as the ISO 27002 control importer.
- **Forms (`app/forms/`)**: Flask-WTF forms handling validation and CSRF protection.
- **Templates (`app/templates/`)**: Bootstrap 5 based UI components, with shared macros and layout hierarchy.
- **CLI (`autoapp.py`)**: Entry point for `flask --app autoapp` commands, including admin bootstrapper and data import logic.

## Data Flow

1. Requests enter via Flask blueprints; per-request sessions are managed by SQLAlchemy.
2. Authentication uses Flask-Login with session-backed cookies; MFA tokens are validated via `pyotp.TOTP`.
3. Business actions persist changes using UTC-aware `created_at`/`updated_at` fields provided by `TimestampMixin`.
4. Background imports read JSON control definitions and persist them through the ORM, producing an `ImportStats` summary.
5. Tests leverage an in-memory SQLite database (or Postgres via `TEST_DATABASE_URL`) using pytest fixtures to simulate flows end to end.

## Deployment Topology

- **Development**: Single container or local Poetry environment using SQLite. Live reload enabled through Flask debug mode.
- **Staging/Production**: Flask app served by Gunicorn behind a reverse proxy, backed by PostgreSQL. Static assets may be offloaded to a CDN if required.
- **Security**: Talisman enforces HTTPS and security headers; CSRF protection is enabled via Flask-WTF.

## Configuration Model

Configuration classes derive from `BaseConfig` and can be selected via `APP_CONFIG` or `FLASK_ENV`. Sensitive values (database URLs, secrets, MFA seeds) are injected through environment variables or the `.env` file in development.

## Observability & Tooling

- Logging uses Flask's standard logging; hooks exist in the application factory for future structured logging.
- CI pipeline (GitHub Actions) runs linting, tests, security scans, and uploads coverage reports.
- Future metrics hooks can be added via a WSGI middleware or Blueprints to expose Prometheus-compatible endpoints.

## Roadmap Considerations

- Extract assessment workflows into dedicated blueprint once UI is stabilised.
- Add asynchronous task queue (e.g., Celery) if control imports become long-running.
- Extend the importer to validate against external schemas for regulatory frameworks beyond ISO 27002.
- Introduce role-based access control management UI once additional roles emerge from requirements.
- Expand manager tooling with bulk assignment and due-date reminders.
