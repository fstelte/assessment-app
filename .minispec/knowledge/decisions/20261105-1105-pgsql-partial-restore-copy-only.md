---
type: decision
id: 20261105-1105-pgsql-partial-restore-copy-only
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

# PostgreSQL partial restore supports COPY data only and drops INSERT parsing

## Context

[[20261105-1100-pgsql-partial-restore-reads-copy-blocks]] makes the restore read
`COPY` data blocks. The old `INSERT` regex in `execute_partial_restore_pgsql` cuts a
statement short at a `;` inside a quoted value. Every backup the app makes,
manual or scheduled, uses `COPY`. `INSERT`-style data only appears in a dump
made by hand with `pg_dump --inserts`.

## Options Considered

- **COPY only, remove the INSERT parsing (chosen).**
- COPY first, then fall back to INSERT with proper statement splitting: rejected.
  It adds a second restore path for a format the app never writes, and the
  existing splitter `_split_sql_statements` lives in `bia/utils.py`, so using it
  would cross a module boundary (constitution principle I).
- COPY, and keep the INSERT path unchanged: rejected because it keeps a known bug.

## Decision

- `execute_partial_restore_pgsql` restores only from `COPY ... FROM stdin;` blocks.
- A selected table with no `COPY` block gets status `skipped` and the message
  "Backup contains no data for this table.", which replaces "No INSERT
  statements found for this table." Like the other per-table result messages,
  it's stored as a plain English string.
- `_make_pgsql_backup_gz` in the tests writes real pg_dump `COPY` output: a
  `CREATE TABLE`, then `COPY public.<t> (cols) FROM stdin;`, tab-separated rows,
  and `\.`.
- `inspect_pgsql_backup` keeps counting `INSERT` lines. It only produces row
  estimates and changing it is out of scope.

## Consequences

### Positive
- ✅ One restore path that matches what the app produces.
- ✅ The `;` bug is gone.
- ✅ The tests use realistic dumps, which closes the gap that hid this bug.

### Negative
- ⚠️ A hand-made `--inserts` dump restores nothing. It now gets a clear message
  per table instead of a misleading one.
- ⚠️ The inspect step can still estimate rows for an `--inserts` dump that the
  restore step then can't load. This is rare and accepted.

## Related Decisions

- [[20261105-1100-pgsql-partial-restore-reads-copy-blocks]]
