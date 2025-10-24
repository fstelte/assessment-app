# Final Review & Hand-Over Checklist

Use this checklist during the final project transition to operations or a new development team.

## Pre-Handover Validation

- [ ] All tests pass locally (`poetry run pytest --cov=app --cov-report=term-missing`).
- [ ] Linting and security scans succeed (`tox -e lint`).
- [ ] Database migrations applied and verified against target environment.
- [ ] Admin user created and MFA enrollment tested end-to-end.
- [ ] ISO 27002 controls imported and spot-checked.
- [ ] Secrets and environment variables documented in a secure location.

## Documentation Delivered

- [ ] README updated with setup, migration, deployment, and MFA procedures.
- [ ] Architecture overview (`docs/architecture.md`).
- [ ] API routes catalog (`docs/api-routes.md`).
- [ ] MFA operations manual (`docs/mfa.md`).
- [ ] User guide (`docs/user_guide.md`).
- [ ] Release notes (`docs/release_notes.md`).
- [ ] Changelog (`CHANGELOG.md`).

## Deployment Assets

- [ ] Docker images built using `docker-compose build`.
- [ ] Production stack verified via `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up`.
- [ ] Postgres credentials stored securely and rotated.
- [ ] Backup strategy configured for `prod-db-data` volume (or cloud equivalent).

## Operational Handover

- [ ] Monitoring and alerting configured for the Flask service.
- [ ] Incident response contacts documented.
- [ ] Runbooks for routine tasks (migrations, imports, MFA resets) shared with operations.
- [ ] Access reviews completed for admin accounts.

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Owner | | | |
| Tech Lead | | | |
| Security Officer | | | |
| Operations Lead | | | |
