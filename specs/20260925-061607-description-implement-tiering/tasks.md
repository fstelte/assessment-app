---
feature: component-tiering
status: planned
created: 2026-09-25
chunk_size: medium
total_tasks: 9
estimated_lines: 545
---

# Component Tiering Tasks

## Overview
Implements per-component tiering (nullable `Component.tier_id`, inheriting the BIA tier) and applies the effective tier's RTO/RPO goals to components, with free-text fallback. See `design.md` and decisions `20260925-0620-component-tier-inherit-from-bia`, `20260925-0625-tier-goals-drive-component-rto-rpo` and `20260925-0640-component-tiering-requirement-resolutions`.

## Task List

### Foundation

#### Task 1: Migration, model properties and duration formatter
- **Estimate:** ~40 lines
- **Files:** `migrations/versions/<new>_add_component_tier.py`, `scaffold/apps/bia/models/__init__.py`, `scaffold/apps/bia/utils.py`
- **Description:** Add nullable `bia_components.tier_id` FK (`ondelete="SET NULL"`, no backfill; downgrade drops the column). Add `Component.tier`, `effective_tier`, `effective_rto`, `effective_rpo`. Add `format_duration_seconds` (largest unit d/h/min/s that divides evenly) and register it as a Jinja filter. Unit labels come from `bia.duration.units.*` (en: s, min, h, d; nl: s, min, u, d); 0 or non-positive renders "<n> s".
- **Depends on:** None
- **Acceptance:** Migration upgrades/downgrades. `effective_tier` = own tier, else BIA tier, else None. RTO and RPO resolve independently: tier goal -> stored text -> None. A tier with only an RTO goal still falls back to stored RPO text.
- **Evidence:** Unit tests pass for the formatter (14400 -> "4 h", 5400 -> "90 min", 90 -> "90 s", 0 -> "0 s", nl labels) and for effective properties incl. no-tier-anywhere and single-goal tiers.

### Core Implementation

#### Task 2: Component form tier field [P]
- **Estimate:** ~60 lines
- **Parallel:** Can run with Tasks 3-6
- **Files:** `scaffold/apps/bia/forms.py`, `scaffold/apps/bia/routes.py`, `scaffold/apps/bia/templates/bia/edit_component.html`, `scaffold/translations/en.json`, `nl.json`
- **Description:** `ComponentForm.tier` select with blank option "Inherit from BIA (TIER x)"; create/edit routes save it; en/nl labels.
- **Depends on:** Task 1
- **Acceptance:** A component can be created/edited with a tier or left inheriting, with the same access rules as editing the component (no extra role).
- **Evidence:** Route tests pass.

#### Task 3: Effective RTO/RPO in availability form [P]
- **Estimate:** ~70 lines
- **Parallel:** Can run with Tasks 2, 4-6
- **Files:** `scaffold/apps/bia/forms.py`, `scaffold/apps/bia/routes.py`, `manage_component_availability.html`, `manage_item_availability.html`, translations
- **Description:** Show each of RTO/RPO read-only as "From {tier label}: {value}" (suffix " (inherited from BIA)" when the component has no own tier) when the effective tier has that goal; otherwise keep the free-text input. Routes ignore submitted RTO/RPO when a tier goal applies so stored text is never overwritten. MTD/MASL unchanged.
- **Depends on:** Task 1
- **Acceptance:** Goal shown read-only when present; free text editable and saved when not. RTO and RPO are decided independently. Saving with a goal applied leaves stored `rto`/`rpo` unchanged.
- **Evidence:** Route tests pass for both cases, incl. a test asserting stored text is preserved while a goal applies.

#### Task 4: Effective values in views, exports and summary aggregation [P]
- **Estimate:** ~90 lines
- **Parallel:** Can run with Tasks 2, 3, 5, 6
- **Files:** `scaffold/apps/bia/templates/bia/components.html` (~299), `requirements.html`, `export_item.html`, `context_detail.html` (~431, component availability table), `export_availability_requirements.html`, `export_availability_summary.html`, `scaffold/apps/bia/routes.py` (~1870-1975, summary aggregation)
- **Description:** Show `effective_rto/rpo` (via the duration filter) wherever component RTO/RPO is displayed; components without an availability row still show tier-derived values. The summary aggregation takes the tier goal in minutes when a goal applies, else `_parse_duration` of the stored text, and includes components with no availability row. BIA-level views (context header, archived list, SSP, all-tiers export) are unchanged. Empty values use the shared "Not set" translation key.
- **Depends on:** Task 1
- **Acceptance:** Every listed view shows effective values; a component with a tier goal and no availability row appears in views and in the per-BIA lowest RTO/RPO; "Not set" when nothing applies.
- **Evidence:** Route/render tests pass, incl. summary aggregation with a tier goal, with stored text only, and with no availability row.
#### Task 5: Incident prefill [P]
- **Estimate:** ~25 lines
- **Parallel:** Can run with Tasks 2-4, 6
- **Files:** `scaffold/apps/incident/services.py`, `scaffold/apps/incident/routes.py`
- **Description:** Prefill incident steps RTO/RPO from the effective values, only when the step's value is empty (existing behaviour). Saved steps are never rewritten when a tier goal changes.
- **Depends on:** Task 1
- **Acceptance:** Incident steps prefill tier-derived RTO/RPO, else stored text.
- **Evidence:** Incident tests pass.

