---
type: decision
id: 20261118-1455-ssp-interconnections-reconciled-from-bia
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/ssp/models.py
  - scaffold/apps/ssp/services.py
  - scaffold/apps/ssp/routes.py
  - scaffold/apps/ssp/templates/ssp/interconnections.html
  - scaffold/apps/ssp/templates/ssp/edit_interconnection.html
  - scaffold/apps/ssp/templates/ssp/view.html
  - migrations/versions/*
tags: [ssp, bia, interconnections, sync, data-model]
participants: [Ferry Stelte, Claude]
---

# SSP interconnections: BIA interfaces own the system names, the SSP owns the details

## Context

The BIA records a free-text `ContextScope.interfaces` field. `seed_interconnections`
copies it into `SSPInterconnection` rows once, when the SSP is created (split on
newlines and `;`). After that the two drift: BIA edits never reach the SSP. The
SSP rows also carry NIST SP 800-18 details the BIA does not have (agreement
type, data direction, security contact, notes).

## Options Considered

### Option 1: BIA names + SSP details, reconciled automatically
- ✅ BIA is the single source of *which* systems are interconnected
- ✅ Keeps the SSP-only interconnection details
- ❌ Needs a `source` column and a reconcile step

### Option 2: Pure live list from BIA
- ✅ Simplest, no drift possible
- ❌ Loses agreement/direction/contact data; drops existing CRUD

### Option 3: Manual "Sync from BIA" button
- ✅ Explicit, minimal change
- ❌ Drift persists until someone clicks

## Decision

We chose **Option 1**.

- New column `SSPInterconnection.source` (`bia` | `manual`, non-native enum,
  default `manual`). The migration backfills `bia` for rows whose normalised
  name (trimmed, case-insensitive) appears in the scope's parsed `interfaces`.
  All others are set to `manual`.
- `reconcile_interconnections(ssp)` in `ssp/services.py` uses the same parsing
  as `seed_interconnections`, which it replaces. It is idempotent:
  - adds a `bia` row for every parsed BIA name with no row yet (normalised match);
  - converts a matching `manual` row to `bia` instead of adding a duplicate;
  - never deletes. A `bia` row whose name is no longer in the BIA is shown with a
    "no longer in BIA" badge, so the user can delete it on purpose. A live `bia`
    row cannot be deleted (amended by 20261118-1530, CHK002/CHK003);
  - `manual` rows are never flagged.
- It runs on `ssp.create`, `ssp.view`, `ssp.interconnections`, `ssp.edit`
  (the boundary helper) and the print/PDF export. It commits only when a row
  was added.
- On `bia` rows, `system_name` is read-only in the edit form. The server
  ignores any submitted value. Users can still add manual interconnections.

## Consequences

### Positive
- ✅ Interfaces added in the BIA show up in the SSP without anyone acting
- ✅ No interconnection detail is lost automatically

### Negative
- ❌ A GET can write (adding rows). This is acceptable: the step is idempotent
  and follows the existing "re-sync on view" pattern in the risk module.
- ❌ Renaming an interface in the BIA produces a new row plus a flagged stale
  row, and the details have to be moved over by hand.
