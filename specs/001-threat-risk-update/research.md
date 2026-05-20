# Research: Threat Model and Risk Updates

## Decision: Store threat scenario assets through a dedicated association table

**Rationale**: The threat module currently stores one `asset_id` on `ThreatScenario`, but the repo already uses many-to-many tables for plural risk relationships such as `risk_component_links` and `risk_control_links`. A dedicated `threat_scenario_assets` table fits the existing SQLAlchemy style, supports clean uniqueness constraints, and gives `sync_scenario_to_risk()` a stable list of assets to map into linked risk components.

**Alternatives considered**:

- Keep a single `asset_id` and duplicate scenarios per asset: rejected because it conflicts with the spec goal and makes review/export ambiguity worse.
- Store asset IDs as JSON on `ThreatScenario`: rejected because it bypasses relational integrity, complicates joins, and diverges from local patterns.

## Decision: Store STRIDE-LM categories as a separate scenario-to-category relationship

**Rationale**: The current `stride_category` field is a scalar enum, but the feature requires multiple existing STRIDE-LM categories per scenario. A `threat_scenario_stride_categories` table preserves the current enum vocabulary, allows straightforward backfill from the existing column, and keeps dashboard/export grouping queryable without inventing a second taxonomy.

**Alternatives considered**:

- Replace STRIDE-LM with a free-form custom taxonomy: rejected because the clarification explicitly selected the existing STRIDE-LM model.
- Store multiple category values in one delimited string column: rejected because it weakens validation and makes aggregation fragile.

## Decision: Limit multi-category behavior to STRIDE methodology while preserving non-STRIDE scenarios

**Rationale**: The threat form already supports `STRIDE`, `PASTA`, `LINDDUN`, and `OWASP`. The requested category expansion is explicitly for existing STRIDE-LM categories, so the design should make multi-category selection apply when the methodology is STRIDE and leave the other methodology-specific fields intact.

**Alternatives considered**:

- Force all methodologies through STRIDE-LM categories: rejected because it would change unrelated threat workflows.
- Remove the methodology selector from scope: rejected because it is an existing persisted feature and outside the requested change.

## Decision: Model risk ticket links as ordered child records with `label` and `url`

**Rationale**: The risk module currently stores a single `ticket_url`, but the repo already has child-row patterns like `RiskImpactAreaLink`. A `RiskTicketLink` child model with `label`, `url`, and `sort_order` fits local ORM conventions, supports multiple external work items, and keeps form/API validation explicit.

**Alternatives considered**:

- Add multiple `ticket_url_n` columns: rejected because it hardcodes an arbitrary limit and complicates validation.
- Store ticket links as JSON on `Risk`: rejected because it breaks relational consistency and makes ordered editing harder.

## Decision: Preserve compatibility in outward-facing contracts during transition

**Rationale**: The risk API currently emits a scalar `ticket_url`, and the threat CSV export currently emits scalar `asset` and `stride_category` columns. To avoid abrupt breakage, the design should add plural contract fields (`ticket_links`, `assets`, `stride_categories`) while keeping a deprecated single-value alias derived from the first item during the transition window.

**Alternatives considered**:

- Break the existing contract immediately: rejected because the repository already keeps compatibility shims for other contract evolutions such as single-control vs multi-control risk payloads.
- Emit one export row per asset/category combination: rejected because it duplicates scenario-level fields and makes one-scenario review harder.

## Decision: Use one migration with deterministic backfill for existing records

**Rationale**: The feature touches three scalar-to-plural conversions that are conceptually one release unit. One Alembic migration can create the new tables, backfill existing rows from `asset_id`, `stride_category`, and `ticket_url`, then switch application code to the new relationships with a single deploy sequence.

**Alternatives considered**:

- Split into multiple migrations across threat and risk separately: rejected because it increases temporary dual-write complexity for one feature branch.
- Skip backfill and require manual cleanup: rejected because it violates the spec and constitution requirement for safe migration discipline.