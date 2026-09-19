---
title: Resolve checklist gaps for Authentication Overview column/summary design
date: 2026-09-18
status: accepted
---

## Context

Running `/minispec.checklist` against the design in
[[20260918-0552-authentication-overview-new-columns]] and
[[20260918-0552-authentication-overview-tier-infotype-summary]] surfaced
several unspecified details: column placement, free-text normalization,
empty-string handling, empty-state rendering, and whether this change has
audit/access-control/documentation/truncation implications. This record
resolves each.

## Decisions

- **Column order** (amended by [[20260919-1235-authentication-overview-environments-column]]:
  `Users` is replaced by `Environments`; the summary-table decisions below
  no longer apply): in the detail tables, new columns are inserted as
  `BIA, Component, Tier, Info type, Owner, Users` — Tier and Info type
  (classification/context) come right after identifying the component and
  before ownership/usage details.
- **Info type normalization**: for summary-table grouping only, `info_type`
  values are trimmed and compared case-insensitively (e.g. "Customer Data"
  and "customer data" count as one group). The detail-table columns still
  display the component's raw, unmodified `info_type` value; only the
  summary table's grouping key is normalized. One of the original casings
  is used as the group's display label.
- **Empty/blank handling**: an empty string or whitespace-only `info_type`
  is treated identically to `NULL` — rendered as "Not set" in both detail
  columns and the summary table, consistent with the normalization above.
- **Empty state**: if the export contains zero components, the new nested
  summary table renders with an empty body and no dedicated empty-state
  message, matching the existing (undecorated) behavior of the
  method-summary table.
- **Audit logging / access control**: no change. The export remains
  gated by the existing `@login_required` check and continues to log a
  single `bia.exported` event; Info type and Tier are already visible to
  the same users elsewhere in the BIA UI, so this does not broaden data
  exposure or require a more granular audit entry.
- **Documentation**: no update required. This export's exact column list
  was not previously documented in `README.md`/`docs/`, so there is
  nothing stale to fix.
- **Long text handling**: no truncation/ellipsis logic is added. The
  `info_type` column wraps using the same default table-cell behavior as
  existing free-text columns (Component name, Owner).
- **Other export formats**: confirmed there is no CSV (or other format)
  variant of the authentication overview — `export_authentication_overview`
  is the only route rendering this data, so no other export needs
  updating.

## Rationale

Keeping normalization scoped to grouping only (not the displayed
per-component value) avoids silently altering data the user entered,
while still preventing the summary table from fragmenting into
near-duplicate rows for the same real-world info type. Declining new
audit/docs/truncation work keeps the change matched to its actual size —
extending an already-authorized, already-visible data export with two
more columns and a summary view, not introducing a new data-exposure
surface.
