---
feature: 20261105-104649-description-when-importing
status: planned
created: 2026-11-05
decisions:
  - 20261105-1100-pgsql-partial-restore-reads-copy-blocks
  - 20261105-1105-pgsql-partial-restore-copy-only
  - 20261105-1110-pgsql-partial-restore-advance-sequences
---

# PostgreSQL Partial Restore Reads COPY Data: Design

## Overview

Partial restore of a PostgreSQL backup (`.sql.gz` / `.sql.gz.enc`) ends with
the status **partial**, and every selected table reports
"No INSERT statements found for this table." Nothing is restored.

**Root cause.** Both backup paths run `pg_dump --format=plain`:

- the manual backup, `create_postgres_backup` in
  `scaffold/apps/admin/backup_utils.py`
- the scheduled backup, `docker/backup-db.sh`

By default, pg_dump writes table data as `COPY <t> (cols) FROM stdin;` blocks,
not as `INSERT` statements. `inspect_pgsql_backup` reads these blocks, so the
preview shows correct row counts. `execute_partial_restore_pgsql` only matches
`INSERT INTO ... VALUES (...);`, so it finds no data for any table.

The test fixture `_make_pgsql_backup_gz` builds its dump from `INSERT` lines.
The only test of the restore step, `TestPgsqlRestoreIdempotence`, runs against
SQLite and accepts any status. That's how the bug got through.

**The fix:**

- The restore step reads `COPY` blocks and loads each one through a temporary
  table using psycopg 3's copy API.
- Each table is restored inside its own savepoint, so one failure doesn't stop
  the rest.
- After a table restores rows, its sequence is moved forward.
- The `INSERT` parsing is removed, which also removes a bug where a `;` inside
  a quoted value cut a statement short.

## User Stories

- As an admin, I want to partially restore selected tables from a PostgreSQL
  backup made by the app (manual or scheduled) so that I can recover lost data
  without a full restore.
- As an admin, I want rows that already exist to be skipped and counted, not
  duplicated or failing, so that I can run a restore safely on a live database.
- As an admin, I want the app to keep working normally after a restore, with no
  duplicate-key errors on new records, so that a restore doesn't break things
  later.
- As an admin, I want a clear result for each table, so that one problem table
  doesn't hide or block the restore of the others.

### Acceptance scenarios

1. **Given** a Postgres backup made by the app and an empty target table,
   **when** the admin restores that table, **then** its status is `restored`,
   `restored_row_count` equals the number of rows in the backup, and the overall
   run status is `completed`.
2. **Given** the same restore run a second time, **then** the table's status is
   `skipped` and `skipped_conflict_count` equals the number of rows in the
   backup.
3. **Given** backup rows that contain tabs, newlines, backslashes, `;` and
   `NULL` (`\N`), **when** they are restored, **then** the stored values match
   the original values exactly.
4. **Given** a selected table that has no `COPY` block in the dump, **then**
   its status is `skipped` with the message "Backup contains no data for this
   table."
5. **Given** two selected tables where the first fails, for example on a
   constraint violation, **then** the first is `failed`, the second is
   `restored`, and the run status is `partial`.
6. **Given** a restored table with a serial or identity primary key whose
   highest restored id is above the live sequence value, **when** the app then
   inserts a new row, **then** the insert succeeds.
7. **Given** a parent and a child table linked by a foreign key, selected
   child first, **when** both are restored into empty tables, **then** both
   are `restored`.
8. **Given** a restore where every selected table is `skipped`, **then** the
   overall run status is `completed`.

## Components

All changes are in `scaffold/apps/admin/backup_utils.py`. No new files or
modules.

### `_extract_copy_blocks(sql_text) -> dict[str, CopyBlock]` (new, private)

A pure function with no database access. It scans the plain pg_dump text for

```
COPY [public.]<table> (<col>, ...) FROM stdin;
<data lines>
\.
```

and returns, for each lowercase table name, the column list (with identifier
quotes removed) and the raw data text between the header line and the `\.`
line.

- The raw data is passed through exactly as it is. Postgres parses it, so there
  is no unescaping in Python.
- The block ends at the first line that is exactly `\.`, never a line that
  only starts with it.

### `execute_partial_restore_pgsql(data, selected_tables, engine)` (rewritten)

The signature and return type stay the same.

**Restore order:** the selected tables are restored parents first, so a
foreign-key child is never inserted before its parent. To do that:

1. Get the live schema's foreign-key order from
   `sa_inspect(engine).get_sorted_table_and_fkc_names()`.
2. Restore the selected tables in that order.
3. Put any selected table missing from that order at the end, in the order it
   was selected.

The returned dict is keyed by table name, so the result order doesn't change
behaviour.

For each table, in that order:

1. If the table has no `COPY` block, mark it `skipped` with the message
   "Backup contains no data for this table."
