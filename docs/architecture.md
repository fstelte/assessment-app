# Architecture Overview

This document captures the target architecture for the scaffold application that unifies the `bia_app` and `csa_app` domains while keeping space for future extensions.

## Vision

- Provide a single Flask foundation that hosts multiple domain applications.
- Reuse shared services (authentication, session security, database access, exports) across all domains.
- Maintain module boundaries so that each domain can evolve semi-independently.
- Offer a clear expansion path for future apps without duplicating infrastructure.

## Layered Design

1. **Presentation** – Flask blueprints per domain, mounted under a shared Bootstrap 5 dark-mode layout. A navigation registry exposes all registered apps and renders contextual menu items (BIA, CSA, Template by default).
2. **Application Services** – Shared service layer for authentication, role management, notifications, exports, and background tasks. Domain-specific services live alongside their module but follow shared interfaces.
3. **Domain & Persistence** – SQLAlchemy models grouped by domain (`scaffold/apps/bia`, `scaffold/apps/csa`) and joined through a common metadata registry. Alembic migrations operate on the unified metadata.
4. **Infrastructure** – Centralised configuration, logging, dependency management, and environment bootstrapping. Optional integrations (Celery/RQ, email, observability) plug into the same layer.

## Module Layout

```text
scaffold/
    __init__.py          # Application factory
    config.py            # Settings loader
    extensions.py        # Flask extension instances
    core/
        registry.py      # Discovery and registration of app modules
    apps/
        bia/             # BIA domain integration
        csa/             # CSA domain integration
        dpia/            # DPIA / FRIA assessments integrated with BIA components
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

1. Port existing models and migrations into the unified metadata layer.
2. Merge authentication flows and session security primitives.
3. Harmonise templates and static assets under the Bootstrap dark-mode theme.
4. Deliver smoke tests covering cross-domain navigation and MFA flows.
5. Publish migration and deployment guidance for PostgreSQL.
