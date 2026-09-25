---
type: decision
id: 20260925-0640-component-tiering-requirement-resolutions
date: 2026-09-25
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/bia/models/__init__.py
  - scaffold/apps/bia/utils.py
  - scaffold/core/audit.py
  - scaffold/apps/incident/*
  - scaffold/translations/*
tags: [bia, tier, checklist]
participants: [Ferry Stelte, Claude]
---

# Component tiering: resolutions of requirements checklist gaps

Resolves the gaps found by `checklists/general.md`. These refine
[[20260925-0620-component-tier-inherit-from-bia]] and
[[20260925-0625-tier-goals-drive-component-rto-rpo]].

## Decisions

- **Tier deletion / level change (CHK001):** There is no tier delete route today.
  The new FK uses `ondelete="SET NULL"` so a future delete falls back to
  inheriting the BIA tier. Level changes are safe: the FK is by id.
- **Authorization (CHK002):** Setting a component's tier needs the same access as
  editing the component. No extra role.
- **Incident steps (CHK003):** Steps store copied text and are not rewritten when a
  tier goal changes. Prefill applies only when a step's RTO/RPO is empty
  (existing behaviour).
- **Single-goal tiers (CHK004):** RTO and RPO are resolved independently: goal if
  set, else stored text, else "Not set".
- **Scope of views (CHK015):** BIA-level views (context detail, archived
  list, SSP view/print, all-tiers export, context CSV row) stay on the BIA
  tier. Component-level views (component detail, availability views/exports,
  Authentication Overview tier column, incident prefill, component data
  export) use the effective tier.
- **Audit (CHK006):** Add `tier_id` to the `Component` field list in
  `core/audit.py`.
- **Duration format (CHK007-CHK008):** Units 86400 d, 3600 h, 60 min, 1 s; the
  largest that divides the value evenly wins. 0 and non-positive values render
  as "<n> s". Labels come from translation keys (`bia.duration.units.*`):
  en `s`, `min`, `h`, `d`; nl `s`, `min`, `u`, `d`.
- **"Applied directly" (CHK009):** Derived at read time, never copied into the
  stored `rto`/`rpo` columns.
- **Availability form wording (CHK010):** "From {tier label}: {value}", with the
  suffix " (inherited from BIA)" when the component has no own tier.
- **"Not set" (CHK011):** One shared translation key, reusing the existing
  Authentication Overview "not set" text.
- **Label format (CHK012):** Always `BiaTier.get_label()`.
- **Authentication Overview (CHK013):** The tier/info-type summary was already
  removed by [[20260919-1235-authentication-overview-environments-column]].
  Only the per-component Tier column changes, to the effective tier.
- **Exports vs screen (CHK014):** Intentional. Backup-style CSV/JSON exports keep
  stored `rto`/`rpo` text (lossless round-trip); on-screen views and the
  HTML availability summary/detailed exports show effective values.
- **Import/export (CHK018-CHK019):** The app exports CSV and SQL (there is no JSON
  export). SQL export writes component `tier_id`; SQL import sets it to null
  when no `BiaTier` with that id exists (level cannot travel through SQL
  because non-table columns are dropped on import). CSV export gains a
  "Component Tier" column (`TIER n > name`, appended last); CSV import parses
  the level (`TIER (\d+)`). Unknown tier or missing column -> null (inherit)
  with a warning in the import result. The existing context-tier import gaps are fixed in the same change (see below).
- **Views and aggregation (CHK005, CHK014):** Effective RTO/RPO also drives:
  `components.html`, `requirements.html`, `export_item.html`,
  `context_detail.html` (component availability table),
  `export_availability_requirements.html` and the summary export. The summary
  aggregation (lowest RTO/RPO per BIA) uses the tier goal in minutes when a
  goal applies, else `_parse_duration` of the stored text, and includes
  components that have no `AvailabilityRequirements` row.- **No tier anywhere (CHK020):** `effective_tier` is None; RTO/RPO fall back to
  stored text, else "Not set".
- **Migration (CHK021):** Nullable column, FK `ondelete="SET NULL"`, no backfill.
  Downgrade drops the column (component tiers are lost; documented).
- **Context tier import fixes (in scope):** CSV context import reads "BIA Tier"
  (`TIER n > name`), resolves the level to a `BiaTier`, and sets `tier_id`;
  blank or unknown -> null with a warning. SQL context import keeps `tier_id`
  only if a `BiaTier` with that id exists, else null with a warning (SQL cannot
  carry the level; a valid id that differs between environments is a known,
  documented limitation). `import_from_csv` and `import_sql_file` return a list
  of warning strings, which their routes (`routes.py:1644`, `2101`) flash.