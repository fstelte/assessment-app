---
title: Add nested Tier/Info type summary table to Authentication Overview export
date: 2026-09-18
status: superseded
superseded_by: 20260919-1235-authentication-overview-environments-column
---

## Context

Following [[20260918-0552-authentication-overview-new-columns]], the
Authentication Overview export gains per-component Tier and Info type
detail columns. The engineer also wants a top-level summary view of how
components break down across Tier and Info type, similar in spirit to the
existing method-summary table.

Two flat single-dimension summaries (one by Tier, one by Info type) were
considered but rejected: Info type is free text and, viewed alone, would
produce a noisy, unbounded list. A flat (Tier, Info type) row-per-pair table
was also considered but loses the grouping structure that makes the tiering
scannable.

## Decision

Add a single new summary table, placed alongside the existing
method-summary table at the top of the export, structured as nested
counts:

- Outer grouping: **Tier**, sorted by `BiaTier.level` ascending, with a
  final "Not set" group for components whose BIA context has no tier
  assigned.
- Inner rows: one per distinct **Info type** value present within that
  tier, sorted alphabetically ascending, with a final "Not set" row for
  components with a blank/null `info_type`.
- Each inner row shows the count of components matching that
  (Tier, Info type) combination.

## Rationale

- Tier is a small, bounded classification, so grouping by it first keeps
  the table's size manageable regardless of how many distinct Info type
  values exist.
- Ascending/natural ordering with "Not set" pushed to the end matches the
  ordering convention already used for Tier, applied consistently to Info
  type as well.
- A single combined table (vs. two separate flat summaries) directly
  answers "how many components of each info type per tier" without
  requiring the reader to cross-reference two tables.

## Scope boundary

This only affects the Authentication Overview export. No schema changes;
grouping/counting happens in `export_authentication_overview` using data
already loaded for the existing per-method grouping query.
