# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-10-18
### Added
- Architecture, API, MFA, user, and release documentation under `docs/`.
- Dockerfile and docker-compose configurations for development (SQLite) and production (Postgres).
- PowerShell management script (`scripts/manage.ps1`) for local run, tests, imports, and migrations.
- Changelog, release notes, and hand-over checklist to support project transition.
- UAT plan, go-live preparation guide, post-implementation plan, and deployment documentation updates.
- Self-assessment start flow, dashboard updates, and assessment detail placeholder.
- Admin interface for importing control catalog JSON, including quick import of the bundled ISO 27002 dataset.
- Admin user management dashboard, activation workflow, and self-service MFA entry point.
- User profile page for theme selection, password changes, and MFA shortcuts.
- Assessment assignment workflow for users with the `manager` role, plus CLI support for granting roles.

### Changed
- README now includes full setup, migration, deployment, and MFA operating guidance.
- Added PostgreSQL driver dependency (`psycopg[binary]`).

## [0.1.0] - 2025-09-30
### Added
- Initial Flask scaffold with authentication, MFA flows, ISO 27002 importer, and CI pipeline.
