---
feature: 20261106-161847-description-partial-restore
status: implemented
created: 2026-11-06
decisions:
  - 20261106-1626-pgsql-partial-restore-dangling-fk-handling
  - 20261106-1635-partial-restore-report-fk-counts-as-fields
---

# Partial Restore: Foreign-Key Violations Design

## Overview

A PostgreSQL partial restore with the default table selection fails on about
25 tables with `psycopg.errors.ForeignKeyViolation`. The default selection
leaves out the identity group (`users`, `roles`, …), but many domain tables
point to `users.id` (author, owner, creator, actor). If one backup row points
to a user that isn't in the live database, the table's single
`INSERT … SELECT` fails. Every table that depends on it then fails too.

The fix cleans each table's temp data before the `INSERT`:

- A nullable foreign key that points to a table **not** in this restore, and
  has no matching live row, is set to NULL. This follows the `SET NULL` rule
  the models already use.
- Any other row with a missing parent is skipped.

Both counts are shown per table on the results page and written to the
audit event.

## User Stories

- As an admin, I want a partial restore with the default selection to bring
  back my BIA, risk, CSA, SSP and threat data, even when the users referenced
  in the backup aren't in the live database.
- As an admin, I want to see per table how many references were cleared and
  how many rows were skipped because a parent was missing, so I know what to
  fix by hand.
- As an admin, I want one bad parent table to not fail every table below it.

## Components

### `_resolve_dangling_fks` (new helper in `scaffold/apps/admin/backup_utils.py`)

Called inside `execute_partial_restore_pgsql`, in the per-table savepoint,
after the COPY data is loaded into the temp table and before the
`INSERT … ON CONFLICT DO NOTHING`.

Signature (indicative):

```python
def _resolve_dangling_fks(
    conn, insp, table_name: str, tmp: str, selected: set[str]
) -> tuple[int, int]:  # (cleared_reference_count, skipped_missing_parent_count)
```

Definitions:

