# Teststrategie

Deze applicatie gebruikt `pytest` als primaire testrunner. De strategie is opgesplitst in drie niveaus zodat regressies vroeg worden opgespoord en beveiligingscontroles aantoonbaar blijven.

## Unittests
- Locatie: `tests/` met bestandsnaam `test_*.py`.
- Dekken pure functies (zoals MFA helpers) en modelmethodes.
- Draaien standaard met `poetry run pytest`.
- Gebruik fixtures uit `tests/conftest.py` voor een in-memory SQLite database.

## Integratietests
- Maken gebruik van `FlaskClient` om routes, forms en database-interacties in samenhang te testen.
- De fixture `postgres_app` ondersteunt optioneel een Postgres-instance via `TEST_DATABASE_URL`; als de variabele ontbreekt worden de tests automatisch overgeslagen.
- Uitvoeren met `poetry run pytest tests/` of via `tox -e py311`.

## End-to-End (E2E)
- Worden uitgevoerd met een toekomstige browsergebaseerde suite (bijv. Playwright/Cypress). Placeholder opgenomen in roadmap; addendum volgt bij implementatie van UI flows.

## Hulpmiddelen
- Coverage: `pytest --cov=app --cov-report=term-missing` (geïntegreerd in CI).
- Linting en security: `ruff`, `black`, `bandit` draaien in CI en lokaal via `tox -e lint`.
- Docker Compose configuratie voor Postgres staat gepland onder `deploy/` (roadmap item) en sluit aan op `postgres_app` fixture.
