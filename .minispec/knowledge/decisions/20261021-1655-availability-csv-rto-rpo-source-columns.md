---
type: decision
id: 20261021-1655-availability-csv-rto-rpo-source-columns
date: 2026-10-21
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/bia/utils.py
tags: [bia, export, csv, rto, rpo]
participants: [Ferry Stelte, Claude]
---

# Availability CSV adds RTO/RPO source and effective columns

## Context

The "manually configured" status must also be visible in the CSV export
(`*_availability_requirements.csv`). That CSV is also an import format, read by
column name.

## Options Considered

### Option 1: Keep stored text, add source + effective columns (chosen)
- ✅ Import round-trips stay lossless: RTO/RPO columns are still the stored text.
- ✅ Readers see the real value and its source without looking up tiers.
- ❌ Four extra columns.

### Option 2: Effective value in the RTO/RPO columns + source columns
- ❌ Re-importing turns tier-derived values into stored manual text.

### Option 3: Source columns only
- ❌ Readers of a `tier` row must look up the goal elsewhere.

## Decision

We chose **Option 1**. Append `RTO Source`, `Effective RTO`, `RPO Source` and
`Effective RPO` after the existing columns. Source values are `tier`,
`manual`, `free text` or `not set`, untranslated, like the existing headers.
The CSV import ignores these columns. The SQL export is unchanged because it
is a raw table dump.

Refined by [[20261021-1730-rto-rpo-prefill-checklist-gap-resolutions]]: the CSV
writes one row per component, including components without an availability
record. The import skips rows whose four stored columns are all empty.

## Related Decisions

- [[20261021-1655-tier-goal-prefills-component-rto-rpo]]
- [[20261021-1730-rto-rpo-prefill-checklist-gap-resolutions]]