2. Otherwise, open a savepoint (`conn.begin_nested()`) and:
   1. `CREATE TEMP TABLE _pr_<t> (LIKE <t> INCLUDING DEFAULTS) ON COMMIT DROP`
   2. Stream the block into it through the raw psycopg 3 cursor:
      `with cur.copy("COPY _pr_<t> (cols) FROM STDIN") as cp: cp.write(block)`
   3. Run
      `INSERT INTO <t> (cols) SELECT cols FROM _pr_<t> ON CONFLICT DO NOTHING`.
      Restored = the rowcount.
      Skipped = the number of rows in the temp table minus restored.
   4. If restored > 0, move the sequence forward (see below).
   5. `DROP TABLE _pr_<t>` to free it before the next table.
3. On an exception, roll back the savepoint and mark the table `failed` with
   the exception text. Continue with the next table.
4. The status is `restored` if restored > 0, otherwise `skipped`. This is
   unchanged.

Table and column names come from the backup and are inserted into SQL. They
are checked with the existing `_validate_table_name` (columns use the same
identifier rule) and quoted. Tables are also limited to `selected_tables`,
which has already been validated.

### Moving the sequence forward (inline, or a small private helper)

1. Find the table's primary key columns.
2. If there is exactly one, run
   `SELECT pg_get_serial_sequence('<t>', '<pk>')`.
3. If that returns a sequence, run
   `SELECT setval(seq, GREATEST((SELECT MAX(<pk>) FROM <t>), (SELECT last_value FROM seq)))`.

The sequence never moves backwards. Tables without a single serial or identity
primary key are skipped.

### `orchestrate_partial_restore` overall status (one-line change)

When every result is `skipped` (`statuses == {"skipped"}`), the overall status
is now `completed`, not `partial`. Restoring rows that all exist already is a
successful no-op, not a partial failure.

### `docs/deployment.md` §Partial Restore (operational docs, principle V)

The section now states:

- PostgreSQL backups made by the app (manual and scheduled) can be partially
  restored.
- Rows that already exist are skipped.
- Selected tables are restored parents first.
- Sequences are moved forward after a restore.
- Hand-made `--inserts` dumps aren't supported, so use Full Restore for those.

### Removed

- The `INSERT INTO ... VALUES` regex and the per-statement
  `ON CONFLICT DO NOTHING` loop in `execute_partial_restore_pgsql`.

### Unchanged

- `inspect_pgsql_backup` keeps its `INSERT`/`COPY`/`CREATE` counting for
  estimates.
- The SQLite partial restore.
- Both backup paths.
- Full restore (`docker/restore/restore_db.py`).
- Routes, templates and translations.
- `orchestrate_partial_restore`, apart from the all-skipped status rule above.

## Data Model

No schema changes and no migration. `TableRestoreResult` and
`PartialRestoreRun` are unchanged. Only the text of one `error_message` value
changes.

## API / Interface

- `execute_partial_restore_pgsql` keeps the same signature and return shape.
- `_extract_copy_blocks` is a new private helper.

## Tests (`tests/test_admin_partial_restore.py`)

- **`_make_pgsql_backup_gz`** builds real pg_dump output: a `CREATE TABLE`,
  then `COPY public.<t> (cols) FROM stdin;`, tab-separated rows using `\N` for
  NULL and pg_dump escapes, and a `\.` line. The existing inspect tests are
  updated to use it. The inspect step already counts `COPY` rows.
- **Pure tests of `_extract_copy_blocks`** (no database needed):
  - several tables
  - quoted identifiers
  - a `public.` schema prefix
  - an empty block
  - a data line that starts with `\.` but isn't exactly `\.`
  - a `;` inside a value
- **Postgres integration tests**, skipped unless a Postgres URL is set (for
  example `TEST_POSTGRES_URL`). These cover acceptance scenarios 1–7.
- **Scenario 8** is tested without Postgres, through `orchestrate_partial_restore`.
- **Remove `TestPgsqlRestoreIdempotence`.** It runs a Postgres-only code path
  against SQLite and accepts every status. The Postgres integration tests
  replace it.

## Operational documentation

Constitution principle V: partial restore of PostgreSQL backups now works for
backups made by the app. If the admin or backup docs mention a limitation or
the old message, update them in the same change. Nothing in the backup or
restore runbooks needs to change otherwise.

## Out of scope

- Changing the backup format (`--inserts`).
- Restoring hand-made `INSERT`-style dumps.
- Translating per-table result messages.
- Changing inspect estimates.
- The SQLite partial restore.

## Open Questions

- ~~**Overall status when every table is skipped.**~~ **Resolved (2026-11-05):**
  in `orchestrate_partial_restore`, a run where every table is `skipped` now
  gets the status `completed`, not `partial`.
- ~~**Postgres in CI.**~~ **Resolved (2026-11-05):** the integration tests run
  locally only. They are skipped unless `TEST_POSTGRES_URL` is set, and CI is
  unchanged.
- **Raw cursor access.** Get the psycopg 3 cursor through
  `conn.connection.driver_connection.cursor()` inside the SQLAlchemy
  transaction, so the `COPY` takes part in the savepoint. Confirm this during
  implementation.
