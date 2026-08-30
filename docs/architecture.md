# Architecture Overview

This document captures the target architecture for the scaffold application that unifies the `bia_app` and `csa_app` domains while keeping space for future extensions.

## Vision

- Provide a single Flask foundation that hosts multiple domain applications.
- Reuse shared services (authentication, session security, database access, exports) across all domains.
- Maintain module boundaries so that each domain can evolve semi-independently.
- Offer a clear expansion path for future apps without duplicating infrastructure.

## Layered Design

1. **Presentation** – Flask blueprints per domain, mounted under a shared Tailwind CSS dark-mode layout. A navigation registry exposes all registered apps and renders contextual menu items.
2. **Application Services** – Shared service layer for authentication, role management, notifications, exports, and background tasks. Domain-specific services live alongside their module but follow shared interfaces.
3. **Domain & Persistence** – SQLAlchemy models grouped by domain (`scaffold/apps/bia`, `scaffold/apps/csa`) and joined through a common metadata registry. Alembic migrations operate on the unified metadata.
4. **Infrastructure** – Centralised configuration, logging, dependency management, and environment bootstrapping. Optional integrations (Celery/RQ, email, observability) plug into the same layer.

## Module Layout

```text
scaffold/
    __init__.py          # Application factory
    config.py            # Settings loader
    extensions.py        # Flask extension instances
    tailwind_cli.py      # Tailwind CSS standalone-CLI build helper
    core/
        registry.py      # Discovery and registration of app modules
    apps/
        bia/             # BIA domain integration
        csa/             # CSA domain integration
        dpia/            # DPIA / FRIA assessments integrated with BIA components
        risk/            # Risk workspace with severity matrix and CSA control links
        maturity/        # CMMI maturity assessments per CSA control
        incident/        # Incident response plans linked to BIA components
        tools/           # Interactive utilities (AI Act Checker, CVSS, etc.)
        threat/          # STRIDE-LM threat modeling with scenario lifecycle
        template/        # Starter template for future domains
```

Each module exposes a `register(app)` function or a `blueprints` collection so the registry can attach routes, CLI commands, and signal handlers automatically.

## Authentication Strategy

- Consolidate the CSA user lifecycle (`UserStatus`, role relationships, MFA settings) with BIA-specific constraints.
- Provide a shared authentication blueprint that handles login, MFA enrolment, verification, and profile management.
- Reuse BIA session fingerprinting and CSA MFA utilities for stronger security posture.
- Offer extension hooks for app-specific authorisation policies.

## Control Catalogue Administration

- The `Control Owner` role can access `/admin/controls` alongside full administrators. Owners curate the CSA catalogue by creating entries manually or ingesting bundled datasets.
- The optional `Control Assigner` role is used when delegating assessment assignments without granting full catalogue access; it appears in the user administration UI with a localized label so administrators can reason about responsibilities quickly.
- The admin controls page now surfaces contextual headings, helper text for the manual form, and richer flash feedback so non-technical users understand what each action does.
- A new NIST SP 800-53 dataset option sits next to the ISO/IEC 27002 JSON import. The parser reads the upstream plain-text reference, groups bullet lines into descriptions, and feeds the shared importer. This lets teams seed US federal baselines without maintaining a JSON export.

## Architecture Decision Records (ADR)

