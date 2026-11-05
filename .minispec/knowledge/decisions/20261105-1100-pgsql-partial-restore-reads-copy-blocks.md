---
type: decision
id: 20261105-1100-pgsql-partial-restore-reads-copy-blocks
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

# PostgreSQL partial restore reads COPY data blocks, not only INSERT statements

## Context

Partial restore of a PostgreSQL backup (`.sql.gz`, `.sql.gz.enc`) ended as
partial, and every selected table said "No INSERT statements found for this
table."

Both the manual backup (`create_postgres_backup`) and the scheduled backup
(`docker/backup-db.sh`) run `pg_dump --format=plain`. By default, pg_dump writes
table data as `COPY <table> (...) FROM stdin;` followed by tab-separated rows
and ends each block with `\.`. `inspect_pgsql_backup` already counts these
blocks, so the preview showed correct row counts. `execute_partial_restore_pgsql`
only matched `INSERT INTO ... VALUES (...);`, so it found nothing to restore.
The test fixture builds its dump from INSERT lines, so the tests never saw real
pg_dump output.

The INSERT pattern `VALUES\s*\([^;]+\);` also cuts a statement short at a `;`
inside a quoted value.

## Options Considered

- **Make the restore read COPY blocks (chosen).** Existing backups become
  restorable and the backup format stays the same.
- Switch backups to `pg_dump --inserts`: rejected. Existing backups would stay
  unrestorable, dumps get larger, full restores get slower, the change would be
  needed in both the Python and the shell backup paths, and the `;` bug remains.
- Both: rejected. Once the restore reads COPY blocks, changing the backup format
  adds nothing.

## Decision

- `execute_partial_restore_pgsql` pulls the `COPY ... FROM stdin;` data block
  for each selected table out of the dump.
- For each table:
  1. Create a temporary table with the same structure as the target.
  2. Load the block's data into it with psycopg 3's `cursor.copy()`, so
     Postgres parses escapes, `\N` nulls and embedded tabs and newlines.
  3. Run `INSERT INTO target (cols) SELECT cols FROM tmp ON CONFLICT DO NOTHING`.
  4. Restored = the INSERT's rowcount. Skipped = rows in the block minus restored.
- This keeps the existing skip-existing behaviour.

## Consequences

### Positive
- ✅ Every existing PostgreSQL backup can be partially restored.
- ✅ Postgres parses the COPY data, so there's no hand-written parser for
  escapes and nulls.
- ✅ Restored and skipped counts are exact per table, not per statement.

### Negative
- ⚠️ The restore depends on psycopg 3's copy API. The project already requires
  psycopg 3.
- ⚠️ The code needs access to the raw DBAPI cursor, not only SQLAlchemy `text()`.

## Related Decisions

- None.
