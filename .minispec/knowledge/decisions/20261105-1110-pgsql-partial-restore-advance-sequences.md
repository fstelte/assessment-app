---
type: decision
id: 20261105-1110-pgsql-partial-restore-advance-sequences
date: 2026-11-05
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/admin/backup_utils.py
  - tests/test_admin_partial_restore.py
tags: [admin, backup, restore, postgresql, bugfix]
participants: [Ferry Stelte, Claude]
---

# Advance sequences after a PostgreSQL partial restore and isolate tables with savepoints

## Context

Once [[20261105-1100-pgsql-partial-restore-reads-copy-blocks]] makes partial
restore insert rows, two problems show up that never mattered before:

1. **Sequences fall behind.** pg_dump keeps primary-key values in the `COPY`
   data. The matching sequence values are separate
   `SELECT pg_catalog.setval(...)` lines, which the restore doesn't run. If a
   restored id is above the live sequence value, a later insert by the app
   fails with a duplicate-key error.
2. **One failure aborts the rest.** All tables are restored inside one
   `engine.begin()` transaction. In Postgres, after one statement fails,
   every later statement in that transaction fails as well.

## Options Considered

- **Move each restored table's sequence past its highest id, read from the
  live database (chosen).**
- Run the dump's `setval` lines for restored tables: rejected. The backup's
  value can be lower than the live value, which causes collisions the other way
  round.
- Leave sequences alone and document it: rejected. It causes failures later
  that are hard to trace, against constitution principle II (least surprise).

## Decision

- Each table's restore runs inside its own savepoint (`conn.begin_nested()`).
  A failure rolls back only that table, marks it `failed`, and the restore
  continues with the next table.
- After a table restores more than 0 rows, find its sequence with
  `pg_get_serial_sequence('<table>', '<pk column>')`. If there is one, set it to
  `GREATEST(MAX(pk), current last_value)`, so the sequence never moves
  backwards.
- Tables without a single-column serial or identity primary key are left
  alone.

## Consequences

### Positive
- ✅ The app can keep inserting rows into restored tables after the restore.
- ✅ The result shows each table's own outcome, so one bad table doesn't fail
  the rest.

### Negative
- ⚠️ One extra query per restored table. This doesn't matter at the scale of an
  admin restore.
- ⚠️ Tables with composite or non-serial keys get no sequence handling. They
  don't need it.

## Related Decisions

- [[20261105-1100-pgsql-partial-restore-reads-copy-blocks]]
- [[20261105-1105-pgsql-partial-restore-copy-only]]
