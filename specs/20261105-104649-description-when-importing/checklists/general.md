---
type: checklist
domain: general
feature: 20261105-104649-description-when-importing
created: 2026-11-05
status: completed
---

# General Requirements Quality Checklist

**Purpose:** Check that the requirements for the PostgreSQL partial restore
`COPY` fix are complete, clear and consistent before implementation starts.
**Feature:** 20261105-104649-description-when-importing

## Completeness

- [x] CHK001 - Is the root cause stated and traced to code? [Completeness]
  - Resolved: design §Overview names both pg_dump call sites and the
    `INSERT`-only regex in `execute_partial_restore_pgsql`.
- [x] CHK002 - Does every acceptance scenario have a task and a test? [Coverage]
  - Resolved: scenarios 1–5 → Task 2, scenario 6 → Task 3, all-skipped
    status → Task 4.
- [x] CHK003 - Is the behaviour for a selected table with no `COPY` block
  defined? [Edge case]
  - Resolved: `skipped`, with "Backup contains no data for this table."
- [x] CHK004 - Is the restore order defined when the selected tables
  reference each other through foreign keys? [Gap]
  - Resolved: selected tables are restored parents first, using
    `get_sorted_table_and_fkc_names()`, and tables missing from that order go
    last. See design §Components (restore order), Task 2, and scenario 7.
- [x] CHK005 - Is it defined what happens to sequences after a restore? [Gap]
  - Resolved: decision 20261105-1110. The sequence is set to `GREATEST(MAX(pk), last_value)`.
- [x] CHK006 - Is it defined whether one table's failure affects the others? [Edge case]
  - Resolved: each table has its own savepoint (decision 20261105-1110).
- [x] CHK007 - Is the overall status when every table is skipped defined? [Clarity]
  - Resolved: `completed`. Decided 2026-11-05 and covered by Task 4.

## Clarity

- [x] CHK008 - Is it clear how the `COPY` data block ends? [Clarity]
  - Resolved: at the first line that is exactly `\.`. A data line that only
    starts with `\.` does not end it. Covered by a Task 1 test.
- [x] CHK009 - Is it clear that data is not unescaped in Python? [Clarity]
  - Resolved: the design and Task 1 both say the raw text goes to Postgres
    unchanged.
- [x] CHK010 - Is the way the `COPY` reaches the database specified? [Clarity]
  - Resolved: a psycopg 3 cursor obtained through
    `conn.connection.driver_connection`, inside the SQLAlchemy transaction.
    This still needs confirming during Task 2 (design open question).

## Consistency

- [x] CHK011 - Do the design, decisions and tasks use the same message text? [Consistency]
  - Resolved: "Backup contains no data for this table." appears the same in
    decision 20261105-1105, the design and Task 2.
- [x] CHK012 - Does design §Components list every code change made by the tasks? [Consistency]
  - Resolved: design §Components now has sections for the
    `orchestrate_partial_restore` all-skipped status and for
    `docs/deployment.md`, and acceptance scenario 8 covers the status.
- [x] CHK013 - Do the tasks match the decision to use `COPY` only? [Consistency]
  - Resolved: Task 2 removes the `INSERT` regex and leaves
    `inspect_pgsql_backup` as it is, matching decision 20261105-1105.

## Security & Constitution

- [x] CHK014 - Are identifiers taken from the backup checked before they go
  into SQL? [Security, Principle II]
  - Resolved: table and column names are checked with the
    `_validate_table_name` rule and quoted. Tables are also limited to the
    validated selection that exists in the live schema
    (`check_schema_compatibility`).
- [x] CHK015 - Is the restore still audited? [Principle II]
  - Resolved: the route already calls `log_event` after
    `orchestrate_partial_restore` (`admin/routes.py` ~L2470). That is unchanged.
- [x] CHK016 - Is there a regression test for the bug? [Principle III]
  - Resolved: the parser tests run in CI. The Postgres restore tests only run
    when `TEST_POSTGRES_URL` is set, and their output must be recorded locally
    (decided 2026-11-05).
- [x] CHK017 - Is the operational documentation updated in the same change? [Principle V]
  - Resolved: Task 4 updates `docs/deployment.md` §Partial Restore.
- [x] CHK018 - Is a migration needed? [Principle III]
  - Resolved: no. There are no schema changes.

## Robustness

- [x] CHK019 - Does `INSERT … SELECT` work for identity columns? [Edge case]
  - Resolved (accepted): no `Identity()` columns exist in models or migrations,
    so serial primary keys accept explicit values. Optionally add
    `OVERRIDING SYSTEM VALUE` as a precaution (analysis I1).
