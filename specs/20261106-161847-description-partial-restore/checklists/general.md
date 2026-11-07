---
type: checklist
domain: general
feature: 20261106-161847-description-partial-restore
created: 2026-11-07
status: completed
---

# General Requirements Quality Checklist

**Purpose:** Check that the requirements for handling dangling foreign keys in
PostgreSQL partial restore are complete, clear and consistent, with the focus
on data integrity and how results are reported.
**Feature:** 20261106-161847-description-partial-restore

## Completeness

- [x] CHK001 - Does the design say in what order a row's foreign keys are handled when one key would clear the row and another would skip it? Is a row that gets cleared and then deleted counted only as skipped? [Gap, Design §Components/_resolve_dangling_fks]
- [x] CHK002 - Is the overall run status (`completed` vs `partial`) defined for a run where rows were cleared or skipped because a parent was missing, but no table failed? [Gap]
- [x] CHK003 - Are requirements defined for foreign-key **cycles** between two selected tables (A → B → A)? The child processed first can't see the parent yet, so with A2 it gets skipped even though the parent is in the backup. [Gap, Edge Case]
- [x] CHK004 - Is it specified what happens when the referenced table doesn't exist in the live schema, or is in a schema other than `public`? [Gap]
- [x] CHK005 - Does the design say whether a cleared or skipped table also gets an explanatory text in the message column, or only counts? [Gap, Design §Results page]
- [x] CHK006 - Are measurable success criteria written down in the design (for example, "default selection on a realistic backup: 0 tables `failed` because of an FK violation")? [Gap, Measurability]

## Clarity

- [x] CHK007 - Is `cleared_reference_count` clearly defined as counting **references** (one per FK per row) or **rows**, for a row with two cleared FKs? [Clarity, Decision 20261106-1635]
- [x] CHK008 - Is it clear whether a row whose FK was cleared but that then hits `ON CONFLICT DO NOTHING` counts in `cleared_reference_count`, `skipped_conflict_count`, or both? [Clarity, Design §execute_partial_restore_pgsql]
- [x] CHK009 - Is "parent table not selected" defined against the admin's selection or against the effective set after the identity group is added automatically? [Clarity, Decision 20261106-1626]
- [x] CHK010 - Is "nullable" defined against the live schema (`insp.get_columns`) rather than the model or the backup? [Clarity]

## Consistency

- [x] CHK011 - Does the formula `skipped_conflict_count = total - restored - skipped_missing_parent` match the meaning of "rows skipped (conflict)" in the existing UI label and in decision 20261105-1100? [Consistency]
- [x] CHK012 - Are the status rules for `restored`/`skipped` the same in the design, decision 20261106-1635 and tasks.md (0 restored → `skipped`, including when the cause is missing parents)? [Consistency]
- [x] CHK013 - Does the "parent fails → child not `failed`" expectation in tasks.md Task 1 (d) agree with CHK003: a cycle could still produce skips that are hard to explain? [Consistency]
- [x] CHK014 - Does the planned rewrite of `test_failing_table_does_not_abort_others` (a non-FK error) still cover what decision 20261105-1110 meant to guarantee about savepoint isolation? [Consistency]

## Measurability

- [x] CHK015 - Do Tasks 1–3 have evidence that can be checked without a local Postgres, or is it written down who runs the `TEST_POSTGRES_URL` tests and where (CI or manually)? [Measurability, tasks.md Notes]
- [x] CHK016 - Are the expected counts in every test case in tasks.md given as exact numbers rather than "counted"? [Measurability]

## Coverage

- [x] CHK017 - Is a composite FK where **one** column is NULL (MATCH SIMPLE, not checked) covered by an explicit test or acceptance criterion? [Coverage, Design §Edge Cases]
- [x] CHK018 - Is the case "identity group selected, but a user row was skipped because of a conflict on a non-PK unique column (email)" covered? With A2 the child row is then skipped, not cleared. [Coverage]
- [x] CHK019 - Are the audit requirements specific enough for later investigation, for example whether the event records *which* FK columns were cleared or only totals? [Coverage, constitution II]
- [x] CHK020 - Do the requirements state that the NL and EN labels have to fit the wider 7-column table, and say how it behaves on a narrow screen? [Coverage, constitution IV]
- [x] CHK021 - Is the behaviour for older run-state files (without the new fields) set as an acceptance criterion and not only mentioned in the design? [Coverage, tasks.md Task 4]

## Resolution (2026-11-07)

All items have been resolved in design.md, the decisions and tasks.md:
- CHK001/007/008/011: fixed order (PK conflicts → skip → clear → INSERT), counting per reference, and the invariant `total = restored + conflict + missing_parent`.
- CHK002/012: run status and table status unchanged; only restored/skipped → `completed`.
- CHK003/013: no FK cycles in the current models; recorded as a known limitation.
- CHK004/009/010: missing referenced table counts as "parent missing"; `selected` is the effective set; nullability comes from the live schema.
- CHK005/019: no message text; the audit event records totals (reason in decision 1635).
- CHK006: SC-001 to SC-004 added to the design.
- CHK014–018/021: test cases (a)–(h) with exact values, a self-reference chain, and an old state file.
- CHK020: `overflow-x-auto` on the results table.

## Summary

- **Total items:** 21
- **Focus areas:** data integrity (FK order, cycles, counting), result and status semantics, testability
- **Main gaps found:**
  - Order and counting when one row has several FKs, or an FK clear combined with a conflict (CHK001, CHK007, CHK008)
  - FK cycles between selected tables (CHK003)
  - Run status after cleared or skipped rows (CHK002)
  - No measurable success criteria in the design (CHK006)
