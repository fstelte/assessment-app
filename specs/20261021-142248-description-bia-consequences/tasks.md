---
feature: 20261021-142248-description-bia-consequences
status: planned
created: 2026-10-21
chunk_size: adaptive
total_tasks: 16
estimated_lines: 1285
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
  `single_category` check. Pass `consequence_groups`. Honour a
  `return_to` query param (via `_safe_return_target`) as the redirect target
  after a successful save (Task 6 forwards it from the old add page).
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
  `scaffold/apps/bia/templates/bia/export_item.html` and
  `scaffold/apps/bia/templates/bia/detail.html` (delete — neither is rendered), `graphify-out/`
- **Description:** Remove now-unused keys (`bia.consequence_form.validation.single_category`,
  modal/JSON strings, `Added %(count)d consequence entries.`); reword the create flash (`consequence_created` now
  always has count=1 → e.g. "Consequence saved."); delete `export_item.html`; update
  `docs/models.md` to say "one consequence per CIA property per component;
  categories stored comma-joined as labels". Fix the delete confirmation on
  `manage_item_consequences.html` (~L192). It currently uses
  `bia.components.table.confirm_delete` ("Delete this component?"). Switch it to
  `bia.all_consequences.confirm_delete`, or for groups with more than one record
  to the new en/nl key `bia.consequences.group.confirm_delete` with
  `{count}` (design §Rules "Delete confirmation"). Run `graphify update .`.
- **Depends on:** All other tasks
- **Acceptance:** No template references removed context vars/endpoints/keys.
  No consequence delete path uses a `components.*` confirm key. A route test
  checks that the manage page renders the group-count confirmation for a legacy
  group.
- **Evidence:** Full `pytest` passes; grep for removed keys/endpoints is empty.

---

## Part 2: Tier RTO/RPO pre-fill with manual overrides

Design: `design.md` Part 2. Decisions: `20261021-1655-tier-goal-prefills-component-rto-rpo`,
`20261021-1655-availability-csv-rto-rpo-source-columns`.

### Wave 4: Foundation

#### Task 12: Duration parser + `Component` recovery source
- **Estimate:** ~110 lines (incl. tests)
- **Files:** `scaffold/apps/bia/models/__init__.py` (next to `format_duration_seconds`),
  `tests/test_bia_component_tier.py`
- **Description:** Add `parse_duration_seconds(text) -> int | None`, moved from
  `_parse_duration` in the summary export (do not switch the caller yet; Task 15
  does that). It returns seconds and follows the unit table in design.md Part 2:
  longest prefix first (`mo`/`maand`/`mnd` = 30 d before `m`), `.`/`,`
  decimals, `j`/`jaar`, a bare number other than 0 → `None`. Flip
  `_effective_recovery` so stored text wins over the goal. Add
  `recovery_source(field)` (tier/manual/free_text/None), `tier_goal_display(field)`
  and the `rto_source`/`rpo_source` properties.
- **Depends on:** None
- **Acceptance:** All five `recovery_source` branches are covered. Rewrite
  `test_effective_recovery_uses_tier_goal_over_stored_text` (stored text now
  wins). Rewrite `test_incident_prefill_uses_tier_goal_then_stored_text`
  (`"stale"` becomes the effective RTO and counts as manual). The parser test
  has one case per row of the unit table, plus `1,5 u` = 5400, `1 maand` =
  2592000, `60` → `None`, and `immediate`/`-` = 0. A goal of 0 with
  `immediate` gives `tier`.
- **Evidence:** `pytest tests/test_bia_component_tier.py -k "duration or recovery or incident"` passes.

### Wave 5: Core

#### Task 13: Availability forms: pre-fill, save rule, hints
- **Estimate:** ~100 lines (incl. tests)
- **Files:** `scaffold/apps/bia/routes.py` (`_tier_goal_notes`, `_apply_availability`,
  `manage_component_availability` ~L1020, `manage_item_availability` ~L1300),
  `manage_component_availability.html`, `manage_item_availability.html` (form part),
  `scaffold/translations/en.json`, `nl.json`, `tests/test_bia_component_tier.py`
