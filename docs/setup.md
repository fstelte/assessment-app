# Setup Guide

Follow these steps to provision a local development environment for the scaffold application.

## Prerequisites

- Python 3.11.x
- Poetry 1.6+ (`pipx install poetry` recommended)
- Node.js (optional) if you plan to rebuild Bootstrap assets
- Docker (optional) for container-based databases

## Installation

1. Clone this repository next to `bia_app` and `csa_app` or within the mono-repo.
2. Run `poetry install` to create a virtual environment and install merged dependencies.
3. Copy `.env.example` to `.env` and adjust the settings (see below).
4. Activate the environment with `poetry shell` or prefix commands with `poetry run`.

## Environment Variables

| Variable | Description | Default |
| --- | --- | --- |
| `SECRET_KEY` | Flask secret for sessions and CSRF | `change-me` |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///instance/scaffold.db` |
| `SCAFFOLD_APP_MODULES` | Comma-separated list of app modules to load | `scaffold.apps.auth.routes,scaffold.apps.admin,scaffold.apps.bia,scaffold.apps.csa,scaffold.apps.template` |
| `SESSION_COOKIE_SECURE` | Marks cookies as secure (HTTPS only) | `true` |
| `PASSWORD_LOGIN_ENABLED` | Enable the legacy email/password login form for break-glass access | `false` |

### Database URLs

- PostgreSQL: `postgresql+psycopg://user:password@localhost:5432/scaffold`
- SQLite (dev only): `sqlite:///instance/scaffold.db`

Install optional drivers using Poetry extras if you prefer managing the Postgres driver separately:

```bash
poetry install --with dev --extras "postgresql"
```

## Running the App

```bash
poetry run run
```

The helper script boots the Flask development server using the unified app factory. Set `FLASK_DEBUG=0` to disable the debugger or override host/port using `FLASK_RUN_HOST` and `FLASK_RUN_PORT`.

## Database Setup

```bash
poetry run flask --app scaffold:create_app db upgrade
```

The unified Alembic environment is already checked in, so you do **not** need to run `flask db init`. Use `poetry run flask --app scaffold:create_app db revision --autogenerate -m "<description>"` to create new migrations when model changes occur.

## Tests and Linting

```bash
poetry run lint
poetry run test
```

The `lint` script runs Ruff and Black in check mode, while `test` executes the pytest suite. CI pipelines should invoke the same commands for consistency.
