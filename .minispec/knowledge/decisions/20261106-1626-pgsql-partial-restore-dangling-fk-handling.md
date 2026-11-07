---
type: decision
id: 20261106-1626-pgsql-partial-restore-dangling-fk-handling
date: 2026-11-06
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/admin/backup_utils.py
  - tests/test_admin_partial_restore.py
tags: [admin, backup, restore, postgresql, bugfix, foreign-key]
participants: [Ferry Stelte, Claude]
---

# PostgreSQL partial restore clears or skips rows whose foreign-key parent is missing

## Context

A partial restore with the default selection fails on about 25 tables with
`psycopg.errors.ForeignKeyViolation`. The default selection leaves out the
identity group (`users`, `roles`, …), but many domain tables point to
`users.id`: `audit_logs.actor_id`, `bia_context_scope.author_id`,
`risk_items.treatment_owner_id`, `csa_assessments.created_by_id`, threat and
SSP owner and creator columns. If one backup row points to a user id that isn't
in the live database, the table's single `INSERT … SELECT` fails as a whole.
Each table that depends on it then fails too, because none of its parent rows
arrived.

Most of these user foreign keys are nullable, and many already use
`ondelete="SET NULL"`. The app already treats "user is gone" as
"set the field to NULL".

## Options Considered

- **A2: set to NULL only where the parent table is not part of this restore;
  otherwise skip the row (chosen).**
- A1: set any nullable foreign key with a missing parent to NULL: rejected.
  It also clears links inside the restored set, such as a component's context
  scope, which turns real data damage into silent orphans.
- B: skip every row that has a missing parent: rejected. It drops most of the
  BIA, risk and threat data just because the author is missing.
- C: include the identity group automatically: rejected. It restores accounts
  and roles the admin didn't choose, and colliding ids can link records to the
  wrong person.

## Decision

In `execute_partial_restore_pgsql`, after loading the COPY data into the temp
table and before the `INSERT`, go through every foreign key of the target table
(`insp.get_foreign_keys`) and find the rows whose referenced row is missing from
the live table (`NOT EXISTS`):

- **Parent table not selected for this restore, and the column is nullable**
  → `UPDATE tmp SET col = NULL` for those rows. They count as *references cleared*.
- **Every other case**, meaning the parent table is selected, or the column is
  `NOT NULL`, or the key is composite and can't be fully set to NULL
  → `DELETE` those rows from the temp table. They count as *skipped, missing
  parent*.

Self-referencing foreign keys are checked against the live table plus the
temp table, so a parent and child in the same backup still restore together.

Refinements (2026-11-07, from the requirements checklist):

- **Fixed order:** (1) remove temp rows whose primary key already exists live,
  counted as conflicts; (2) delete the dangling rows for the non-clearable FKs,
  repeated until stable; (3) clear the dangling clearable FKs; (4) `INSERT`.
  A row is therefore never both skipped and cleared, and a rerun reports 0
  cleared.
- **"Selected"** means the effective set after the identity group is added
  automatically. **"Nullable"** is read from the live schema.
- A referenced table that is missing from the live schema counts as
  "parent missing".
- **FK cycles between two selected tables** are a known limitation (the rows
  of the first table are skipped). There are none in the current models.

The live table is queried after earlier tables in the same run have been
inserted. A parent table that restored first therefore counts as present, and
a parent table that failed leaves its children with skipped rows, not failures.

## Consequences

### Positive
- ✅ The default selection restores domain data without the identity group.
- ✅ One failed parent no longer fails every table below it. The child rows
  are reported as skipped.
- ✅ It works for every foreign key with no hard-coded table list, and it
  follows the `SET NULL` rule the models already use.

### Negative
- ⚠️ Owner and author fields come back empty when the user isn't present.
  The result reports this, so it isn't silent.
- ⚠️ A few extra queries per foreign key per table. This is fine for an admin
  operation.

## Related Decisions

- [[20261105-1100-pgsql-partial-restore-reads-copy-blocks]]
- [[20261105-1110-pgsql-partial-restore-advance-sequences]]
