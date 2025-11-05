# Control Self-Assessment Web App

This project scaffolds a Flask-based self-assessment platform that can start on SQLite and migrate to PostgreSQL. The structure is modular, separating blueprints, forms, models, services, and auxiliary authentication utilities. Bootstrap 5 is assumed for styling and the code base is prepared for minimal JavaScript usage.

## Setup

1. Install Poetry: https://python-poetry.org/docs/#installation
2. Install dependencies, including development tooling:
   ```shell
   poetry install --with dev
   ```
3. Activate the virtual environment when you want an interactive shell:
   ```shell
   poetry shell
   ```
4. Copy `.env.example` to `.env` and adjust secrets, database URLs, and Flask settings before running the server.

Run ad-hoc commands by prefixing them with `poetry run` when the shell is not active.

## Project Structure

```
app/
  __init__.py
  auth/
  blueprints/
  forms/
  models/
  services/
  static/
  templates/
```

Configuration classes live in `app/config.py` and extensions are centralised in `app/extensions.py`. The application factory in `app/__init__.py` loads configuration based on `FLASK_ENV` or `APP_CONFIG`, registers extensions, and wires blueprints.

## Local Development Workflow

- Start the development server against SQLite (default):
   ```shell
   poetry run flask --app autoapp --debug run
   ```
- Run the ISO 27002 control importer:
   ```shell
   poetry run flask --app autoapp import-controls iso_27002_controls.json
   ```
- Web UI import (admin): upload of JSON-bestanden via `/admin/controls/import` of gebruik de standaard dataset knop.
- Beheer gebruikers en activeer accounts via `/admin/users`.
- Ken rollen toe via de CLI:
   ```shell
   poetry run flask --app autoapp assign-role user@example.com manager
   ```
- Execute unit tests with coverage:
   ```shell
   poetry run pytest --cov=app --cov-report=term-missing
   ```
- Windows users can use `scripts/manage.ps1` to run the same workflows via `./scripts/manage.ps1 run` or `./scripts/manage.ps1 test --Coverage`.

## Environment Configuration

The application defaults to SQLite for quick local setup. Override `DATABASE_URL` for PostgreSQL deployments. The `.env.example` file lists the expected variables.

## Database Migrations

- Bootstrap the schema:
   ```shell
   poetry run flask --app autoapp db upgrade
   ```
- Create a migration after model changes:
   ```shell
   poetry run flask --app autoapp db migrate -m "Describe change"
   ```
- Apply migrations in higher environments using the same `db upgrade` command.

Alembic configuration lives in `alembic.ini`; migration scripts reside under `migrations/`.

## Testing

- `poetry run pytest` voert de volledige suite uit.
- `poetry run pytest --cov=app --cov-report=term-missing` levert coverage details.
- `tox -e lint` combineert `ruff`, `black --check`, en `bandit`.
- `tox -e py311` installeert dependencies en draait linting en tests.
- Stel `TEST_DATABASE_URL` in om integratietests tegen Postgres te activeren; zonder deze variabele worden de betreffende tests overgeslagen. Zie `docs/test_strategy.md`.

## Continuous Integration

GitHub Actions (`.github/workflows/ci.yml`) voert bij elke push en pull request linting (`ruff`, `black`), security scanning (`bandit`) en tests met coverage uit.

## Deployment

- **Docker (development, SQLite):** `docker-compose up app` start de Flask debug server met ingebouwde SQLite opslag.
- **Docker (production, Postgres):** `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d` draait de app achter Gunicorn plus een Postgres database.
- **Handmatig:** stel `FLASK_ENV=production` en een `DATABASE_URL` in, voer `poetry run flask --app autoapp db upgrade` uit en start met `poetry run gunicorn "autoapp:create_app()"`.
- **Database seeds:** gebruik de import-command (`import-controls`) of voeg eigen Flask CLI commands toe.

Bestudeer `Dockerfile`, `docker-compose.yml`, en `docker-compose.prod.yml` voor parameters en build targets.

## MFA Operations

- Gebruikers kunnen zich registreren en optioneel MFA inschakelen; de volledige flow staat in `docs/mfa.md`.
- Admins beheren MFA via `/admin/manage_user_mfa/<user_id>` en via CLI (`poetry run flask --app autoapp create-admin`).
- Reset of rotate een secret door de admin route aan te roepen; gebruikers moeten daarna een nieuw token verifiëren.
- Gebruikers beheren hun profiel (thema, wachtwoord, MFA) via `/auth/profile` of de **Beheer & MFA** dropdown.
- Testscenario's voor MFA staan in `tests/test_auth.py` en `tests/test_admin_mfa.py`.

## Rollen & toewijzing

- Rol **admin**: volledige toegang tot gebruikersbeheer, control-import en assessment toewijzing.
- Rol **manager**: kan self-assessments toewijzen aan andere gebruikers via `/assessments/assign`.
- Gebruik `assign-role` CLI om rollen toe te kennen (zie Local Development Workflow).

## Documentatie

- `docs/architecture.md` – componentdiagram, dataflow, en toekomstige uitbreidingen.
- `docs/api-routes.md` – overzicht van publieke en geauthenticeerde routes plus autorisatie.
- `docs/mfa.md` – MFA onboarding, reset stappen, en troubleshooting.
- `docs/test_strategy.md`
- `docs/security_checklist.md`
- `docs/deployment.md`
- `docs/user_guide.md`
- `docs/release_notes.md`
- `docs/uat_plan.md`
- `docs/go_live_preparation.md`
- `docs/post_implementation_plan.md`

Toekomstige wijzigingen worden bijgehouden in `CHANGELOG.md`; voor overdracht zie `docs/hand_over_checklist.md`.
