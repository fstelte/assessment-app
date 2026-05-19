<!--
Sync Impact Report
Version change: unversioned template -> 1.0.0
Modified principles:
- Principle slot 1 -> I. Modular Domain Boundaries
- Principle slot 2 -> II. Security, Auditability, and Least Surprise
- Principle slot 3 -> III. Test and Migration Discipline
- Principle slot 4 -> IV. Consistent UI and Localization
- Principle slot 5 -> V. Operational Readiness Over Local Convenience
Added sections:
- Technology and Architecture Standards
- Delivery Workflow and Quality Gates
Removed sections:
- None
Templates requiring updates:
- ✅ .specify/templates/plan-template.md
- ✅ .specify/templates/spec-template.md
- ✅ .specify/templates/tasks-template.md
Follow-up TODOs:
- None
-->

# Assessment App Constitution

## Core Principles

### I. Modular Domain Boundaries
All new business capability MUST fit the Flask application-factory and blueprint
architecture already used in `scaffold/apps/`. Domain behavior MUST live beside
its owning module's routes, forms, models, templates, and services. Shared code
MUST move into `scaffold/core/`, `scaffold/extensions.py`, or another existing
cross-cutting surface only when at least two modules benefit from it. Direct
cross-domain shortcuts that bypass the owning module's abstractions MUST be
avoided unless they are documented in the implementation plan.

Rationale: the platform consolidates multiple assessment domains into one codebase,
so enforceable module boundaries are necessary to keep growth manageable.

### II. Security, Auditability, and Least Surprise
Changes that touch authentication, authorization, admin controls, exports,
sensitive data, or assessment evidence MUST preserve secure defaults, explicit
role checks, and audit visibility. Break-glass or legacy access paths MUST stay
environment-controlled and disabled by default for production. Any change that
alters who can view, edit, export, or sync data MUST identify the affected roles,
audit implications, and operational risk before implementation is approved.

Rationale: the application handles security assessments and governance evidence,
so trust depends on predictable access control and reviewable activity.

### III. Test and Migration Discipline
Behavior changes MUST ship with focused automated validation using the existing
pytest suite. Schema changes MUST ship with an Alembic migration and a review of
upgrade impact. Bug fixes SHOULD add or update a regression test whenever the
behavior can be exercised automatically. A change is not complete until the most
specific available validation for the touched area has been run and documented.

Rationale: the repository uses shared metadata, many interacting modules, and
frequent releases; regressions and schema drift are otherwise expensive.

### IV. Consistent UI and Localization
New UI and template work MUST use the established Tailwind-based design language,
reuse shared macros or layout patterns where available, and route user-facing
copy through the project's localization helpers. Bootstrap MAY remain only in
legacy surfaces that already depend on it and MUST not be introduced in new
implementation. Exports and generated views MUST preserve the same meaning and
terminology as the interactive UI.

Rationale: the platform serves non-technical users across multiple modules, so
consistency and translation coverage are part of correctness, not polish.

### V. Operational Readiness Over Local Convenience
Production behavior MUST assume containerized deployment on another machine,
environment-driven configuration, database migrations during release flow, and
observable failure modes. Features that change deployment, scheduled work,
security integration, backup or restore behavior, or required environment
variables MUST update the relevant operational documentation in the same change.
Local-only shortcuts MUST not become a hidden production dependency.

Rationale: the system is deployed through Docker-based workflows, so undocumented
runtime assumptions turn directly into release failures.

## Technology and Architecture Standards

- Python 3.11, Flask, SQLAlchemy, Alembic, and Poetry are the authoritative
	backend stack unless an approved amendment states otherwise.
- Settings MUST be loaded through `scaffold.config.Settings` and environment
	variables; secrets MUST not be hard-coded in source files.
- Model changes belong in the owning module under `scaffold/apps/<domain>/` and
	MUST remain compatible with the unified migration strategy in `migrations/`.
- New frontend work MUST default to Tailwind utilities and the existing Jinja2
	template structure under `scaffold/templates/` and `scaffold/apps/*/templates/`.
- Significant user-visible, deployment-visible, or compliance-visible behavior
	changes MUST be reflected in the repository documentation under `README.md` or
	`docs/` within the same workstream.

## Delivery Workflow and Quality Gates

- Substantial work MUST be captured through the Spec Kit flow so that
	specification, plan, and task artifacts can be checked against this
	constitution before implementation starts.
- Every implementation plan MUST explicitly confirm module ownership, security
	and audit impact, validation scope, localization impact, and operational or
	migration impact.
- Reviewers and implementers MUST reject changes that skip required tests,
	required migrations, required docs, or required translation updates when those
	concerns are in scope.
- When a change introduces justified complexity, the implementation plan MUST
	record why a simpler option was rejected.

## Governance

This constitution overrides conflicting local conventions for planning,
implementation, and review. Amendments MUST be made through a documented change
that updates this file and any affected templates in `.specify/templates/`.

Versioning policy:
- MAJOR: remove or redefine a governing principle in a backward-incompatible way.
- MINOR: add a principle, add a mandatory governance section, or materially
	expand an existing rule.
- PATCH: clarify wording, fix ambiguity, or make non-semantic editorial changes.

Compliance review expectations:
- Every plan MUST pass a constitution check before design or implementation work
	proceeds.
- Every task list MUST reflect required validation, migration, security,
	localization, and documentation work when those concerns apply.
- Every implementation review MUST verify compliance using the current
	constitution, [README.md](c:/Users/fstelte/Documents/assessment-app/README.md),
	and [docs/deployment.md](c:/Users/fstelte/Documents/assessment-app/docs/deployment.md)
	as the primary runtime guidance.

**Version**: 1.0.0 | **Ratified**: 2026-05-17 | **Last Amended**: 2026-05-17
