# Implementation Plan: Guided PASTA Risk Analysis

**Branch**: `[004-guided-pasta-risk]` | **Date**: 2026-06-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-guided-pasta-risk/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Extend the existing model-level PASTA workflow in `scaffold/apps/threat/` so stage seven becomes a structured risk-conclusion surface that reuses the current likelihood and impact scoring scale, keeps PASTA as the source of truth, and lets threat editors explicitly publish or refresh eligible PASTA risk conclusions into the existing risk workspace without creating duplicate downstream records. Reuse the current methodology-aware HTML/PDF/CSV export surfaces and Tailwind/Jinja review patterns so guided PASTA reporting matches the rest of the application.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: Flask, SQLAlchemy, Alembic, Flask-WTF, Flask-Login, Flask-Babel, Jinja2, Tailwind CSS

**Storage**: Relational database through SQLAlchemy and Alembic migrations; existing `threat_models`, `pasta_stage_records`, `pasta_findings`, `threat_scenarios`, and `risk_items` tables remain authoritative surfaces

**Testing**: pytest request/integration tests in the existing threat and risk suites, especially `tests/test_threat_pasta_routes.py`, `tests/test_threat_pasta_exports.py`, and new focused publish/reporting coverage

**Target Platform**: Docker-deployed Flask web application on Linux server infrastructure

**Project Type**: Modular Flask web application with HTML UI, synchronous export generation, and cross-module threat-to-risk integration

**Performance Goals**: Keep stage edit, publish, and republish flows in a normal synchronous request cycle; preserve current interactive threat-model responsiveness; keep HTML/PDF/CSV output for ordinary PASTA models within the existing single-request export path

**Constraints**: Extend existing `threat` and `risk` modules rather than adding a new module; keep PASTA as the source of truth after publication; require explicit publish or republish instead of automatic sync; reuse the application's current 1-5 likelihood and impact scoring semantics and risk severity thresholds; no separate approval workflow or new reporting subsystem in v1; preserve localization, audit logging, and non-PASTA behavior

**Scale/Scope**: One feature slice spanning `scaffold/apps/threat/`, limited read/update touch points in `scaffold/apps/risk/`, one Alembic migration for new PASTA risk-conclusion persistence, existing export templates plus targeted reporting updates, and focused regression coverage across current PASTA and risk-workspace tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Module ownership is explicit and the change fits an existing domain module or a justified shared abstraction.
- [x] Security, authorization, audit logging, and export implications are identified for every affected workflow.
- [x] Required validation is named, and any schema change includes an Alembic migration plan.
- [x] UI, copy, and localization impact are captured for user-facing changes.
- [x] Operational impact is documented, including environment variables, deployment steps, backup/restore implications, and release notes updates.

## Project Structure

### Documentation (this feature)

```text
specs/004-guided-pasta-risk/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── pasta-reporting-surfaces.md
│   └── pasta-risk-publication-http.md
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
│   ├── risk/
│   │   ├── models.py
│   │   ├── routes.py
│   │   └── templates/
│   └── threat/
│       ├── forms.py
│       ├── models.py
│       ├── routes.py
│       ├── services.py
│       └── templates/
├── templates/
└── static/

migrations/
tests/
docs/
docker/
```

**Structure Decision**: Keep the workflow ownership in `scaffold/apps/threat/`, because the repo already implements model-level PASTA stages, PASTA findings, bootstrap behavior, methodology-aware exports, and threat-to-risk sync services there. Extend `models.py` with stage-seven structured risk-conclusion persistence and publication metadata, `forms.py` and `routes.py` with guided stage-seven scoring and publish/republish actions, `services.py` with score mapping and risk projection helpers, and `templates/threat/` with guided stage-seven review, publish-state, and export presentation updates. Reuse `scaffold/apps/risk/models.py` and `scaffold/apps/risk/routes.py` for the existing risk workspace projection target and display linkage, while keeping migrations in `migrations/versions/` and regression tests in the current `tests/test_threat_pasta_*.py` surface plus focused risk-workspace coverage.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Change Impact Summary

**Auth/Roles Impact**: Existing threat edit permissions remain authoritative for creating, scoring, publishing, and republishing guided PASTA conclusions. Review access remains on the current threat review path, while risk workspace consumers continue to use the risk module's existing access controls. Publication does not introduce a new elevated publish-only role.

**Data/Migration Impact**: Current PASTA stage and finding tables already exist. The change adds structured stage-seven persistence for likelihood, impact, publish metadata, and linked risk projection state, plus any required nullable linkage to existing `risk_items`. One Alembic migration is required and will backfill existing stage-seven `risk_conclusion` findings into the new structured conclusion record, preserve the legacy narrative finding as the human-readable source text, mark legacy conclusions without complete scoring as draft and unpublished, and preserve current PASTA models, existing STRIDE scenario risk sync, and existing exports.

**Localization Impact**: New translation keys are required for guided stage-seven score labels, publish and republish actions, publication gating errors, source-of-truth messaging, risk workspace linkage badges, and methodology-aware report terminology across interactive and exported views.

**Operations Impact**: No new environment variables or background services are expected. Release work must include the Alembic migration, documentation updates for the guided PASTA publish flow and report behavior, and release notes clarifying that PASTA conclusions publish explicitly into the risk workspace rather than syncing automatically.

## Phase 0 Research

- Research output: [research.md](./research.md)
- Key decisions captured: extend the current model-level PASTA implementation instead of redesigning it, represent stage-seven structured scoring through a dedicated conclusion extension rather than generic risk fields on every finding, backfill existing stage-seven `risk_conclusion` findings into that extension during migration while keeping their narrative text intact, make publication explicit and idempotent, and reuse current risk-workspace severity logic and existing reporting surfaces.

## Phase 1 Design

- Data model: [data-model.md](./data-model.md)
- Contracts: [contracts/pasta-risk-publication-http.md](./contracts/pasta-risk-publication-http.md), [contracts/pasta-reporting-surfaces.md](./contracts/pasta-reporting-surfaces.md)
- Validation quickstart: [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

- [x] Module ownership remains explicit: the threat module owns guided PASTA workflow, scoring, and publication, while the risk module remains the downstream workspace projection target.
- [x] Security and audit implications remain explicit: publication stays on existing threat edit permissions, risk projection changes are auditable, and review/export authorization remains unchanged.
- [x] Validation and migration scope are explicit: one Alembic migration plus focused pytest coverage for publish gating, republish behavior, risk-workspace linkage, and reporting surfaces.
- [x] UI and localization impact remain captured: stage-seven scoring controls, publish state, workspace linkage, and methodology-aware reporting all require Tailwind/Jinja-consistent UI and translation coverage.
- [x] Operational impact remains bounded and documented: no new env vars are introduced, but migration, release notes, and guided operator documentation are required.
