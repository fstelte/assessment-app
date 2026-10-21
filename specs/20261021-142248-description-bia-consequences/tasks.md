---
feature: 20261021-142248-description-bia-consequences
status: planned
created: 2026-10-21
chunk_size: adaptive
total_tasks: 11
estimated_lines: 900
---

# BIA Consequences per CIA with Category Labels — Tasks

## Overview

Implements [design.md](design.md): multiselect category labels stored on one
consequence per (component, CIA property); grouped CIA display on every
overview; group edit/delete; all writes consolidated on
`manage_item_consequences`.

## Shared Contracts (fixed up front so waves can run in parallel)

1. **`ConsequenceGroup` / `group_consequences(consequences)`** in
   `scaffold/apps/bia/utils.py` — exact shape as in design.md § Components.
   Groups ordered by component name, then C → I → A → "not set".
2. **Template context name:** every route that renders consequences passes
   `consequence_groups: list[ConsequenceGroup]` (in addition to whatever it
   passes today, until the template no longer needs the old variable).
3. **`save_cia_consequence(component, security_property, categories, worstcase,
   justification_worstcase, realisticcase, justification_realisticcase,
   replace_ids) -> Consequences`** in `scaffold/apps/bia/utils.py`; does not
   commit (caller commits).
4. **Translation keys** (added in Task 3, used everywhere else):
   - `bia.consequence_category.{financial,operational,reputation_and_trust,regulatory,human_and_safety,privacy}`
   - `bia.flash.consequence_exists_edit`
   - `bia.flash.consequence_group_changed`
   - `bia.consequence_form.validation.target_exists`
   - `bia.consequences.group.merge_hint` (takes `count`)
   - `bia.view_consequences.actions.manage`
   - `bia.flash.consequence_group_deleted`