#### Task 6: Authentication Overview effective tier [P]
- **Estimate:** ~40 lines
- **Parallel:** Can run with Tasks 2-5
- **Files:** `scaffold/apps/bia/routes.py` (~1721), `scaffold/apps/bia/templates/bia/export_authentication.html`
- **Description:** Eager-load component tier; the per-component Tier column uses `effective_tier` (the tier/info-type summary was already removed by decision 20260919-1235).
- **Depends on:** Task 1
- **Acceptance:** A component with its own tier shows that tier in the Tier column; others show the BIA tier.
- **Evidence:** Existing authentication overview tests updated and passing.

### Data Flow

#### Task 7: Export, import, audit, duplicate BIA
- **Estimate:** ~90 lines
- **Files:** `scaffold/apps/bia/utils.py` (CSV export ~275-318, CSV import ~543, SQL export ~718-737, SQL import ~899-908), `scaffold/core/audit.py`, `scaffold/apps/bia/routes.py` (~2299)
- **Description:** SQL export writes component `tier_id`; SQL import sets it to null when no `BiaTier` with that id exists. CSV export appends a "Component Tier" column (`TIER n > name`); CSV import parses the level. Unknown tier or missing column -> null (inherit) with a warning in the import result. Add `tier_id` to the `Component` field list in `core/audit.py`. Duplicate BIA copies component `tier_id`. RTO/RPO columns keep exporting stored text.
- **Depends on:** Task 1
- **Acceptance:** CSV and SQL round-trips preserve component tier when tiers exist; CSV round-trip preserves it across environments with different tier ids (by level); SQL import with an unknown tier id imports as inherit; legacy files without the column import; duplicate keeps tiers; audit records tier changes.
- **Evidence:** CSV round-trip, SQL round-trip, unknown-tier, legacy-file, duplicate and audit tests pass.
#### Task 8: Fix context tier import (CSV and SQL) [P]
- **Estimate:** ~60 lines
- **Parallel:** Independent of Task 1; can run with Tasks 1-6. Touches the same files as Task 7 (utils.py, routes.py), so do it before or after Task 7, not alongside.
- **Files:** `scaffold/apps/bia/utils.py` (CSV context import ~496-523, `import_from_csv`, `import_sql_file`, SQL context insert ~877-893), `scaffold/apps/bia/routes.py` (~1644, ~2101), translations
- **Description:** CSV context import reads "BIA Tier" (`TIER n > name`), resolves the level to a `BiaTier`, sets `tier_id`. SQL context import keeps `tier_id` only if that `BiaTier` exists. Blank/unknown -> null. `import_from_csv` and `import_sql_file` return a list of warning strings; the routes flash them (en/nl keys).
- **Depends on:** None
- **Acceptance:** A CSV export of a tiered BIA re-imports with the same tier (also when tier ids differ); a SQL import with an unknown context `tier_id` imports with no tier and a warning; blank tier stays blank without a warning.
- **Evidence:** CSV round-trip, SQL unknown-id and blank-tier tests pass.

### Integration

#### Task 9: Route tests, translation parity and docs
- **Estimate:** ~70 lines
- **Files:** `tests/test_bia_routes.py`, `tests/test_translation_keys.py` (run/extend), `docs/models.md`, `docs/` export/import notes
- **Description:** Also documents the context tier import behaviour and its SQL id limitation. End-to-end route tests for inheritance and availability behaviour; confirm en/nl key parity for the new keys; document `Component.tier_id`, the effective properties and the new "Component Tier" CSV column / `tier_id` in SQL export.
- **Depends on:** Tasks 2-8
- **Acceptance:** Full test suite passes; new keys exist in en and nl; docs updated.
- **Evidence:** `pytest` green (incl. `test_translation_keys.py`).
## Notes
- Chunk size assumed medium (constitution has no explicit setting).
- Not covered: dropping free-text RTO/RPO columns, tier ceiling/floor rules, tier goals vs MTD/MASL.
- Stored free-text RTO/RPO is retained in the DB and exported as-is.
- No tier delete route exists today; the FK uses `SET NULL` so a future delete falls back to inheritance.

## Progress
- [x] Task 1: Migration, model properties and duration formatter
- [x] Task 2: Component form tier field
- [x] Task 3: Effective RTO/RPO in availability form
- [x] Task 4: Effective values in views, exports and summary aggregation
- [x] Task 5: Incident prefill
- [x] Task 6: Authentication Overview effective tier
- [ ] Task 7: Export, import, audit, duplicate BIA
- [ ] Task 8: Fix context tier import (CSV and SQL)
- [ ] Task 9: Route tests, translation parity and docs