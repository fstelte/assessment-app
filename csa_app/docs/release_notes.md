# Release Notes

## Version 0.2.0 (2025-10-18)

### Highlights
- Comprehensive documentation set covering architecture, API routes, MFA operations, and user guidance.
- Containerised workflows for both development (SQLite) and production (Postgres) environments.
- Streamlined local developer experience via `scripts/manage.ps1`.

### Upgrade Notes
- Run `poetry install --with dev` to pull the new PostgreSQL driver dependency (`psycopg[binary]`).
- Review `docker-compose.prod.yml` for new environment variables (notably `POSTGRES_PASSWORD`).
- Regenerate `.env` values to include any missing configuration referenced in the new docs.

### Known Issues
- Assessment CRUD routes remain placeholders pending UI wireframes.
- MFA audit logging roadmap items are documented but not yet implemented.

## Version 0.1.0 (2025-09-30)

Initial release providing Flask scaffold, MFA-enabled authentication, ISO 27002 control importer, migrations, and CI tooling.