- **Description:** Drop the read-only goal box. Always render the input with
  the goal hint below it, plus a "Manually configured (tier goal: …)" line when
  the source is manual. On GET, pre-fill the formatted goal when nothing is
  stored. `manage_component_availability` uses `AvailabilityForm(obj=…)`, so set
  the data only when `not form.is_submitted()`. In `_apply_availability`, store
  `""` when the submitted text is empty or parses to the goal, else store it as
  typed. Add the en/nl keys for the manual form line and the marker text
  (`manual · tier {value}` / `handmatig · tier {value}`). There is no tooltip.
- **Depends on:** Task 12
- **Acceptance:** Rewrite tests 199–238 (`…shows_goal_and_keeps_stored_text`,
  `…decides_rto_and_rpo_independently`,
  `…update_availability_json_respects_tier_goal`). The new behaviour is:
  unchanged pre-fill → stored `""`; `"240 min"` against a 4 h goal → `""`;
  `"2 h"` → stored and manual; cleared → `""`; GET shows a pre-filled input.
  The translation-parity test includes the new keys.
- **Evidence:** `pytest tests/test_bia_component_tier.py -k availability` passes.

#### Task 14: Manual marker in tables and HTML/PDF exports [P]
- **Estimate:** ~70 lines (incl. tests)
- **Parallel:** Can run with Task 15
- **Files:** new `scaffold/apps/bia/templates/bia/_recovery_marker.html` (macro),
  `manage_item_availability.html` (list), `components.html` (~L299),
  `context_detail.html` (~L431), `requirements.html` (~L128),
  `export_availability_requirements.html` (~L43), `tests/test_bia_component_tier.py`
- **Description:** Add a macro `recovery_marker(component, field, plain=False)`
  that renders **visible text** `manual · tier 4 h` (nl `handmatig · tier 4 u`)
  only when the source is manual. No tooltip. In-app it uses the amber chip
  classes; with `plain=True` (exports) it renders plain text in parentheses.
  Call it after every `effective_rto`/`effective_rpo` output. In
  `components.html`, call it after each value. The summary export gets no
  marker.
- **Depends on:** Task 12 (keys from Task 13)
- **Acceptance:** Update `test_requirements_page_shows_tier_goal_instead_of_stored_text`
  (stored text now shown with the marker) and
  `test_component_pages_show_tier_goal_without_availability_row` (still the
  goal, no marker). New test: a manual component shows the marker on
  components, BIA detail and the requirements export; a tier-following one
  does not.
- **Evidence:** targeted pytest passes; rendered HTML contains/omits the marker.

#### Task 15: Summary export precedence + CSV source columns [P]
- **Estimate:** ~80 lines (incl. tests)
- **Parallel:** Can run with Task 14
- **Files:** `scaffold/apps/bia/routes.py` (summary export ~L1931–2000),
  `scaffold/apps/bia/utils.py` (availability CSV ~L515), `tests/test_bia_component_tier.py`
- **Description:** Remove the local `_parse_duration`, use
  `parse_duration_seconds` (`None` → inf), and drop the "tier goal replaces
  stored text" branch so each component contributes its effective value. Append
  `RTO Source`, `Effective RTO`, `RPO Source` and `Effective RPO` to the
  availability CSV (`tier`/`manual`/`free text`/`not set`, mapped from the
  internal `free_text`/`None`). The CSV now writes **one row per component**,
  including those without an availability record. The CSV import
  (`utils.py` ~L768) skips rows whose MTD, RTO, RPO and MASL are all empty.
- **Depends on:** Task 12
- **Acceptance:** Rewrite `test_summary_export_takes_lowest_of_tier_goal_and_stored_text`
  and `test_summary_export_uses_tier_goals_and_stored_text` for the new
  precedence. A new CSV test checks the headers, one row per source, and a row
  for a component with no record. The CSV round trip still passes and does not
  create empty availability records.
