---
type: decision
id: 20261106-1635-partial-restore-report-fk-counts-as-fields
date: 2026-11-06
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/admin/backup_utils.py
  - scaffold/apps/admin/routes.py
  - scaffold/apps/admin/templates/admin/partial_restore_results.html
  - scaffold/translations/en.json
  - scaffold/translations/nl.json
  - docs/deployment.md
tags: [admin, backup, restore, ui, i18n]
participants: [Ferry Stelte, Claude]
---

# Report cleared references and missing-parent skips as separate counts

## Context

[[20261106-1626-pgsql-partial-restore-dangling-fk-handling]] creates two new
outcomes per table: foreign-key references set to NULL (parent table not
restored), and rows skipped because their parent row is missing. The results
page currently shows restored rows, conflict-skipped rows and one message
column.

## Options Considered

- **Two new fields with their own columns and localized labels (chosen).**
- Add both counts to `skipped_conflict_count` and explain them in the message:
  rejected. One column would then mix conflicts and orphans, and the message
  isn't localized.
- Hybrid, with only a missing-parent column: rejected in favour of making
  both outcomes equally easy to see.

## Decision

- `TableRestoreResult` gets `cleared_reference_count: int = 0` and
  `skipped_missing_parent_count: int = 0`. They have defaults, so
  `save_run_state`/`load_run_state` (`asdict` / `**r`) keep working, and older
  run-state files still load.
- `skipped_conflict_count` keeps its meaning: rows skipped by
  `ON CONFLICT DO NOTHING`. It equals `total - restored - skipped_missing_parent`.
- `partial_restore_results.html` gets two right-aligned columns.
  New keys: `admin.backup.partial_restore.results.cleared_references` and
  `admin.backup.partial_restore.results.skipped_missing_parent`, in both
  `en.json` and `nl.json`.
- The `partial_restore_execute` audit event adds
  `cleared_reference_counts` and `skipped_missing_parent_counts` next to
  `skipped_conflict_counts`.
- A table where every row was skipped (0 restored) keeps status `skipped`, as
  it does today.
- **Counting:** `cleared_reference_count` counts per reference (a row with two
  cleared FKs counts 2). Every COPY row lands in exactly one bucket:
  `total = restored + skipped_conflict + skipped_missing_parent`.
- **Run status:** unchanged. Cleared or skipped rows don't make a run
  `partial`. A run with only `restored`/`skipped` tables is `completed`.
- No extra message text per table. The counts are the explanation.
- The audit event records totals per table, not which FK columns were
  cleared. That detail can be worked out from the backup and the live
  database, and would make the event much larger.
- The SQLite path leaves both fields at 0.

## Consequences

### Positive
- ✅ The admin can see per table exactly where data was cut back.
- ✅ The audit trail records it (constitution principle II).

### Negative
- ⚠️ The results table is wider: 7 columns.

## Related Decisions

- [[20261106-1626-pgsql-partial-restore-dangling-fk-handling]]
