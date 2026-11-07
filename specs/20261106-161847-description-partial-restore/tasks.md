---
feature: 20261106-161847-description-partial-restore
status: planned
created: 2026-11-07
chunk_size: medium
total_tasks: 4
estimated_lines: 200
---

# Partial Restore: Foreign-Key Violations Tasks

## Overview

Stop PostgreSQL partial restore from failing with `ForeignKeyViolation`. Before
the `INSERT`, the temp data is cleaned up: a reference to an unselected parent
table is set to NULL when the column allows it, and every other row with a
missing parent is skipped. Both counts are reported per table on the results
page and in the audit event. See [design.md](design.md) and decisions
`20261106-1626-pgsql-partial-restore-dangling-fk-handling` and
`20261106-1635-partial-restore-report-fk-counts-as-fields`.

## Task List

### Foundation

#### Task 1: Clear or skip dangling foreign keys in the PostgreSQL restore
- **Estimate:** ~75 lines (about 45 implementation, about 30 tests)
- **Files:** `scaffold/apps/admin/backup_utils.py`, `tests/test_admin_partial_restore.py`
- **Description:**
  - Add `cleared_reference_count: int = 0` and `skipped_missing_parent_count: int = 0`
    to `TableRestoreResult`.
  - Add `_resolve_dangling_fks(conn, insp, table_name, tmp, selected) -> tuple[int, int]`
    that returns `(cleared_reference_count, skipped_missing_parent_count)`,
    for non-self-referencing foreign keys. It follows the fixed order in
    design §Components:
    (1) if the table has a PK, delete the temp rows whose PK already exists live
    (no separate return value: these rows fall into `skipped_conflict_count`
    through the formula below);
    (2) delete the dangling rows for non-clearable FKs and count them as
    skipped;
    (3) `UPDATE … SET col = NULL` for clearable FKs (single column, nullable in
    the live schema, referenced table not in `selected`), counted per reference.
    A missing referenced table counts as "parent missing". Quote every
    identifier and pass it through `_validate_table_name`.
  - In `execute_partial_restore_pgsql`, call the helper inside the savepoint
    after the COPY and before the `INSERT`. Set
    `skipped_conflict_count = total - restored - skipped_missing_parent`
    and fill in both new fields.
  - Tests in `TestPgsqlRestore`: add a `pr_owner` table and a nullable
    `pr_child.owner_id → pr_owner`. Exact expected values:
    - (a) owner not selected and missing → `restored=1, cleared=1, skipped_missing_parent=0`;
    - (b) `parent_id NOT NULL`, parent not selected and missing → `restored=0, skipped_missing_parent=1`, status `skipped`;
    - (c) parent selected but row missing from the backup → `skipped_missing_parent=1, cleared=0`;
    - (d) parent table fails (non-FK error) → child table status `skipped`, not `failed`.
  - Rewrite `test_failing_table_does_not_abort_others` so it fails for a reason
    other than a foreign key (for example, a value that doesn't match the
    column type), because a dangling foreign key is now skipped.
- **Depends on:** None
- **Acceptance:** The default-selection scenario no longer produces
  `ForeignKeyViolation`. The existing pgsql tests stay green.
- **Evidence:** `TEST_POSTGRES_URL=… pytest tests/test_admin_partial_restore.py -k Pgsql`
  passes locally (run against a Docker Postgres by the implementer, output
  recorded in the PR). A plain `pytest tests/test_admin_partial_restore.py`
  passes.

#### Task 2: Order and counting edge cases
- **Estimate:** ~35 lines (tests; small fixes in `_resolve_dangling_fks` only if a case fails)
- **Files:** `tests/test_admin_partial_restore.py` (and `scaffold/apps/admin/backup_utils.py` if needed)
- **Description:** Add a nullable composite FK column pair to the test schema. Exact expected values:
  - (e) a row with a dangling `parent_id` (skip) **and** a dangling `owner_id` (clear) → `skipped_missing_parent=1, cleared=0`;
  - (f) rerun of (a) → `restored=0, cleared=0, skipped_conflict=1`;
  - (g) composite FK with one NULL column → row restored unchanged;
  - (h) helper `_assert_buckets(result, total)` checks
    `restored + skipped_conflict + skipped_missing_parent == total`, used in
    (a)–(g).
- **Depends on:** Task 1
- **Acceptance:** The fixed order (PK conflicts → skip → clear → INSERT) and the
  counting rules from decision 20261106-1635 are covered by tests.
