---
feature: 20261119-073747-affected-assets-list-add-overlay
status: planned
created: 2026-11-19
chunk_size: adaptive
total_tasks: 5
estimated_lines: 265
---

# Affected Assets List with "Add component" Overlay Tasks

## Overview

This replaces the native multi-select on `/risk/<id>/edit` (Related
components) and `/threat/<id>/scenarios/<id>/edit` (Threatened assets) with a
list of the selected items, a × button per row, and an "Add component" overlay.
It is a template and JS change only. Routes, forms and validation stay the same.
Decisions: 20261119-0740, 0741 and 0742.

## Task List

### Foundation

#### Task 1: Picker macro and translations
- **Estimate:** ~70 lines
- **Files:** `scaffold/templates/partials/asset_picker.html` (new),
  `scaffold/translations/en.json`, `scaffold/translations/nl.json`
- **Description:** Add the macro
  `asset_picker(field, add_label, readonly=False, readonly_note=None)`.
  - Wrapper `<div data-asset-picker>` containing:
    - the field rendered with `class="hidden"`
    - `<ul data-asset-picker-list>` with the server-rendered selected options,
      so the list shows before the JS runs
    - `<p data-asset-picker-empty>` for the empty state
    - when not read-only, an Add button with
      `data-modal-target="#<field.id>-picker-modal"`
  - The overlay: `.modal` markup copied from `bia/context_form.html`, holding a
    search `<input data-asset-picker-search>`, `<div data-asset-picker-options>`,
    an Add button `[data-asset-picker-confirm]` and Cancel `[data-modal-close]`.
  - When `readonly`, the macro renders no × buttons, no Add button and no
    overlay. If `readonly_note` is given, it renders the note.
  - Render `field.errors` under the list. Make the list `aria-live="polite"`.
    Give the overlay list a 60vh max height with scrolling. Use only theme
    variables (decision 0800).
  - Translation keys go under `asset_picker.*`: add_component, add_asset,
    title_component, title_asset, search, confirm, cancel, empty_selected,
    empty_available, no_matches, remove ("Remove {label}"), readonly_note,
    open_scenario.
- **Depends on:** None
- **Acceptance:** The macro imports and renders without errors. All keys exist
  in en and nl.
- **Evidence:** The rendered-HTML assertions in Tasks 3 and 4 pass. A JSON key
  check on both locale files passes.

#### Task 2: Picker JS
- **Estimate:** ~70 lines
- **Files:** `scaffold/static/js/ui.js`
- **Description:** Add `bindAssetPickers()` and call it from
  `DOMContentLoaded`, before `bindModalTriggers` so this listener runs first.
  For each `[data-asset-picker]`:
  - `renderList()`: build a row for each selected `<option>` (label plus a ×
    button that sets `selected = false` and renders again), and toggle the
    empty state.
  - On the Add button click, rebuild the overlay checkboxes from the unselected
    options and clear the search. `openModal` emits no event, so the picker
    does this in its own listener.
  - The search hides option rows whose label does not contain the query,
    case-insensitive.
  - Confirm sets `selected = true` for the checked options, calls
    `window.tailwindUI.closeModal(modal)` and renders the list.
  - Use `textContent` for labels, never `innerHTML`, because labels are user
    data.
  - Focus (decision 0800): opening moves focus to the search, closing returns
    it to the Add button, and after × focus moves to the next row's ×, or the
    previous row's ×, or the Add button. Rows follow choice order. Show the
    "no matches" line when the search matches nothing.
- **Depends on:** Task 1
- **Acceptance:** In the browser, add and remove work, Cancel and Esc discard
  changes, and the posted form has the expected ids.
- **Evidence:** Manual browser check on both edit pages, with the result written
  in the task notes. No JS errors in the console.

### Wiring

#### Task 3: Scenario edit page [P]
- **Estimate:** ~50 lines
- **Parallel:** Can run with Task 4
- **Files:** `scaffold/apps/threat/templates/threat/scenario_form.html`,
  `scaffold/apps/threat/routes.py`, `tests/test_threat_routes.py`,
  `tests/test_threat_pasta_scenarios.py`
