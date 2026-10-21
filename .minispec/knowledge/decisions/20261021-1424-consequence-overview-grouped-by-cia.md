---
type: decision
id: 20261021-1424-consequence-overview-grouped-by-cia
date: 2026-10-21
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/bia/routes.py
  - scaffold/apps/bia/templates/bia/manage_item_consequences.html
tags: [bia, consequences, ui]
participants: [Ferry Stelte, Claude]
---

# Consequence overview shows one row per CIA property per component

## Context

Users want the consequence overview to show the CIA properties, with the
category labels shown inside those rows, instead of one row per category.

## Options Considered

### Option 1: One row per consequence record
CIA property first, labels as chips. A component can still show several
Confidentiality rows.
- ✅ Direct 1:1 mapping, so edit and delete stay simple.
- ❌ Still several rows per property when a user records more than one.

### Option 2: One row per CIA property per component (chosen)
Group by component and security property in the display layer. Each component
gets at most three rows (C, I, A). The labels are the union of all underlying
consequences' categories, and the impacts are the highest worst-case and
realistic values, which is the same rule `_summary_impacts` uses.
- ✅ Matches what users expect: a CIA view with labels inside it.
- ✅ No data constraint, so legacy one-row-per-category data displays
  correctly without a migration.
- ❌ A grouped row can hide several records, so edit and delete need a way to
  reach each one.

### Option 3: Enforce at most one consequence per CIA property
- ❌ Needs a uniqueness rule and a merge migration for existing data, and stops
  users recording different scenarios per property.

## Decision

Group in the display layer only. The data model allows several consequences
per property.

## Consequences

- A grouping helper builds `(component, property) -> rows` with the merged
  labels and max impacts.
- Each grouped row must still give access to its underlying records for edit
  and delete (see the follow-up decision on interaction).