- **Evidence:** The pgsql tests pass with `TEST_POSTGRES_URL`, with the output
  in the PR.

### Core Implementation

#### Task 3: Self-referencing foreign keys [P]
- **Estimate:** ~40 lines
- **Parallel:** Can run with Task 4
- **Files:** `scaffold/apps/admin/backup_utils.py`, `tests/test_admin_partial_restore.py`
- **Description:** In `_resolve_dangling_fks`, when `referred_table == table_name`,
  count the temp table as a valid parent alongside the live table, and repeat
  the `DELETE` pass until no rows are removed. Tests, using a `pr_node(parent_id → pr_node)`
  table that mirrors `adr_records.supersedes_id`:
  - a chain of 3 rows → `restored=3`;
  - a chain of 3 rows with the root parent missing → `restored=0, skipped_missing_parent=3`;
  - `_assert_buckets` on both.
- **Depends on:** Task 2
- **Acceptance:** Self-referencing tables restore without FK violations, and
  orphan chains don't leave half-inserted rows.
- **Evidence:** The new pgsql tests pass with `TEST_POSTGRES_URL`, with the
  output in the PR.

#### Task 4: Results page, translations, audit event and docs [P]
- **Estimate:** ~50 lines
- **Parallel:** Can run with Task 3
- **Files:** `scaffold/apps/admin/templates/admin/partial_restore_results.html`,
  `scaffold/translations/en.json`, `scaffold/translations/nl.json`,
  `scaffold/apps/admin/routes.py`, `docs/deployment.md`,
  `tests/test_admin_partial_restore.py`
- **Description:**
  - Add two right-aligned columns after "Rows skipped (conflict)". The table
    wrapper gets `overflow-x-auto` so 7 columns scroll on narrow screens.
  - Add the keys `admin.backup.partial_restore.results.cleared_references` and
    `…skipped_missing_parent` in EN and NL.
  - Add `cleared_reference_counts` and `skipped_missing_parent_counts` to the
    `partial_restore_execute` audit event.
  - In the "Partial Restore" section of `docs/deployment.md`, under the
    PostgreSQL bullets, document:
    - a reference to a table that isn't restored is set to NULL when the column allows it;
    - any other row with a missing parent is skipped;
    - both counts appear on the results page and in the audit trail;
    - FK cycles between selected tables are a known limitation.
  - Tests: the new fields round-trip through
    `save_run_state`/`load_run_state`; an old state file without the fields
    still loads with both values 0; the results page shows both headers; the
    audit payload contains both keys.
- **Depends on:** Task 1
- **Acceptance:** The admin sees both counts per table in EN and NL. The audit
  trail records them. An old run-state file still loads. The operational docs
  describe the new behaviour (constitution V).
- **Evidence:** `pytest tests/test_admin_partial_restore.py` passes without
  Postgres. `docs/deployment.md` diff in the PR.

## Notes
- The pgsql tests are skipped unless `TEST_POSTGRES_URL` is set, and CI doesn't
  run them (no Postgres in `.github/`). The implementer runs them locally
  against a Docker Postgres and puts the output in the PR. That's the required
  evidence for Tasks 1–3.
- After all tasks: check SC-001 manually by restoring a real backup with the
  default selection.
- `test_failing_table_does_not_abort_others` keeps covering the savepoint
  isolation from decision 20261105-1110, just with a non-FK error.
- Known limitation: FK cycles between selected tables. There are none in the
  current models (checked 2026-11-07).
- No migration is needed because there's no schema change. Translation updates
  are required (constitution IV), and so is the docs update (constitution V).
- Deferred: the SQLite path (no FK enforcement, so orphans are inserted
  silently), a warning in the preview, and remapping users.
- Rejected, simpler option (constitution governance): putting both counts in
  the message text. The reasons are in decision 20261106-1635.

## Progress
- [ ] Task 1: Clear or skip dangling foreign keys in the PostgreSQL restore — *implemented and committed; waiting on evidence: `-k Pgsql` against a real Postgres (not run yet, Docker unavailable on 2026-11-07). Without Postgres: 75 passed, 13 skipped.*
- [ ] Task 2: Order and counting edge cases — *implemented and committed; waiting on evidence: `-k Pgsql` against a real Postgres (not run yet). Without Postgres: 91 tests, 75 passed, 16 skipped, 0 failed.*
- [ ] Task 3: Self-referencing foreign keys
- [ ] Task 4: Results page, translations, audit event and docs
