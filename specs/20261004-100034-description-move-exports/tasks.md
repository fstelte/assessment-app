---
feature: 20261004-100034-description-move-exports
status: planned
created: 2026-10-04
chunk_size: adaptive
total_tasks: 3
estimated_lines: 185
---

# Move Global Exports to the Landing Page – Tasks

## Overview

Move the nine global BIA export reports from the `/bia/index` "Exports" card to
the root landing page (`template.index`). Show them only to logged-in users,
grouped into three themed cards with inline format links. Template,
translation and test changes only. **No routes are touched.** See
[design.md](design.md) and decision `20261004-1005-landing-page-exports-layout`.

## Task List

### Foundation

#### Task 1: Translation keys for the landing-page exports
- **Estimate:** ~60 lines
- **Files:** `scaffold/translations/en.json`, `scaffold/translations/nl.json`
- **Description:** Add `app.home.exports.*` keys: `title`, `intro`,
  `groups.impact`, `groups.inventories`, `groups.architecture`, and one label
  per report (`cia_detailed`, `cia_summary`, `availability_detailed`,
  `availability_summary`, `data_inventory`, `component_inventory`,
  `dependencies`, `tiers`, `authentication`). Base the wording on the existing
  `bia.dashboard.sidebar.export_*` strings. Dependencies and Tiers get proper
  keys and lose their hardcoded English labels.
  **Do not delete** existing `bia.dashboard.sidebar.export_*` keys.
  `TIERING_TRANSLATION_KEYS` in `tests/test_bia_component_tier.py` still checks
  `bia.dashboard.sidebar.export_component_inventory`, and the per-BIA dropdown
  still uses `bia.dashboard.sidebar.exports`.
- **Depends on:** None
- **Acceptance:** Both files are valid JSON and have the same key set under
  `app.home.exports`.
- **Evidence:** A new pytest test asserts every `app.home.exports.*` key exists
  in both `en.json` and `nl.json`. Existing translation tests
  (`test_tiering_translation_keys_exist_in_both_locales_with_matching_placeholders`)
  still pass.

### Core Implementation

#### Task 2: Landing page "Reports & exports" section + tests
- **Estimate:** ~110 lines (≈80 template, ≈30 tests)
- **Files:** `scaffold/apps/template/templates/template/index.html`,
  `tests/test_bia_component_tier.py`, `docs/deployment.md`, new test in `tests/` for the landing page
  (or add to an existing BIA routes test module)
- **Description:**
  - Wrap the section in
    `{% if current_user.is_authenticated and 'bia' in registered_blueprints() %}`.
  - Define the reports once as a `{% set reports = [...] %}` structure
    (group → items → formats with endpoint + kwargs) and render it in a loop.
  - Layout: responsive grid (1 col mobile, 3 col `lg`), one card per group,
    each row = report name + pill links (`fa-file-code` HTML, `fa-file-pdf`
    PDF, `fa-file-csv` CSV) in the existing surface/border token style.
  - No JavaScript.
  - Move `test_dashboard_offers_component_inventory_csv_html_and_pdf` so it
    checks `/` instead of `/bia/index`, and rename it.
  - Docs (constitution: user-visible change): add a bullet under
    `docs/deployment.md` → "BIA Export Artefacts" saying the global reports
    are now on the home page for signed-in users. Routes are unchanged.
- **Depends on:** Task 1
- **Acceptance:** Logged-in `GET /` contains links to all 9 reports in every
  format from the design table. Anonymous `GET /` contains no `/bia/export_`
  links and still returns 200.
- **Evidence:** New/updated pytest tests pass. Visual check of `/` in light
  and dark theme, desktop and mobile widths.

#### Task 3: Remove global exports from the BIA dashboard + test [P]
- **Estimate:** ~-85 / +15 lines
- **Parallel:** Can run with Task 2 (different template files)
- **Files:** `scaffold/apps/bia/templates/bia/dashboard.html`,
  `tests/test_bia_routes.py`
- **Description:**
  - Remove the third `bia-dashboard-actions__item` (global Exports card).
  - Remove the "Exports" `bia-chip` from the hero.
  - Change `.bia-dashboard-actions` media rule from `repeat(3, …)` to
    `repeat(2, …)`.
  - **Keep** the per-context Exports dropdown on each BIA card and the
    `extra_js` dropdown script.
  - Add a test: `/bia/index` doesn't contain `export_all_tiers`,
    `export_all_consequences`, `export_component_inventory`, etc., but still
    contains per-context `export_item` / `export_bia_sql` links.
- **Depends on:** None (but merge with/after Task 2 so exports are never
  missing from the UI)
- **Acceptance:** Dashboard renders with two balanced action cards. Per-BIA
  export dropdown still opens.
- **Evidence:** New test passes. Full `pytest` suite green. Visual check of
  `/bia/index`.

## Notes
- No route, permission or URL changes. Bookmarked export URLs keep working.
- The dropdown JS stays on the dashboard because the per-BIA dropdown uses it.
  The landing page needs none.
- Run `graphify update .` after implementation.
- Deferred: putting exports in the top navigation (design open question).

## Progress
- [x] Task 1: Translation keys for the landing-page exports
- [x] Task 2: Landing page "Reports & exports" section + tests (visual check pending)
- [ ] Task 3: Remove global exports from the BIA dashboard + test
