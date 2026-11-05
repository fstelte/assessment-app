---
feature: 20261105-104649-description-when-importing
status: planned
created: 2026-11-05
chunk_size: adaptive
total_tasks: 4
estimated_lines: 255
---

# PostgreSQL Partial Restore Reads COPY Data: Tasks

## Overview

Partial restore of PostgreSQL backups only read `INSERT` statements, but
pg_dump writes `COPY` blocks, so every table came back "No INSERT statements
found". These tasks change the restore to:

- load `COPY` blocks through a temporary table (psycopg 3 `cursor.copy()`)
- give each table its own savepoint
- move sequences forward after rows are restored

They also make the test fixture use real pg_dump output, and make a run where
every table is skipped count as `completed`.

See [design.md](design.md) and the decisions
[[20261105-1100-pgsql-partial-restore-reads-copy-blocks]],
[[20261105-1105-pgsql-partial-restore-copy-only]] and
[[20261105-1110-pgsql-partial-restore-advance-sequences]].

## Task List

### Foundation

#### Task 1: Parse COPY blocks and make the test fixture realistic
- **Estimate:** ~80 lines
- **Files:** `scaffold/apps/admin/backup_utils.py`, `tests/test_admin_partial_restore.py`
- **Description:**
  - Add the pure function `_extract_copy_blocks(sql_text)`. It returns
    `{table_lower: CopyBlock(columns, data)}` for each
    `COPY [public.]<t> (cols) FROM stdin;` block.
  - Column names have their identifier quotes removed.
  - `data` is the raw text up to, but not including, the first line that is
    exactly `\.`.
  - Rewrite `_make_pgsql_backup_gz` so it writes real pg_dump output: a
    `CREATE TABLE`, then `COPY public.<t> (cols) FROM stdin;`, tab-separated
    rows using `\N` for NULL, and `\.`. Its input becomes rows instead of
    `INSERT` strings.
  - Update the callers in the existing inspect tests.
- **Depends on:** None
- **Acceptance:** Pure tests (no database) cover:
  - several tables
  - quoted identifiers
  - the `public.` prefix
  - an empty block
  - a data line that starts with `\.` but isn't exactly `\.`
  - a `;` and an escaped tab or newline inside a value, kept unchanged
  - a table with no block, which is missing from the result

  The inspect tests still pass, and `inspect_pgsql_backup` row counts come
  from the `COPY` blocks.
- **Evidence:** `pytest tests/test_admin_partial_restore.py` passes.

### Core Implementation

#### Task 2: Rewrite `execute_partial_restore_pgsql` to restore from COPY blocks
- **Estimate:** ~120 lines
- **Files:** `scaffold/apps/admin/backup_utils.py`, `tests/test_admin_partial_restore.py`
- **Description:** Keep the signature and return shape.

  First, sort the selected tables parents first:
  1. Get the live foreign-key order from
     `sa_inspect(engine).get_sorted_table_and_fkc_names()`.
  2. Restore the selected tables in that order.
  3. Put any selected table missing from that order at the end, in the order
     it was selected.

  Then, for each table in that order:
  1. If it has no block, mark it `skipped` with
     "Backup contains no data for this table."
  2. Otherwise, inside `conn.begin_nested()`:
     1. `CREATE TEMP TABLE _pr_<t> (LIKE <t> INCLUDING DEFAULTS) ON COMMIT DROP`
     2. Load the data with the psycopg 3 cursor (through
        `conn.connection.driver_connection`):
        `cur.copy("COPY _pr_<t> (cols) FROM STDIN")` and `write(data)`.
     3. Run
        `INSERT INTO <t> (cols) SELECT cols FROM _pr_<t> ON CONFLICT DO NOTHING`.
        Restored = the rowcount. Skipped = the temp table's row count minus
        restored.
     4. `DROP TABLE _pr_<t>`.
  3. On an exception, roll back the savepoint, mark the table `failed`, and
     continue with the next table.

  Also:
  - Check table and column names with the `_validate_table_name` rule, then
    quote them.
  - Remove the `INSERT` regex and the per-statement loop.
  - Remove `TestPgsqlRestoreIdempotence`.
  - Add the `TEST_POSTGRES_URL` skip marker and a fixture that creates and
    drops the test tables.
