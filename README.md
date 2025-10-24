# Scaffold App

Unified scaffold that layers the existing `bia_app` and `csa_app` domains into a single Flask platform managed by Poetry. The project ships with a shared application factory, merged dependencies, and opinionated defaults so new domain apps can plug into the platform with minimal effort.

## Features

- Consolidated SQLAlchemy metadata spanning BIA and CSA domains.
- Unified authentication with MFA, role management, and session security hardening.
- Bootstrap dark-mode layout, navigation partials, and reusable components.
- Dynamic registry for discovering and wiring additional app blueprints.
- Alembic migrations, pytest suite, and lint scripts ready for CI pipelines.

## Setup Guide

1. **Install dependencies**
   - Install [Poetry](https://python-poetry.org/docs/#installation).
   - Run `poetry install` in this repository to create the virtual environment.
2. **Configure environment**
   - Copy `.env.example` to `.env` and adjust values as needed.
   - Default database points to `sqlite:///instance/scaffold.db`; override for production deployments.
   - Update `SCAFFOLD_APP_MODULES` when enabling additional domains.
3. **Initialise local database**
   - Run `poetry run flask --app scaffold:create_app db upgrade` to apply migrations.
4. **Create an administrator account**
   - Execute `poetry run flask --app scaffold:create_app create-admin` and provide the prompts.
   - Re-run the command whenever you need to rotate credentials or activate an admin.
5. **Start the development server**
   - Execute `poetry run run` to launch the Flask development server (debug mode on by default).
   - Visit `http://127.0.0.1:5000` and log in using seeded credentials.
6. **Quality checks**
   - Run `poetry run lint` for Ruff and Black in check mode.
   - Run `poetry run test` for the pytest suite.

## Deployment

- **Server process**: run `poetry run gunicorn 'scaffold:create_app()'` behind a reverse proxy such as Nginx. Set `FLASK_DEBUG=0` and terminate TLS at the proxy when `SESSION_COOKIE_SECURE=true`.
- **Configuration**: manage secrets with environment variables or a platform-specific secret store. At minimum set `SECRET_KEY`, `DATABASE_URL`, and restrict `SCAFFOLD_APP_MODULES` to the deployed domains.
- **Static assets**: Bootstrap is loaded from a CDN by default. If offline assets are required, build them and mount under `scaffold/static`.
- **Migrations**: execute `poetry run flask --app scaffold:create_app db upgrade` during deployment. Integrate with release pipelines or infrastructure hooks so migrations run before the new code serves traffic.
- **Observability**: configure logging handlers in `scaffold/config.py` or via `LOGGING_CONFIG`. Add health endpoints as lightweight blueprints registered through the module registry.

## Database Configuration

### PostgreSQL

- Install the optional dependency: `poetry install --extras postgresql`.
- Connection string example: `postgresql+psycopg://user:password@host:5432/scaffold`.
- Append `?sslmode=require` for managed services that enforce TLS.
- Grant `CREATE`, `ALTER`, and `DROP` privileges if Alembic migrations will manage schema changes.

### MariaDB

- Install the optional dependency: `poetry install --extras mariadb`.
- Connection string example: `mariadb+pymysql://user:password@host:3306/scaffold`.
- Include `charset=utf8mb4` (`.../scaffold?charset=utf8mb4`) to enable full Unicode support.
- Ensure the database user has `ALTER`, `INDEX`, and `REFERENCES` permissions for migrations.

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
