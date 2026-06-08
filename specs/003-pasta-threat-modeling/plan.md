# Implementation Plan: PASTA Threat Modeling

**Branch**: `[003-extend-pasta-modeling]` | **Date**: 2026-06-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-pasta-threat-modeling/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Promote PASTA from the current per-scenario methodology flag into a model-level, seven-stage workflow inside the existing threat module by adding persisted PASTA stage and finding records, allowing one-way bootstrap from existing STRIDE-LM models, reusing STRIDE-LM mappings only where they fit, and letting selected PASTA findings generate or link standard threat scenarios for downstream sync and export flows.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: Flask, SQLAlchemy, Alembic, Flask-WTF, Flask-Login, Flask-Babel, Jinja2, Tailwind CSS

**Storage**: Relational database via SQLAlchemy and Alembic migrations; SQLite in development and container-managed database in deployed environments

**Testing**: pytest request/integration tests for threat routes, exports, and audit behavior with focused model/service regression coverage

**Target Platform**: Docker-deployed Flask web application on Linux server infrastructure

**Project Type**: Modular Flask web application with HTML UI, exports, audit logging, and downstream threat-to-risk synchronization

**Performance Goals**: Preserve current synchronous threat-model create/edit/export responsiveness; allow users to complete a first pass through the first four PASTA stages within the success-criteria workflow target; keep HTML/PDF/CSV review outputs readable in a single normal request cycle for ordinary threat models

**Constraints**: Keep the feature inside `scaffold/apps/threat`; preserve existing STRIDE-LM-only models; one-way bootstrap only; reuse STRIDE-LM mappings optionally instead of forcing them; maintain audit logging, translation coverage, and Tailwind/Jinja patterns; avoid a separate reporting subsystem in v1

**Scale/Scope**: One domain module (`threat`) plus shared audit/export helpers, approximately five new relational tables and targeted columns on `threat_models`, one Alembic migration, new PASTA stage/finding UI surfaces, existing export updates, and focused threat-route/export test expansion

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Module ownership is explicit: the threat module owns the PASTA workflow, while existing shared audit and PDF export helpers are reused without introducing a new domain module.
- [x] Security, authorization, audit logging, and export implications are identified: existing threat view/edit role checks remain authoritative, stage/finding changes and bootstrap actions require audit coverage, and existing export surfaces gain methodology-aware behavior.
- [x] Required validation is named, and schema change scope includes an Alembic migration plan for the new PASTA persistence tables and any new `threat_models` columns.
- [x] UI, copy, and localization impact are captured: new stage workflow labels, gating/revalidation messages, bootstrap prompts, and export terminology require translation updates and Tailwind-consistent templates.
- [x] Operational impact is documented: no new environment variables are expected, but migration/release notes, docs updates, and export behavior changes must ship with the feature.

## Project Structure

### Documentation (this feature)

```text
specs/003-pasta-threat-modeling/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── pasta-workflow-http.md
│   └── threat-exports.md
└── tasks.md
```

### Source Code (repository root)

```text
scaffold/
├── __init__.py
├── config.py
├── extensions.py
├── core/
├── apps/
│   └── threat/
│       ├── forms.py
│       ├── models.py
│       ├── routes.py
│       ├── services.py
│       ├── data/
│       └── templates/
├── templates/
└── static/

migrations/
tests/
docs/
docker/
```

**Structure Decision**: Keep the implementation inside `scaffold/apps/threat/` because the current threat model CRUD, methodology flagging, exports, risk sync, library integration, and role checks already live there. Extend `models.py` with PASTA model/stage/finding persistence, `forms.py` and `routes.py` with model-level PASTA workflow and bootstrap actions, `services.py` with stage gating/export projection helpers, and `templates/threat/` with PASTA stage/review surfaces. Use `migrations/versions/` for schema changes, `tests/test_threat_routes.py` for focused route/export/audit regression coverage, `scaffold/translations/` for copy, and `docs/history.md` plus `docs/models.md` for release-facing documentation.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Change Impact Summary

**Auth/Roles Impact**: Existing threat module access rules remain authoritative: any authenticated user may review where current routes allow review, while only admins and assessment managers may create models, bootstrap PASTA from STRIDE-LM, edit stage content, or generate/link downstream scenarios. Export access follows the existing threat review permission path and all new bootstrap or stage-edit actions remain auditable.

**Data/Migration Impact**: Add model-level PASTA persistence to the threat domain: new stage and finding tables, relational links for optional STRIDE-LM mappings and downstream threat-scenario traceability, and targeted `threat_models` metadata for methodology/bootstrap source. Existing `ThreatScenario.methodology` and `pasta_stage` fields need a compatibility decision during implementation, and the work requires one Alembic migration plus any needed bootstrap/backfill handling. That compatibility decision must be resolved before migration implementation begins.

**Localization Impact**: Add translation keys for the seven canonical PASTA stage names, gating/revalidation labels, bootstrap copy, stage/finding actions, review headings, export terminology, and any helper text that differentiates PASTA-native outputs from reused STRIDE-LM mappings.

**Operations Impact**: No new environment variables, schedulers, or backup behaviors are expected. Release work must include the Alembic migration, updated operator guidance on when to use PASTA versus STRIDE-LM bootstrap, and release notes covering methodology-aware exports and downstream scenario generation/linking.

## Phase 0 Research

- Research output: [research.md](./research.md)
- Key decisions captured: make PASTA model-level rather than scenario-level, use canonical seven-stage workflow names with explicit stage records, keep STRIDE-LM reuse optional through finding-level mappings, use one-way bootstrap from existing STRIDE-LM models, and extend current threat review/export surfaces instead of creating a separate reporting subsystem.

## Phase 1 Design

- Data model: [data-model.md](./data-model.md)
- Contracts: [contracts/pasta-workflow-http.md](./contracts/pasta-workflow-http.md), [contracts/threat-exports.md](./contracts/threat-exports.md)
- Validation quickstart: [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

- [x] Module ownership remains explicit: implementation stays in `scaffold/apps/threat/` with existing shared audit/PDF helpers reused as cross-cutting services.
- [x] Security and audit impact remain covered: threat-module role checks stay in place, bootstrap and stage/finding changes are auditable, and export behavior remains tied to existing review authorization.
- [x] Validation and migration scope are explicit: one Alembic migration plus focused pytest coverage for bootstrap, stage gating, downstream scenario linking, and methodology-aware exports.
- [x] UI and localization impact are captured: the design introduces new PASTA workflow templates/copy while keeping Tailwind/Jinja conventions and translation requirements explicit.
- [x] Operational impact remains bounded and documented: standard migration/release flow applies, no new env vars are introduced, and docs/release notes must explain the new methodology behavior.