- **Evidence:** `pytest tests/test_bia_component_tier.py -k "summary or csv"` passes.

### Wave 6: Integration

#### Task 16: Docs + full validation (Part 2)
- **Estimate:** ~25 lines
- **Files:** `docs/models.md` (`Component` effective RTO/RPO, `AvailabilityRequirements`),
  `docs/history.md`, `graphify-out/`
- **Description:** Document the new precedence, the sources, "empty stored
  text means follow the tier", and that imports store text as given. Add a
  history entry with an explicit **behaviour change** note: hidden legacy
  RTO/RPO text becomes effective again, so incident steps and summary exports
  can change. Run `graphify update .`.
- **Depends on:** Tasks 13–15 (and Task 11 for the shared docs files)
- **Acceptance:** The docs no longer say that the tier goal replaces stored text.
- **Evidence:** Full `pytest` passes, apart from the known pre-existing failures listed in Notes.

## Parallel Waves

| Wave | Tasks | Notes |
|---|---|---|
| 1 | 1, 2, 3, 6 | Fully independent |
| 2 | 4, 4b, 5, 7, 8, 9, 10 | Need Tasks 1 (+2 for Task 4) and 3; touch different `routes.py` functions/templates |
| 3 | 11 | After everything |
| 4 | 12 | Part 2 foundation; independent of Part 1 |
| 5 | 13, then 14 ∥ 15 | 14 and 15 touch different files (except the test file; add tests in separate sections) |
| 6 | 16 | After 11 and 13–15 |

Critical path: Task 1/2 → Task 4 → Task 11.

## Notes
- Display-only grouping means Wave 2 view tasks work on legacy data without
  any migration.
- Task 6 pointed the Add/Edit buttons on `view_consequences.html` at the
  manage page (the template's `url_for` calls to removed endpoints would have
  500'd the page). Task 7 still removes the modal markup/JS and groups rows.
- Use separate new test files per task to avoid conflicts in `tests/test_bia_routes.py`
  (only Task 6 edits it).
- Deferred: CSV import label splitting, DB uniqueness constraint, legacy data
  merge migration.
- Test infra (53793aa): shared `login` fixture fixed. Known pre-existing
  failures to ignore when judging evidence: 7 stale tests in
  `test_bia_routes.py` (old `/bia/<id>` URL, author-less BIAs need admin),
  10 SSP fixture errors (`template.index`), `test_no_eager_translations`
  (matches itself), 3 in `test_bia_forms.py`. New route tests must log in as
  the BIA's author (`ContextScope(author=login)`).

## Progress
- [x] Task 1: `group_consequences()` + `category_label()` helpers + tests (76a726a)
- [x] Task 2: `save_cia_consequence()` helper + tests
- [x] Task 3: Translation keys (en/nl) (3439be7)
- [x] Task 6: Remove JSON endpoints, redirect `/consequences/new`
- [x] Task 4: Manage page route — group edit, create→edit, preselect
- [x] Task 4b: Manage page template — grouped list
- [x] Task 5: Group delete
- [x] Task 7: Component consequences page — read-only grouped
- [x] Task 8: All-consequences page — grouped (paginates by component)
- [x] Task 9: BIA detail (and item export) — grouped, plus group counts
- [x] Task 10: Global consequences export — grouped (detailed + summary counts)
- [x] Task 11: Cleanup, full validation, docs (confirmed by engineer 2026-10-21; manage-page tests pass, no removed key still referenced)
- [x] Task 12: Duration parser + `Component` recovery source
- [x] Task 13: Availability forms: pre-fill, save rule, hints
- [x] Task 14: Manual marker in tables and HTML/PDF exports
- [ ] Task 15: Summary export precedence + CSV source columns
- [ ] Task 16: Docs + full validation (Part 2)