5. **Manage page query params:** `consequence_id` (edit that record's group),
   `component_id` and `security_property` (preselect for create).
6. **Template filter `consequence_category`** → `category_label(value)` from
   `utils.py`. Templates render chips as `{{ cat | consequence_category }}`.

Parallel tasks touching `routes.py` edit **different functions only** — merge
conflicts should be trivial.

## Task List

### Wave 1 — Foundation (all three in parallel, no dependencies)

#### Task 1: `group_consequences()` + `category_label()` helpers + tests [P]
- **Estimate:** ~130 lines (≈60 impl, ≈70 tests)
- **Parallel:** with Tasks 2, 3, 6
- **Files:** `scaffold/apps/bia/utils.py`, `scaffold/apps/bia/routes.py` (filter
  registration next to `duration`, ~L96), `scaffold/apps/bia/forms.py`
  (`ConsequenceForm.consequence_category` choice labels → lazy translation keys),
  `tests/test_bia_consequence_groups.py` (new)
- **Description:** Add `category_label()` (key → `bia.consequence_category.<key_with_underscores>`,
  unknown → raw value) and register it as filter `consequence_category`.
  Add `ConsequenceGroup` dataclass and `group_consequences()`.
  Union of `get_categories()` in `ConsequenceForm` choice order, unknown values
  after in first-seen order; max worst/realistic
  via `get_impact_level`; distinct non-empty justifications joined by `"\n\n"`;
  `records` sorted by id; `representative_id = records[0].id`; property match
  `strip().lower()`; unknown/empty property → trailing "not set" group.
- **Depends on:** None
- **Acceptance:** Legacy input (3 rows, same component+C, one category each,
  differing impacts) → one group with 3 labels and the highest impacts; mixed
  C/I/A ordering correct; single comma-joined record → labels split; unknown
  value `Operational` sorts last and `category_label` returns it raw; known key
  returns translated label.
- **Evidence:** `pytest tests/test_bia_consequence_groups.py` passes.

#### Task 2: `save_cia_consequence()` helper + tests [P]
- **Estimate:** ~70 lines (≈25 impl, ≈45 tests)
- **Parallel:** with Tasks 1, 3, 6
- **Files:** `scaffold/apps/bia/utils.py` (separate section from Task 1), `tests/test_bia_consequence_save.py` (new)
- **Description:** Update lowest id in `replace_ids` (or create when empty), set
  `consequence_category = ",".join(categories)`, delete the other ids. No commit.
- **Depends on:** None
- **Acceptance:** Empty `replace_ids` → 1 new row; 3 ids → 1 row survives (lowest
  id) with joined labels, other 2 deleted.
- **Evidence:** `pytest tests/test_bia_consequence_save.py` passes.

#### Task 3: Translation keys (en/nl) [P]
- **Estimate:** ~35 lines
- **Parallel:** with Tasks 1, 2, 6
- **Files:** `scaffold/translations/en.json`, `scaffold/translations/nl.json`
- **Description:** Add all keys from Shared Contract 4 in both languages
  (6 category labels + 6 messages).
  Do not remove old keys yet (Task 11).
- **Depends on:** None
- **Acceptance:** Keys present in both files, valid JSON.
- **Evidence:** `python -c "import json;json.load(open(...))"` on both files; existing i18n tests pass.

#### Task 6: Remove JSON endpoints, redirect `/consequences/new` [P]
- **Estimate:** ~-200 / +40 lines
- **Parallel:** with Tasks 1, 2, 3 (independent of helpers)
- **Files:** `scaffold/apps/bia/routes.py` (`add_component_consequence_view`,
  `add_consequence`, `get_consequence`, `edit_consequence`),
  `scaffold/apps/bia/templates/bia/manage_component_consequence.html` (delete),
  `tests/test_bia_routes.py` (tests around L295, L385–415)
- **Description:** Delete the three JSON endpoints. Replace
  `add_component_consequence_view` body with a 302 to
  `manage_item_consequences(item_id=component.context_scope_id, component_id=id)`
  keeping the permission check. Delete the template. Rewrite the old create test
  to assert the redirect `Location`; keep the components-list link test.
  Leave `view_consequences.html` modal for Task 7 (it will 404 briefly — fine on
  the feature branch).
- **Depends on:** None
- **Acceptance:** GET `/bia/component/<id>/consequences/new` → 302 to manage page
  with `component_id`; removed URLs → 404/405.
- **Evidence:** `pytest tests/test_bia_routes.py` passes.

### Wave 2 — Core (all in parallel once Wave 1 helpers land)

#### Task 4: Manage page route — group edit, create→edit, preselect [P]
- **Estimate:** ~130 lines (≈60 impl, ≈70 tests)
- **Parallel:** with Tasks 5, 7, 8, 9, 10, 4b
- **Files:** `scaffold/apps/bia/routes.py` (`manage_item_consequences`),
  `scaffold/apps/bia/forms.py` (hidden `group_ids` field on
  `BIAConsequenceManagerForm`), `tests/test_bia_consequence_manage.py` (new)
- **Description:** GET `consequence_id` → resolve group, prefill merged values,
  hidden `group_ids`. GET `component_id`/`security_property` → preselect.
  POST create with existing (component, property) → no save, re-render in edit
  mode with merged prefill ∪ submitted labels + flash `consequence_exists_edit`.
  POST edit → if current group ids ≠ submitted `group_ids` → no save, reload
  edit form with fresh merged values + flash `consequence_group_changed`;
  else `save_cia_consequence(..., replace_ids=group_ids)`; if the target
  (component, property) changed and already has a group → form error
  `target_exists`. At least one label required (create and edit). Drop
  `single_category` check. Pass `consequence_groups`.
- **Depends on:** Tasks 1, 2, 3
- **Acceptance:** Multi-label create stores 1 row; duplicate create doesn't save
  and shows edit mode; editing a 3-row legacy group leaves 1 row with union
  labels; stale `group_ids` doesn't save and shows the flash; zero labels →
  validation error; retarget conflict shows error; preselect params populate form.
- **Evidence:** `pytest tests/test_bia_consequence_manage.py tests/test_bia_routes.py` passes.

#### Task 4b: Manage page template — grouped list [P]
- **Estimate:** ~70 lines
- **Parallel:** with Tasks 4, 5, 7, 8, 9, 10
- **Files:** `scaffold/apps/bia/templates/bia/manage_item_consequences.html`
- **Description:** Replace `consequence_rows` table with `consequence_groups`:
  component · CIA badge · label chips (`| consequence_category`) · worst ·
  realistic · justifications; merge hint when `records|length > 1` (this page
  only); Edit link uses `representative_id`;
  Delete posts to `delete_consequence(representative_id)`. Render hidden
  `group_ids` field. Category multiselect help text stays.
- **Depends on:** Tasks 1, 3 (contract 2 for context name)
- **Acceptance:** Page renders grouped rows for legacy and new data.
- **Evidence:** Route test from Task 4 asserts grouped HTML (one C row, chips);
  manual check in browser.

#### Task 5: Group delete [P]
- **Estimate:** ~45 lines (≈15 impl, ≈30 tests)
- **Parallel:** with Tasks 4, 4b, 7, 8, 9, 10
- **Files:** `scaffold/apps/bia/routes.py` (`delete_consequence`), `tests/test_bia_consequence_delete.py` (new)
- **Description:** Delete all records sharing the given record's
  (component_id, normalised security_property). Keep permission check and
  response shape; flash `consequence_group_deleted` where it redirects.
- **Depends on:** Task 3
- **Acceptance:** Deleting one id of a 3-row group removes all 3; other
  properties untouched.
- **Evidence:** `pytest tests/test_bia_consequence_delete.py` passes.

#### Task 7: Component consequences page — read-only grouped [P]
- **Estimate:** ~-150 / +50 lines
- **Parallel:** with Tasks 4, 4b, 5, 8, 9, 10
- **Files:** `scaffold/apps/bia/routes.py` (`view_consequences`),
  `scaffold/apps/bia/templates/bia/view_consequences.html`
- **Description:** Pass `consequence_groups`; render grouped read-only rows;
  remove add/edit modal markup and its JS; header "Manage" button →
  `manage_item_consequences(item_id=…, component_id=…)` (only when user can edit).
- **Depends on:** Tasks 1, 3
- **Acceptance:** No references to removed endpoints remain in the template;
  grouped rows display.
- **Evidence:** `pytest tests/test_bia_routes.py` passes; grep for
  `add_consequence|edit_consequence|get_consequence` in templates returns nothing.

#### Task 8: All-consequences page — grouped [P]
- **Estimate:** ~50 lines
- **Parallel:** with Tasks 4, 4b, 5, 7, 9, 10
- **Files:** `scaffold/apps/bia/routes.py` (route rendering `all_consequences.html`, ~L951),
  `scaffold/apps/bia/templates/bia/all_consequences.html`
- **Description:** Pass `consequence_groups`; one row per group with BIA/component,
  CIA badge, chips, impacts; delete uses `representative_id`.
- **Depends on:** Tasks 1, 3
- **Acceptance:** Grouped rendering; delete button deletes group (with Task 5).
- **Evidence:** Smoke test GET returns 200 and contains one row per group.

#### Task 9: BIA detail (and item export) — grouped, plus group counts [P]
- **Estimate:** ~60 lines
- **Parallel:** with Tasks 4, 4b, 5, 7, 8, 10
- **Files:** `scaffold/apps/bia/routes.py` (`view_item` ~L451, `export_item` ~L1567 —
  both render `context_detail.html`), `scaffold/apps/bia/templates/bia/context_detail.html`
  (section ~L499, count ~L362), `scaffold/apps/bia/templates/bia/components.html`
  (consequence count, if shown)
- **Description:** Pass `consequence_groups` from both routes; replace the
  consequences table body with grouped rows (read-only, no merge hint).
  Change per-component consequence counts to count groups
  (`group_consequences(component.consequences) | length`).
- **Depends on:** Tasks 1, 3
- **Acceptance:** Detail page and HTML/PDF item export show grouped CIA rows;
  a legacy component with 3 C-rows shows count 1.
- **Evidence:** Existing view/export tests pass; smoke assert on one grouped row.

#### Task 10: Global consequences export — grouped [P]
- **Estimate:** ~40 lines
- **Parallel:** with Tasks 4, 4b, 5, 7, 8, 9
- **Files:** `scaffold/apps/bia/routes.py` (`export_all_consequences` ~L1925),
  `scaffold/apps/bia/templates/bia/export_all_consequences.html`
- **Description:** Grouped rows in HTML/PDF (no merge hint). CSV/SQL/JSON
  exports unchanged.
- **Depends on:** Task 1
- **Acceptance:** HTML/PDF export shows grouped CIA rows with labels.
- **Evidence:** Existing export tests pass; HTML export smoke test.

### Wave 3 — Integration

#### Task 11: Cleanup, full validation, docs
- **Estimate:** ~40 lines
- **Files:** `scaffold/translations/en.json`, `scaffold/translations/nl.json`,
  `docs/models.md` (L16 `Consequences` entry),
  `scaffold/apps/bia/templates/bia/export_item.html` (delete — unused), `graphify-out/`
- **Description:** Remove now-unused keys (`bia.consequence_form.validation.single_category`,
  modal/JSON strings, `Added %(count)d consequence entries.`); remove
  `consequence_rows` if unused; delete `export_item.html`; update
  `docs/models.md` to say "one consequence per CIA property per component;
  categories stored comma-joined as labels"; `graphify update .`.
- **Depends on:** All other tasks
- **Acceptance:** No template references removed context vars/endpoints/keys.
- **Evidence:** Full `pytest` passes; grep for removed keys/endpoints is empty.

## Parallel Waves

| Wave | Tasks | Notes |
|---|---|---|
| 1 | 1, 2, 3, 6 | Fully independent |
| 2 | 4, 4b, 5, 7, 8, 9, 10 | Need Tasks 1 (+2 for Task 4) and 3; touch different `routes.py` functions/templates |
| 3 | 11 | After everything |

Critical path: Task 1/2 → Task 4 → Task 11.

## Notes
- Display-only grouping means Wave 2 view tasks work on legacy data without
  any migration.
- Task 6 temporarily breaks the modal on `view_consequences.html` until Task 7
  lands — acceptable on the feature branch; don't release between them.
- Use separate new test files per task to avoid conflicts in `tests/test_bia_routes.py`
  (only Task 6 edits it).
- Deferred: CSV import label splitting, DB uniqueness constraint, legacy data
  merge migration.

## Progress
- [ ] Task 1: `group_consequences()` + `category_label()` helpers + tests
- [ ] Task 2: `save_cia_consequence()` helper + tests
- [ ] Task 3: Translation keys (en/nl)
- [ ] Task 6: Remove JSON endpoints, redirect `/consequences/new`
- [ ] Task 4: Manage page route — group edit, create→edit, preselect
- [ ] Task 4b: Manage page template — grouped list
- [ ] Task 5: Group delete
- [ ] Task 7: Component consequences page — read-only grouped
- [ ] Task 8: All-consequences page — grouped
- [ ] Task 9: BIA detail (and item export) — grouped, plus group counts
- [ ] Task 10: Global consequences export — grouped
- [ ] Task 11: Cleanup, full validation, docs