- A temp row is **dangling** for a foreign key
  (`insp.get_foreign_keys(table_name)`: `constrained_columns` →
  `referred_table.referred_columns`) when every constrained column is NOT NULL
  (MATCH SIMPLE: a partly NULL key isn't checked) and the live
  `referred_table` has no row with that key. For a self-referencing foreign key
  (`referred_table == table_name`), the temp table also counts as a valid parent.
- A foreign key is **clearable** when `referred_table` isn't in `selected`,
  the key has one column, and that column is nullable in the **live** schema
  (`insp.get_columns`).
- `selected` is the **effective** set of tables in this run, after the identity
  group has been added automatically (`run.selected_tables`), so not only
  what the admin ticked.
- A referenced table that isn't in the live schema counts as "no row exists".
  Only the `public` schema is supported, as in the rest of the restore.

Steps, in a fixed order, inside the savepoint after the COPY and before the `INSERT`:

1. **Remove PK conflicts.** If the table has a primary key, delete the temp rows
   whose PK already exists in the live table. Add the count to
   `skipped_conflict_count`. These rows would be skipped anyway, and removing
   them first stops a rerun from reporting cleared references for rows that
   are never inserted.
2. **Skip.** For each **non-clearable** foreign key, run
   `DELETE FROM tmp WHERE <dangling>`. Add the rowcount to
   `skipped_missing_parent_count`. Repeat the whole pass until no more rows are
   deleted, because deleting a self-referencing parent can leave a child
   orphaned in the temp table.
3. **Clear.** For each **clearable** foreign key, run
   `UPDATE tmp SET col = NULL WHERE <dangling>`. Add the rowcount to
   `cleared_reference_count`.
   This happens after step 2, so a row is never both skipped and cleared.
   The count is **per reference**: a row with two cleared foreign keys counts 2.
4. `INSERT … ON CONFLICT DO NOTHING`. Rows that still conflict, on a unique
   constraint other than the PK, are added to `skipped_conflict_count`.

Each row in the COPY block ends up in exactly one bucket:
`total = restored + skipped_conflict + skipped_missing_parent`.
The one inaccuracy accepted: a cleared row that then hits a conflict on a
unique constraint other than the PK still counts towards
`cleared_reference_count`.

All identifiers go through `_validate_table_name` and are quoted, as in the
existing code.

### `execute_partial_restore_pgsql` (changed)

- Calls the helper with `selected = set(selected_tables)`. The caller already
  passes the effective set.
- `total` stays the count of the COPY block.
  `skipped_conflict_count = total - restored - skipped_missing_parent`. This
  covers both PK conflicts removed in step 1 and conflicts from the `INSERT`.
- Sets the two new counts on `TableRestoreResult`.
- Status per table is unchanged: `restored` if restored > 0, otherwise
  `skipped`. The table's message column stays empty for cleared or skipped
  rows; the counts are the explanation.
- Run status is unchanged: the orchestrator already returns `completed` when
  every table is `restored`/`skipped`. Cleared or skipped rows don't make a
  run `partial`.
- Order (parents first), savepoints and sequence handling stay the same.

Because tables restore parents-first in one transaction, a parent table
restored earlier in the run is already visible in the live table. If a parent
table failed, its children see a missing parent and skip those rows. They no
longer fail.

### Results page and audit

- `partial_restore_results.html`: two right-aligned columns after
  "Rows skipped (conflict)".
- `routes.py` `partial_restore_execute` audit event: adds
  `cleared_reference_counts` and `skipped_missing_parent_counts`, keyed by table.
- `en.json` / `nl.json`, under `admin.backup.partial_restore.results`:
  - `cleared_references`: "References cleared (parent not restored)" /
    "Verwijzingen gewist (bovenliggende tabel niet hersteld)"
  - `skipped_missing_parent`: "Rows skipped (missing parent)" /
    "Overgeslagen rijen (ontbrekende bovenliggende rij)"

## Data Model

`TableRestoreResult` gets two fields:

```python
cleared_reference_count: int = 0
skipped_missing_parent_count: int = 0
```

They have defaults, so `save_run_state` / `load_run_state` (`asdict` / `**r`)
need no changes, and older run-state JSON files still load. No database
migration is needed.

## API/Interface

No new routes. The results page and the audit payload get extra fields.

## Edge Cases

- **User FK nullable, users not selected** (`bia_context_scope.author_id`,
  `risk_items.treatment_owner_id`, …): the reference is cleared and the row
  restores.
- **NOT NULL user FK, users not selected** (e.g. the assignee on
  `csa_assessment_assignments`): the row is skipped and counted.
- **Parent table selected but its row is missing** (parent row lost to a
  unique conflict, or parent table failed): the child row is skipped and counted.
- **Composite FK to an unselected table**: the row is skipped. No partial
  NULLs are written.
- **Self-reference** (parent and child in the same backup): restores. An
  orphan chain is skipped step by step.
- **Identity group selected**: `users` is selected, so user foreign keys are
  never cleared. Any dangling row is skipped.
- **Identity group selected, but a user row was skipped because of a conflict on
  email**: `users` is selected, so it's not clearable. Child rows that point to
  the backup id are skipped and counted under missing parent.
- **Composite FK with one NULL column**: not checked (MATCH SIMPLE). The row
  goes through unchanged.
- **Rerun of the same backup**: every row is removed as a PK conflict in step 1.
  Cleared and missing-parent counts are 0.
- **FK cycle between two selected tables (A → B → A)**: *known limitation.*
  The table restored first can't see its parent yet, so those rows are skipped.
  The current models have no cycles (checked 2026-11-07 with
  `sort_tables_and_constraints`). If one is added later, it needs a follow-up
  feature.
- **Table with no foreign keys**: no change, and both counts are 0.

## Success Criteria

- **SC-001:** A partial restore of a real production backup with the default
  selection, into a database whose `users` ids don't match, has **0 tables**
  with status `failed` and no `ForeignKeyViolation` in any message.
- **SC-002:** For every table, `restored + skipped_conflict + skipped_missing_parent`
  equals the number of rows in the COPY block.
- **SC-003:** Running the same restore again gives `restored = 0`,
  `cleared = 0` and `skipped_missing_parent = 0` for every table.
- **SC-004:** The run status of the SC-001 scenario is `completed`.

## Testing

The exact test cases and expected values are in [tasks.md](tasks.md)
(Tasks 1–4). That's the only source, so this section and the tasks can't
drift apart. In short: PostgreSQL tests in `TestPgsqlRestore` on
`_make_pgsql_backup_gz` COPY dumps (clear, skip, cascade, order, rerun,
composite key, self-reference, total invariant), plus tests without Postgres
for run state, the results page and the audit payload.

## Constitution Check

| Principle | Confirmation |
|-----------|--------------|
| I. Module boundaries | Only the `admin` module (`backup_utils.py`, `routes.py`, admin template). No cross-domain imports; FK information comes from the SQLAlchemy inspector, not from other modules' models. |
| II. Security & audit | No change to roles or access: partial restore stays admin-only. Audit impact: the `partial_restore_execute` event gets `cleared_reference_counts` and `skipped_missing_parent_counts`. Operational risk: owner and author fields can come back empty; this is visible on the results page and in the audit log. Identifiers stay validated and quoted (no SQL injection through table or column names). |
| III. Test & migration | Regression tests in `tests/test_admin_partial_restore.py`. The pgsql tests run locally with `TEST_POSTGRES_URL` (not in CI), and the output is recorded in the PR. No schema change, so no Alembic migration. |
| IV. UI & localization | Two columns in the existing Tailwind table, with labels through `_()` and keys in `en.json` and `nl.json`. No Bootstrap. |
| V. Operational readiness | Restore behaviour changes, so the "Partial Restore" section of `docs/deployment.md` is updated in the same change (Task 4). No new environment variables or deployment steps. |

## Out of Scope

- SQLite partial restore. SQLite doesn't enforce foreign keys here, so it
  doesn't fail. It does insert orphan rows without saying so. Follow-up.
- A warning in the preview that user references will be cleared. Follow-up.
- Remapping users by email or username.

## Open Questions

- None. Checked 2026-11-07: outside the identity group, the only `NOT NULL`
  user reference is `csa_assessment_assignments.assignee_id`. Those rows are
  skipped when the user is missing. Self-referencing tables in the models:
  `adr_records.supersedes_id` and `threat_models.bootstrap_source_model_id`.
