# Implementation Plan: Threat Model and Risk Updates

**Branch**: `[001-run-feature-hook]` | **Date**: 2026-05-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-threat-risk-update/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Implement plural threat-scenario assignments and plural risk ticket tracking by replacing the threat module's single `asset_id` and single `stride_category` fields with relationship-backed collections, replacing the risk module's single `ticket_url` field with ordered labeled links, and preserving existing records through one migration/backfill pass plus compatibility aliases in exports and the risk API.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11

**Primary Dependencies**: Flask, SQLAlchemy, Alembic, Flask-WTF, Flask-Login, Flask-Babel, Jinja2, Tailwind CSS

**Storage**: Relational database via SQLAlchemy and Alembic migrations; SQLite in development

**Testing**: pytest request/integration tests plus focused model/service regression coverage

**Target Platform**: Docker-deployed Flask web application on Linux server infrastructure

**Project Type**: Modular Flask web application with HTML UI, exports, and a small REST API surface

**Performance Goals**: Preserve current synchronous create/edit flows and export generation without introducing noticeable latency for ordinary threat models and risk records; keep summary/detail review of multi-assigned scenarios readable in one page load

**Constraints**: Backward-compatible migration/backfill for existing single-value records; maintain audit logging and translation coverage; do not break non-STRIDE methodologies; do not introduce Bootstrap into new UI work; preserve current risk API consumers through compatibility aliases during transition

**Scale/Scope**: Two domain modules (`threat`, `risk`), three new relational tables, one combined Alembic migration, one REST API contract update, threat CSV/HTML/PDF display changes, and targeted updates to threat/risk route and template test coverage

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

## Project Structure

### Documentation (this feature)

```text
specs/001-threat-risk-update/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
scaffold/
├── __init__.py
├── config.py
├── extensions.py
├── core/
├── apps/
│   └── <domain>/
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

**Structure Decision**: Keep all business logic inside the existing owning domains: `scaffold/apps/threat/` for scenario asset/category changes and exports, `scaffold/apps/risk/` for ticket-link storage and API changes, `migrations/versions/` for schema evolution, `tests/` for focused regression coverage, `docs/` for user-facing or release-facing notes if contract changes need documentation, and `scaffold/translations/` for new copy.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations are currently expected.

## Change Impact Summary

**Auth/Roles Impact**: Threat and risk edit flows continue to affect authenticated assessment users; touched routes should preserve or tighten explicit admin/assessment-manager checks where current access is only login-gated, and all new assignment/ticket-link changes remain auditable.

**Data/Migration Impact**: Add `threat_scenario_assets`, `threat_scenario_stride_categories`, and `risk_ticket_links`; backfill from existing `threat_scenarios.asset_id`, `threat_scenarios.stride_category`, and `risk_items.ticket_url`; then remove or deprecate the scalar columns in application usage as part of one Alembic migration.

**Localization Impact**: New labels, help text, validation errors, table headings, badge text, and ticket-link row copy are required for threat scenario forms, risk forms, summaries, and exports.

**Operations Impact**: Standard deployment migration flow only; no new env vars or schedulers are expected, but release notes should call out the schema migration, deprecated compatibility fields, and any export/API format adjustments.

## Phase 0 Research

- Research output: [research.md](./research.md)
- Key decisions captured: multi-asset and multi-category threat relationships use association tables; risk ticket links use an ordered child table with label and URL; non-STRIDE methodologies remain supported while multi-category behavior applies to STRIDE-LM; export and API compatibility keep a transitional single-value alias where necessary.

## Phase 1 Design

- Data model: [data-model.md](./data-model.md)
- Contracts: [contracts/risk-api.yaml](./contracts/risk-api.yaml), [contracts/threat-exports.md](./contracts/threat-exports.md)
- Validation quickstart: [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

- [x] Module ownership remains explicit: threat changes stay in `scaffold/apps/threat/`, risk ticket links stay in `scaffold/apps/risk/`, and no new shared abstraction is required.
- [x] Security and audit impact are covered: route access must remain role-aware, audit events must include multi-assignment and ticket-link changes, and export changes are identified.
- [x] Validation and migration scope are explicit: one Alembic migration plus focused pytest coverage for threat routes, risk routes, and risk API behavior.
- [x] UI and localization impact are captured: both affected forms and review surfaces require translation updates and Tailwind-consistent rendering.
- [x] Operational impact remains bounded: no new runtime configuration is expected beyond normal migration/release steps and compatibility communication.
