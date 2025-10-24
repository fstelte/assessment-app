# Go-Live Preparation Guide

This guide outlines the activities required before promoting the Control Self-Assessment platform to production.

## Data Seeding

- **Control Catalog:**
  ```shell
  poetry run flask --app autoapp import-controls iso_27002_controls.json
  ```
  Validate the import via the admin dashboard and spot-check control counts.
- **Assessment Templates:** Use Alembic/fixtures or manual entry to create baseline assessments needed for launch.
- **Reference Data:** Verify roles (`admin`, `user`) exist; seed any default questionnaires or scoring rubrics.

## Admin Account Initialisation

1. Create at least two admin users (primary and backup):
   ```shell
   poetry run flask --app autoapp create-admin
   ```
2. Enforce MFA enrollment for each admin via `/admin/manage_user_mfa/<user_id>`.
3. Record admin contact details and escalation paths in the runbook.

## Secrets Management

- Generate unique values for `SECRET_KEY`, database credentials, and any API keys.
- Store secrets in a secure vault (Azure Key Vault, AWS Secrets Manager, or on-prem HSM).
- Deliver secrets to the operations team through encrypted channels; avoid email or chat transcripts.
- Update deployment manifests (`docker-compose.prod.yml`, CI secrets) with vault references rather than raw values when possible.

## Backup Strategy

- Enable daily backups of the Postgres `prod-db-data` volume via managed backups or scheduled `pg_dump`.
- Store backups in a secure, access-controlled location with retention policy (minimum 30 days).
- Test restoration procedures before go-live to ensure RTO/RPO targets can be met.

## Monitoring & Logging

- **Application Logs:** Configure Docker logging drivers or ship logs to centralized logging (ELK, Azure Monitor, CloudWatch).
- **Error Reporting:** Integrate with an incident tracker (Sentry, Rollbar) by adding the DSN to environment variables and instrumenting Flask error handlers.
- **Health Checks:** Ensure `/healthz` is monitored by load balancers and alerting system.
- **Metrics:** Plan collection of request latency, error rates, and database health metrics; integrate with Prometheus/Grafana or equivalent.

## Final Verification Checklist

- [ ] Database seeded and verified.
- [ ] Admin accounts created, MFA enabled.
- [ ] Secrets provisioned via secure channel.
- [ ] Backups configured and restore test completed.
- [ ] Logging, monitoring, and alerting validated in staging.
- [ ] Rollback plan documented (container rollback or DB restore procedure).
