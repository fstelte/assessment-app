---
type: decision
id: 20261119-1826-architecture-overview-migration-keep-current
date: 2026-11-19
status: accepted
supersedes: null
superseded_by: null
impacts:
  - migrations/versions/*
  - scaffold/apps/ssp/models.py
tags: [ssp, architecture-overview, migration]
participants: [Ferry Stelte, Claude]
---

# Architecture overview migration: keep only the current version, drop version numbers

Follows from `20261119-1825-architecture-overview-flat-file-list`.

## Context

Under the flat-list model every stored row is shown. Existing SSPs may hold
several versions, where only the highest one was visible and the rest were
history. Without a data migration, those old versions would suddenly appear.

## Options Considered

### Option 1: Keep only the current version
- ✅ Every SSP looks the same right after the upgrade
- ❌ Old history bytes are deleted (the audit log keeps the upload events)

### Option 2: Keep everything
- ✅ No data loss
- ❌ Old diagrams pop up as extra files and must be cleaned up by hand

### Option 3: Archive flag
- ✅ No data loss and no visual change
- ❌ An extra column that every query must respect, for data nobody can reach in the UI

## Decision

Option 1. The Alembic migration:
1. Deletes every `ssp_architecture_overview_versions` row that is not the
   highest `version_number` for its `ssp_id`.
2. Drops the `uq_ssp_architecture_overview_version` constraint and the
   `version_number` column (in `batch_alter_table`, as other migrations do).

Files are listed by `uploaded_at` ascending, then `id`. The table name and the
`image_data` column stay, to keep the migration small. The downgrade
re-adds `version_number`, numbered per SSP by `uploaded_at`; deleted history
is not restored.

*Amended by 20261120-0900:* the upgrade logs how many rows were pruned
(CHK001). Operators are told to back up first (CHK002). The test fixture is
fixed as A:{1,2,3}, B:{1}, C:{} (CHK016).

## Consequences

### Positive
- ✅ No visible change on upgrade
- ✅ No leftover column without meaning

### Negative
- ❌ Historical versions are permanently removed on upgrade
- ❌ The table name `..._versions` no longer describes its contents (accepted to keep the change small)
