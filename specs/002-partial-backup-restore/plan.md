# Implementation Plan: Partial Backup Restore

**Branch**: `[002-partial-backup-restore]` | **Date**: 2026-05-27 | **Spec**: `specs/002-partial-backup-restore/spec.md`

**Input**: Feature specification from `/specs/002-partial-backup-restore/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add an admin-only partial restore workflow that can inspect a backup, list available tables, enforce required restore groups for identity/auth tables, preview conflict counts, and import only the selected tables while skipping conflicting existing rows by default. The implementation should live in `scaffold/apps/admin`, reuse existing backup encryption helpers and audit facilities, and add backend-specific inspection/restore adapters for SQLite and PostgreSQL rather than relying on the current full-restore watcher.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: Flask, SQLAlchemy, Flask-WTF, flask-login, cryptography, Jinja2, pytest

**Storage**: SQLite and PostgreSQL application databases; gzip and optional Fernet-encrypted backup files; temporary inspection/preview metadata in filesystem-backed temp artifacts; existing `AuditLog` for event history

**Testing**: pytest using Flask `client`, app-context database fixtures, and targeted admin route/service tests

**Target Platform**: Dockerized Linux deployment running the Flask app plus backup/restore sidecar tooling

**Project Type**: Modular Flask web application with admin UI and companion restore tooling

**Performance Goals**: Inspect the approved timed validation fixtures for SQLite `.db.gz` and PostgreSQL `.sql.gz` backups, each exposing 10 to 20 restorable tables and a valid 3-table non-identity selection, within the 5-minute admin workflow target from the spec. Larger or future backup variants remain operationally valid but outside the v1 timed target until explicitly added.

**Constraints**: Support both SQLite and PostgreSQL backups; admin-only with fresh-login protection; `user` must be restored only with its identity/auth group; skip conflicting rows by default; preserve untouched tables; no row-level diff UI in v1; production behavior must remain Docker- and env-driven

**Scale/Scope**: One admin-driven restore at a time, dozens of selectable tables per backup, one multi-step partial-restore workflow under the admin backup area, and focused tests/docs for the admin restore slice

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Module ownership is explicit and the change fits an existing domain module
  or a justified shared abstraction.
- [x] Security, authorization, audit logging, and export implications are
  identified for every affected workflow.
- [x] Required validation is named, and any schema change includes an Alembic
  migration plan.
- [x] UI, copy, and localization impact are captured for user-facing changes.
- [x] Operational impact is documented, including environment variables,
  deployment steps, backup/restore implications, and release notes updates.

Status before Phase 0 research:

- [x] Module ownership is explicit: admin routes/forms/templates own the workflow; shared backup parsing helpers belong in `scaffold/apps/admin/backup_utils.py`; no new cross-domain abstraction is justified yet.
- [x] Security, authorization, and audit implications are identified: admin-only access, fresh-login requirement, sensitive identity-table warnings, and audit events for inspect/preview/execute/results.
- [x] Validation and migration scope are named: focused pytest coverage for admin routes and restore helpers; no Alembic migration is planned because preview/run state remains ephemeral and audit uses the existing model.
- [x] UI and localization impact are captured: new admin partial-restore pages, warnings, preview/result copy, and translation keys in `en.json` and `nl.json`.
- [x] Operational impact is documented: existing backup env vars stay authoritative, restore behavior changes need deployment/runbook updates, and the full-restore watcher remains the fallback path for unsupported backups.

## Project Structure

### Documentation (this feature)

```text
specs/002-partial-backup-restore/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── partial-restore-http.md
└── tasks.md
```

### Source Code (repository root)

```text
scaffold/
├── config.py
├── core/
│   └── audit.py
├── apps/
│   ├── admin/
│   │   ├── backup_crypto.py
│   │   ├── backup_utils.py
│   │   ├── forms.py
│   │   ├── routes.py
│   │   └── templates/admin/
│   ├── identity/
│   │   └── models.py
│   └── scim/
│       └── models.py
├── translations/
└── templates/

docker/
└── restore/
  └── restore_db.py

tests/
└── test_admin_routes.py

docs/
├── backup_encryption_plan.md
└── deployment.md
```

**Structure Decision**: Keep all user-facing partial-restore workflow code in `scaffold/apps/admin` because the current backup UI, restore upload form, encryption handling, and admin authorization already live there. Extend `backup_utils.py` with backend-specific inspection and partial-import helpers, add new partial-restore routes/forms/templates under admin, reuse `scaffold/core/audit.py` for audit events, and update `docker/restore/restore_db.py` only if full-restore fallback behavior needs clearer separation. No new persistent domain module is required.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|


## Change Impact Summary

**Auth/Roles Impact**: Reuse the existing `admin` role and `require_fresh_login()` gate for inspection, preview, and execution. No new roles are introduced. Sensitive table selection adds stronger warnings, but not broader access.

**Data/Migration Impact**: No new persistent application tables are planned in v1. The feature adds temporary inspection/preview state outside the main database and uses the existing `AuditLog` model for history. The implementation must include expiry, revalidation, cleanup, and single-run protection for that ephemeral state. No Alembic migration or backfill is expected unless implementation later proves a persistent restore-run model is necessary.

**Localization Impact**: Add English and Dutch translation keys for partial-restore titles, step labels, selection helpers, backend-specific parse/decryption failures, identity-group warnings, dependency and schema-mismatch messages, conflict summaries, row-count estimate labels, success/error flashes, and results terminology.

**Operations Impact**: Continue using `BACKUP_DIR`, `BACKUP_ENCRYPTION_KEY`, and `RESTORE_WATCH_DIR`. Document the exact partial-restore-eligible backup variants, that unsupported or uninspectable backups still require full restore, that eligibility is coupled to current backup-generation behavior, how partial restore behaves for SQLite vs PostgreSQL, how preview state expires and is cleaned up, how single-run protection works, and how schema mismatches or no-key tables are blocked. Update restore runbooks plus release notes to cover identity-group selection, skip-existing conflict behavior, repeat-run expectations, and post-restore verification.

## Post-Design Constitution Check

- [x] Module ownership remains explicit and limited to existing admin/identity/shared audit surfaces.
- [x] Security and audit behavior remain central to the design: no broader permissions, explicit warnings for identity data, and auditable restore lifecycle events.
- [x] Validation remains focused and automatable with pytest; no schema migration is required by the current design.
- [x] User-facing workflow changes remain within Tailwind/Jinja patterns and require localization updates.
- [x] Operational impact is documented alongside the technical design, including fallback to full restore and backend-specific restore behavior.

