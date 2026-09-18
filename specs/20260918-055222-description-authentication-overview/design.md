---
feature: authentication-overview-tier-infotype-export
status: planned
created: 2026-09-18
decisions:
  - 20260918-0552-authentication-overview-new-columns
  - 20260918-0552-authentication-overview-tier-infotype-summary
  - 20260918-0552-authentication-overview-gap-resolutions
---

# Authentication Overview Export: Info type & Tier Design

## Overview

Extend the existing Authentication Overview export
(`export_authentication_overview` in `scaffold/apps/bia/routes.py`,
rendered by `scaffold/apps/bia/templates/bia/export_authentication.html`)
to surface each component's `info_type` and its owning BIA context's
`BiaTier.level`, both as new per-component columns and as a new nested
summary table.

## User Stories

- As a compliance/security reviewer, I want to see each component's
  information type and risk tier in the Authentication Overview export, so
  that I can assess authentication coverage in the context of data
  sensitivity and business criticality.
- As a reviewer, I want a top-level breakdown of components by Tier and
  Info type, so that I can spot concentrations of sensitive/high-tier
  components without reading every detail table.

## Components

### Detail tables (existing, extended)

Every per-authentication-method table and the "unassigned" table gain two
columns, inserted in this order: **BIA, Component, Tier, Info type, Owner,
Users** (Tier/Info type placed right after Component, before ownership/
usage columns).

- **Info type**: `component.info_type` (raw, unmodified value), or the
  existing `not_set` translation string when blank/whitespace-only or
  `NULL`.
- **Tier**: `component.context_scope.tier.get_label()` (no locale
  argument — `BiaTier.get_label` resolves the tier name via the current
  request locale internally, unlike `AuthenticationMethod.label_for_locale`
  which forces a specific locale; Tier therefore renders in a single,
  current-locale-dependent language, not bilingually like the Method
  summary), or `not_set` when `context_scope.tier` is `None`.
- Long values wrap using the same default table-cell behavior as existing
  free-text columns; no truncation/ellipsis is added.

### New nested summary table

A new table, placed alongside the existing method-summary table at the top
of the export:

- Grouped by Tier (`BiaTier.level` ascending; components with no tier form
  a final "Not set" group).
- Within each Tier group, one row per distinct Info type value present in
  that tier. For grouping only, `info_type` is trimmed and compared
  case-insensitively (e.g. "Customer Data" and "customer data" merge into
  one group, displayed using one of the original casings); blank/
  whitespace-only/`NULL` values form a final "Not set" row. Rows are
  ordered alphabetically ascending with "Not set" last.
- Each row shows the count of matching components.
- If the export has zero components, the table renders with an empty body
  and no dedicated empty-state message (matching the existing
  method-summary table's behavior).

Built in `export_authentication_overview` from the same `components` query
already used for method grouping — no additional DB query needed.

## Data Model

No schema changes. Reuses:

- `Component.info_type` (`scaffold/apps/bia/models/__init__.py:129`)
- `ContextScope.tier` -> `BiaTier` (`scaffold/apps/bia/models/__init__.py:62-63`,
  `BiaTier.level` at line 27, `BiaTier.get_label` at line 36)

## API/Interface

No route signature changes. `export_authentication_overview` gains local
grouping logic (Tier -> Info type -> count) and passes the result to the
template as a new context variable (e.g. `tier_summary`). Template gains:

- Two `<th>`/`<td>` pairs in each existing per-component table, in the
  column order specified above.
- One new `<table>` for the nested Tier/Info type summary.
- New translation keys under `bia.export.authentication_overview.columns`
  (e.g. `info_type`, `tier`) and a new
  `bia.export.authentication_overview.tier_summary` namespace (title,
  column headers, `not_set` tier/info-type labels) in `en.json`/`nl.json`,
  following the existing key structure.

## Out of Scope / Confirmed Non-Changes

- No CSV or other export-format variant exists for this data —
  `export_authentication_overview` is the only route affected.
- No change to access control or the `bia.exported` audit event: the
  export stays behind the existing `@login_required` check, and Info
  type/Tier are already visible elsewhere in the BIA UI to the same users.
- No documentation update: this export's exact column list was not
  previously documented.

## Open Questions

- None outstanding — all structural, formatting, and edge-case decisions
  were resolved during design and the subsequent checklist review (see
  linked decision records).

