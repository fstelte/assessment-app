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
- The **Architecture Principle catalogue** is administered at `/admin/principles`, by the same role as the control catalogue (`admin` or the `Control Owner` role) and with the same create/edit/delete/bulk-delete flow as `/admin/controls`. Unlike controls, deleting a principle that is still referenced by an ADR is blocked — this is a deliberate difference from control deletion (which has no such guard), because an ADR's principle reference is a compliance record, not disposable working data. Admins reach the page through the **Principles** button in the admin menu (`/admin/users`) and in the top navigation. Descriptions have no application-level length cap; the only limit is Flask's `MAX_FORM_MEMORY_SIZE` (500 KB per form field by default), which the JSON import applies too, so every principle can be edited and saved.
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

## Architecture Overview Files

- Every System Security Plan can carry **architecture overview files**: one or more PNG, JPEG or PDF diagrams uploaded from the SSP's main overview page and shown together, oldest first (`uploaded_at, id`). Any authenticated user who can reach the SSP can upload and delete them; no role was introduced. Several files can be selected in one upload, which is all or nothing: if any file is refused, nothing is saved (decisions `20261119-1825`, `20261119-1827`).
- Each file is validated on its bytes, not its filename or browser-supplied MIME type. A PDF must start with `%PDF-`. An image must decode and verify with Pillow as PNG or JPEG within an 8000×8000 pixel cap, on top of Pillow's decompression-bomb guard. Each file may be at most 10 MB. The stored `mime_type` is the detected one (decision `20261118-1505`).
- Batches are capped at 100 MB: the gateway sets `client_max_body_size 100m`, and `ui.js` blocks a larger selection before it is sent. Flask's `MAX_CONTENT_LENGTH` stays unset (decision `20261120-0900`, `docs/deployment.md`).
- File bytes are stored **in the database** (`ssp_architecture_overview_versions`, a `LargeBinary` column; the table keeps its legacy name), not on the container filesystem. The deployment has no user-upload volume mounted (only `./backups`/`./restore`, see `docs/deployment.md`), so filesystem storage would silently lose uploads on container recreation. See decision record `20260829-1230-architecture-overview-image-design`.
- Files are not versioned. Version numbers, history and restore were removed in migration `20261119_0001`, which kept only the newest version per SSP. To replace a diagram, delete it and upload the new one.
- The serving route (`GET /ssp/<id>/architecture-overview/<file_id>/image`) sets `X-Content-Type-Options: nosniff`. Images are served `inline`. PDFs are always served as `attachment`, so user-supplied PDFs never render from the app's origin, and the CSP is unchanged.
- Every upload and delete writes one `AuditLog` row per file via `log_event()` (`entity_type="ssp_architecture_overview"`, details `{ssp_id, original_filename}`).

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