- Every System Security Plan can carry a set of Architecture Decision Records ([adr.github.io](https://adr.github.io/) style: Title, Status, Context, Decision, Consequences). Creating an ADR always starts by selecting one required primary Architecture Principle, plus optional secondary principles for decisions that touch more than one.
- The **Architecture Principle catalogue** is administered at `/admin/principles`, by the same role as the control catalogue (`admin` or the `Control Owner` role) and with the same create/edit/delete/bulk-delete flow as `/admin/controls`. Unlike controls, deleting a principle that is still referenced by an ADR is blocked — this is a deliberate difference from control deletion (which has no such guard), because an ADR's principle reference is a compliance record, not disposable working data.
- Principles support **bulk import** from a JSON file at `/admin/principles`, shaped as:
  ```json
  {
    "principles": [
      { "name": "Least Privilege by Default", "description": "Grant the minimum access required..." }
    ]
  }
  ```
  Import upserts by name (case-insensitive, trimmed) and reports a created/updated/error summary, matching the control catalogue's import UX. See `specs/20260829-095929-description-adr-https/design.md` for a fuller example file.
- ADR status follows a fixed lifecycle (`Proposed → Accepted/Rejected`, `Accepted → Deprecated`) plus a **supersede** action: creating a new ADR can declare it supersedes an existing one in the same SSP, which immediately flips the older ADR's status to `Superseded` and links both records. Supersession is one-directional and can only happen once per ADR — an already-superseded ADR cannot be selected as a supersede target again.
- Every principle/ADR mutation (create, update, delete, import, status change, supersession) writes an `AuditLog` row via `log_event()`, per this project's Security & Auditability principle.

## Architecture Overview Image

- Every System Security Plan can carry an **architecture overview image** — a PNG or JPEG diagram uploaded from the SSP's main overview page, displayed inline near the authorization boundary/FIPS fields. Any authenticated user who can reach `ssp.edit` can upload one; no new role was introduced.
- Uploads must be PNG or JPEG, decoded and verified with Pillow (not just checked by filename/MIME header), 5 MB or smaller, and within an 8000×8000 pixel cap (on top of Pillow's own decompression-bomb guard) to keep a small, malicious file from being decoded into an oversized image.
- Image bytes are stored **in the database** (`ssp_architecture_overview_versions`, a `LargeBinary` column), not on the container filesystem — the deployment has no user-upload volume mounted (only `./backups`/`./restore`, see `docs/deployment.md`), so filesystem storage would silently lose uploads on container recreation. See decision record `20260829-1230-architecture-overview-image-design` for the full rationale.
- Every upload creates a new, **immutable, append-only version**, numbered per SSP (`UniqueConstraint(ssp_id, version_number)` prevents two concurrent uploads from landing on the same number). The current image is simply the version with the highest number — there is no separate "is current" flag to keep in sync.
- Past versions are listed in a collapsible history (uploader, timestamp) with a **Restore** action. Restoring never rewrites history: it reads the old version's bytes and inserts them as a brand-new version (copy-forward), the same pattern this codebase already uses for ADR supersession.
- The image-serving route (`GET /ssp/<id>/architecture-overview/<version_id>/image`) sets `Content-Disposition: inline` and `X-Content-Type-Options: nosniff` so a browser can't reinterpret an upload as something other than its declared image type.
- Every upload and restore writes an `AuditLog` row via `log_event()` (`entity_type="ssp_architecture_overview"`); a restore's payload records which version number it restored from.

## Database Strategy

- Unified SQLAlchemy metadata backed by Flask-Migrate.
- Environment variable `DATABASE_URL` selects the engine (PostgreSQL recommended, SQLite allowed for development).
- Provide a Poetry extra (`postgresql`) for environments that prefer optional driver management.
- Maintain migration scripts in `migrations/` with domain-aware naming.
- Document engine-specific considerations (character sets, JSON support, backup) in `docs/deployment.md`.

## Extensibility

- Registry-driven module discovery via `SCAFFOLD_APP_MODULES` environment variable.
- Template module demonstrates minimal structure for a new app (blueprint, services, models).
- Shared documentation outlines the checklist for integrating additional domains.

## Roadmap

1. ~~Port existing models and migrations into the unified metadata layer.~~ ✓ Complete.
2. ~~Merge authentication flows and session security primitives.~~ ✓ Complete.
3. ~~Migrate templates and static assets to Tailwind CSS dark-mode theme.~~ ✓ Complete (Bootstrap removed 2026-02-27).
4. Expand smoke-test coverage for cross-domain navigation, MFA flows, and threat modeling.
5. Publish database migration and deployment guidance for PostgreSQL at scale.