- **Description:** Replace the `form.asset_ids(...)` render at line ~165 with
  `asset_picker(form.asset_ids, add_label="Add asset", ...)` when `scenario`
  is set. Otherwise keep the current select. In `scenario_edit`
  (`threat/routes.py` ~L1017), reject an empty `asset_ids` with a field error
  instead of silently keeping the old assets (decision 0800, CHK001). Legacy
  exemption: if the scenario has a legacy `asset_id` and no `assigned_assets`,
  keep the existing backfill and raise no error. The create route stays
  unchanged.
- **Depends on:** Tasks 1, 2
- **Acceptance:** The edit page shows the picker with the assigned assets
  listed. The new page shows the native select. Posting `asset_ids` still
  updates `assigned_assets`. Posting an empty `asset_ids` re-renders the page
  with an error, and the assets are unchanged. The legacy test
  `test_legacy_single_asset_scenario_saves_without_reassignment` still passes.
- **Evidence:** New pytest cases pass. `tests/test_threat_routes.py`,
  `tests/test_threat_pasta_scenarios.py` and `tests/test_threat_risk_sync.py`
  pass.

#### Task 4: Risk edit page and read-only synced risk [P]
- **Estimate:** ~45 lines
- **Parallel:** Can run with Task 3
- **Files:** `scaffold/apps/risk/templates/risk/form.html`,
  `tests/test_risk_routes.py`, `tests/test_threat_risk_sync.py`. The template
  already gets `linked_scenario_url`, which points to `scenario_detail`, so no
  route change is needed.
- **Description:** In edit mode (`risk` is set), render
  `asset_picker(form.component_ids, ..., readonly=form.managed_by_threat,
  readonly_note=...)` with add_label "Add component". The note links to the
  linked scenario's **detail** page. Remove the "Linked components" summary
  block (~L430) in edit mode (decision 0800). Create
  mode keeps `render_field_with_help`.
- **Depends on:** Tasks 1, 2
- **Acceptance:**
  - A manual risk edit has the list and the Add button.
  - A threat-linked risk shows the components with no Add or × buttons, and
    shows the scenario link.
  - The create page is unchanged.
  - Saving still works, including the "no components" validation error.
- **Evidence:** New pytest cases pass. `tests/test_risk_routes.py`,
  `tests/test_threat_risk_sync.py` and `tests/test_risk_actions.py` pass.

### Polish

#### Task 5: Docs, release notes, graph update
- **Estimate:** ~30 lines
- **Files:** `docs/risk.md`, `specs/20261119-073747-affected-assets-list-add-overlay/release-notes.md` (new)
- **Description:** Document the new picker and the read-only behaviour for
  threat-linked risks. Write release notes (no migration). Run
  `graphify update .`.
- **Depends on:** Tasks 3, 4
- **Acceptance:** The docs match the behaviour.
- **Evidence:** The full pytest suite passes. The graph update ran.

## Notes
- The open question is resolved: component labels already read
  "<BIA> - <component>" (`component_choice_label`), so the overlay shows the
  BIA without extra work.
- A disabled select is not submitted. That is fine for threat-linked risks,
  because the sync owns the value.
- Deferred: the picker on the create pages, the threat finding form, and
  creating new assets inline.

## Progress
- [x] Task 1: Picker macro and translations
- [x] Task 2: Picker JS
- [ ] Task 3: Scenario edit page
- [ ] Task 4: Risk edit page and read-only synced risk
- [ ] Task 5: Docs, release notes, graph update

## Implementation Log
- Task 2: the picker owns its overlay because the ui.js modal helpers style
  nothing (decision 0742 amendment). About 145 lines instead of ~70. Evidence:
  27/27 headless Chromium checks against the real macro, ui.js and compiled
  Tailwind CSS (scratchpad `drive.py`, not committed). The existing failure
  `test_threat_routes.py::test_csv_export_includes_plural_columns`
  (DetachedInstanceError) was already there before this feature.