- **Depends on:** Task 1
- **Acceptance:** Postgres integration tests for design scenarios 1–5 and 7:
  1. Restore into an empty table → `restored`, with the correct count.
  2. Re-run → `skipped`, with the correct skipped count.
  3. Tabs, newlines, backslashes, `;` and NULL come back exactly as they were.
  4. A table with no data block → `skipped` with the new message.
  5. One table fails (constraint violation) → that table is `failed`, the
     other is `restored`.
  7. Parent and child linked by a foreign key, selected child first → both
     are `restored`.
- **Evidence:** Run against a local Postgres:
  `TEST_POSTGRES_URL=... pytest tests/test_admin_partial_restore.py` passes.
  Without the variable, the Postgres tests are skipped and the rest pass.

#### Task 3: Move sequences forward after a restore
- **Estimate:** ~40 lines
- **Files:** `scaffold/apps/admin/backup_utils.py`, `tests/test_admin_partial_restore.py`
- **Description:** After a table restores more than 0 rows, inside its
  savepoint:
  1. Find the primary key columns.
  2. If there is exactly one, run `pg_get_serial_sequence('<t>', '<pk>')`.
  3. If that returns a sequence, run
     `setval(seq, GREATEST((SELECT MAX(pk) FROM t), (SELECT last_value FROM seq)))`.

  Tables without a single serial or identity primary key are skipped.
- **Depends on:** Task 2
- **Acceptance:** Postgres integration tests:
  - Scenario 6: restore ids above the live sequence, then
    `INSERT ... DEFAULT VALUES` succeeds.
  - The sequence is never lowered when the live value is already higher.
  - A table without a serial key restores without error.
- **Evidence:** Same local Postgres pytest run passes.

### Integration & Polish

#### Task 4: Treat an all-skipped run as completed, and update the docs [P]
- **Estimate:** ~15 lines
- **Parallel:** Can run with Task 3
- **Files:** `scaffold/apps/admin/backup_utils.py`, `tests/test_admin_partial_restore.py`, `docs/deployment.md`
- **Description:**
  - In `orchestrate_partial_restore`, treat `statuses == {"skipped"}` as
    `completed`.
  - Update the Partial Restore section of `docs/deployment.md`. Postgres
    backups made by the app (manual and scheduled) are supported. Rows that
    already exist are skipped. Selected tables are restored parents first.
    Sequences are moved forward after a restore. Hand-made `--inserts` dumps are not supported, so use Full Restore for
    those.
- **Depends on:** Task 2
- **Acceptance:** A test (no database, using a stubbed or SQLite path) shows
  that a run with only `skipped` results has overall status `completed`. The
  docs section reflects the new behaviour.
- **Evidence:** `pytest tests/test_admin_partial_restore.py` passes.

## Notes

- **Postgres tests run locally only.** They are skipped unless
  `TEST_POSTGRES_URL` is set. CI only runs the pure parser tests and the status
  test. To mark Task 2 or 3 done, run the tests against a local Postgres and
  record the output.
- `COPY` data is passed to Postgres unchanged, so there is no unescaping in
  Python.
- `inspect_pgsql_backup` now counts `COPY` rows with `_extract_copy_blocks`
  (done in Task 1 after review, which fixed rows being credited to the wrong
  table).
- **Deferred:** restoring `--inserts` dumps, Postgres in CI, translating
  per-table result messages.
- After the code changes, run `graphify update .`.

## Progress
- [x] Task 1: Parse COPY blocks and make the test fixture realistic
- [ ] Task 2: Rewrite `execute_partial_restore_pgsql` to restore from COPY blocks
  - Implemented (2026-11-05). Waiting for the local `TEST_POSTGRES_URL` test run
    before this task can be marked done.
- [ ] Task 3: Move sequences forward after a restore
  - Implemented (2026-11-05). Waiting for the local `TEST_POSTGRES_URL` test run
    before this task can be marked done.
- [ ] Task 4: Treat an all-skipped run as completed, and update the docs
