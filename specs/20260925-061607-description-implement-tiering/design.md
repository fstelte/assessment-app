---
feature: component-tiering
status: planned
created: 2026-09-25
decisions:
  - 20260925-0620-component-tier-inherit-from-bia
  - 20260925-0625-tier-goals-drive-component-rto-rpo
  - 20260925-0640-component-tiering-requirement-resolutions
---

# Component Tiering Design

## Overview
Add an optional tier to each BIA component using the same `BiaTier` definition
as the BIA (`ContextScope.tier`). A component without its own tier inherits the
BIA's. The tier's RTO/RPO goals are applied directly (derived at read time, not
copied) as the component's effective RTO/RPO, falling back to the stored
free-text values.

## User Stories
- As a BIA author, I want to set a tier per component so that components that
  differ from their BIA are classified correctly.
- As a BIA author, I want components to inherit the BIA tier by default so that
  I only enter what differs.
- As a reader, I want a component's RTO/RPO to follow its tier's goals so that
  the tier is the single definition.

## Requirements
- Effective tier: component's own tier, else the BIA's tier, else none.
- Effective RTO and RPO are resolved independently: tier goal (formatted) ->
  stored free text -> "Not set".
- Setting a component tier needs the same access as editing the component.
- Label format everywhere is `BiaTier.get_label()`; "Not set" uses one shared
  translation key.

## Components
### Model (`bia/models/__init__.py`)
- `Component.tier_id` nullable FK to `bia_tiers.id` (`ondelete="SET NULL"`),
  `Component.tier` relationship.
- `Component.effective_tier`, `effective_rto`, `effective_rpo`.
- `format_duration_seconds(seconds)`: units 86400 d, 3600 h, 60 min, 1 s; largest
  unit that divides evenly; 0 or non-positive renders "<n> s". Unit labels from
  `bia.duration.units.*` (en: s, min, h, d; nl: s, min, u, d). Registered as a
  Jinja filter.

### Forms (`bia/forms.py`)
- `ComponentForm.tier` select: same choices as the context form; blank option
  "Inherit from BIA (TIER x)".
- Availability form: RTO/RPO each rendered read-only as "From {tier label}:
  {value}" (suffix " (inherited from BIA)" when the component has no own tier)
  when the effective tier has that goal; otherwise editable free text. Stored
  text is never overwritten while a goal applies. MTD/MASL unchanged.

### Consumers
- Component-level views use effective values: `components.html`, `requirements.html`,
  `export_item.html`, `context_detail.html` (component availability table),
  `export_availability_requirements.html`, Authentication Overview per-component
  Tier column, incident prefill (only for empty step RTO/RPO; saved steps are not
  rewritten). Components without an `AvailabilityRequirements` row still show a
  tier-derived RTO/RPO.
- Availability summary export (lowest RTO/RPO per BIA): uses the tier goal in
  minutes when a goal applies, else `_parse_duration` of the stored text; includes
  components with no availability row; displays tier-derived values with the
  duration formatter.
- BIA-level views stay on the BIA tier: context detail header, archived list, SSP
  view/print, all-tiers export, context CSV row.
- Authentication Overview: only the per-component Tier column changes (the
  tier/info-type summary was removed by decision 20260919-1235).
- Audit (`core/audit.py`): add `tier_id` to the `Component` field list.
- Data export/import (`bia/utils.py`; the app has CSV and SQL, no JSON): SQL writes
  component `tier_id`, and import nulls it when no such `BiaTier` exists. CSV adds
  a "Component Tier" column (`TIER n > name`, appended last); import parses the
  level. Unknown tier or missing column -> null with a warning. RTO/RPO columns
  keep exporting stored text (lossless round-trip).
- Context tier import fixes (existing gaps, same change): CSV context import reads
  "BIA Tier" and resolves the level; SQL context import keeps `tier_id` only when
  the `BiaTier` exists. Blank/unknown -> null. `import_from_csv` and
  `import_sql_file` return warning strings that the routes flash.
- Duplicate BIA copies each component's ``tier_id``.
### Migration
- Add `bia_components.tier_id` (nullable, FK `ondelete="SET NULL"`, no
  backfill). Downgrade drops the column (component tiers lost; documented).

## Data Model
`bia_components.tier_id -> bia_tiers.id` (nullable). No changes to
`bia_tiers` or `bia_availability_requirements`.

## API/Interface
No new endpoints. Existing component create/edit and availability routes gain
the tier field / read-only goals. Translations (en, nl) for new labels and
duration units.

## Constitution Check
- **Module ownership:** model, forms, routes, templates and formatter stay in
  `scaffold/apps/bia/`; the incident module only reads the bia model (as it does
  today). Audit mapping stays in `core/audit.py`.
- **Security/audit:** no new roles; setting a tier needs the same access as editing
  the component; `tier_id` added to audit fields; exports gain a tier column but
  no new data exposure beyond what the component pages show.
- **Validation:** pytest coverage in every task plus Task 8 (route tests,
  translation-key parity).
- **Localization:** en/nl keys for the tier field, read-only wording, duration
  units and "Not set"; exports use the same terminology as the UI.
- **Migration/operational:** Alembic migration (nullable, `SET NULL`, no backfill,
  downgrade drops the column); docs updated for the export column.

## Scope
Covered: everything above. Not covered: dropping the free-text RTO/RPO columns,
tier ceiling/floor rules, comparing tier goals to MTD/MASL, a tier delete
feature, tier reporting beyond the Authentication Overview.

## Open Questions
None outstanding.