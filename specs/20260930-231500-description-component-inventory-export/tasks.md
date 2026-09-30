---
feature: component-inventory-export
status: planned
created: 2026-09-30
chunk_size: medium
total_tasks: 2
estimated_lines: 205
---

# Component Inventory Export Tasks

## Overview
Adds the "Component inventory" export: the Data Inventory data without "Beheer",
plus effective tier, tier source (Component/BIA) and authorisation (Yes/No).
Available as CSV, HTML and PDF from one dashboard dropdown. See `design.md` and
decision `20260930-2315-component-inventory-export-scope`.

## Task List

### Foundation

#### Task 1: Route, row building and CSV export
- **Estimate:** ~100 lines
- **Files:** `scaffold/apps/bia/routes.py`, `scaffold/translations/en.json`, `scaffold/translations/nl.json`, `tests/test_bia_routes.py`
- **Description:** Add `export_component_inventory` (`@login_required`) after
  `export_data_inventory`. Query components of non-archived BIAs, with
  `joinedload` on `context_scope` → `tier`, `tier`, `authentication_method` and
  `environments` → `authentication_method`. Sort case-insensitively by BIA
  name, then component name, then component id. Build row dicts with these
  fields; every missing value is the translated "Not set", never "N/A":
  - BIA
  - Component
  - Information (`info_label.get_label()`, else `info_type`)
  - Owner
  - Authentication (`_describe_authentication`)
  - Tier (`effective_tier.get_label()`)
  - Tier source ("Component" if `tier_id` is set, even when it equals the BIA
    tier; "BIA" if the tier is inherited; empty if there is no tier)
  - Authorisation (`_resolve_component_authorization_usage()[0]` → Yes/No)

  For `format=csv`, write the translated headers and rows with `csv.writer`
  (comma delimiter) to `ensure_export_folder() / Component_Inventory_<ts>.csv`
  encoded as `utf-8-sig`, and `send_file` it. Put a `'` in front of every text
  cell that starts with `=`, `+`, `-` or `@`. Log `bia.exported` with
  `entity_type="bia_component_inventory"` and `format="csv"`, then commit.
  Add i18n keys under `bia.export.component_inventory.*` for the headers, the
  tier source values and `not_set` in en + nl, reusing `bia.common.yes/no`.
- **Depends on:** None
- **Acceptance:** `GET /bia/export_component_inventory?format=csv` returns a CSV
  with the 8 translated headers and one row per component of non-archived BIAs.
  It has no "Beheer" column. The existing `export_data_inventory` output is
  unchanged.
- **Evidence:** New pytest tests pass for:
  - the headers
  - archived BIAs being excluded
  - tier and tier source for a component with its own tier, one inheriting the
    BIA tier, and one with no tier
  - authorisation Yes/No, including "No" for a component without enabled
    environments
  - the UTF-8 BOM, "Not set" for missing values, and the `'` prefix on a
    name starting with `=`
  - a header-only CSV when there are no components
  - the unchanged Data Inventory headers

  The full `pytest` suite stays green.

### Integration

#### Task 2: HTML/PDF template and dashboard dropdown
- **Estimate:** ~105 lines
- **Files:** `scaffold/apps/bia/templates/bia/export_component_inventory.html` (new), `scaffold/apps/bia/routes.py`, `scaffold/apps/bia/templates/bia/dashboard.html`, `scaffold/translations/en.json`, `scaffold/translations/nl.json`, `tests/test_bia_routes.py`, `docs/history.md`
- **Description:**
  - Add the standalone export template, following the style of
    `export_authentication.html`: a title, the generation timestamp and one
    table with the same 8 columns in the same order, built from the same row
    dicts. With no rows, show a single "no components" line. No `'` prefix in
    HTML; that is CSV only.
  - For any format other than csv (default `html`; unknown values fall back to
    HTML), render it with `export_mode=True` and
    `export_css=_load_export_css()`, then return
    `_send_export_response(html, "Component_Inventory_<ts>.html")`.
  - Add a `data-export-dropdown` block to the dashboard sidebar exports list,
    after the existing ones, with CSV (`format='csv'`), HTML and PDF
    (`format='pdf'`) entries in the same markup as the other dropdowns.
  - Log `format` as the format actually sent (`html` or `pdf`).
  - Add i18n keys for the report title, the empty-state line and the sidebar
    button label (en + nl); reuse `bia.export.generated_at` for the timestamp.
  - Add a `docs/history.md` entry for the new export (columns, formats, CSV
    encoding and the `'` prefix).
- **Depends on:** Task 1
- **Acceptance:** The HTML export downloads with the columns and values; the
  PDF export returns `application/pdf`; the dashboard shows the dropdown with
  3 working links.
- **Evidence:** New pytest tests pass: the HTML response contains the headers,
  tier and tier source values; with no components it shows the empty-state
  line; `format=pdf` with `html_to_pdf_bytes` mocked returns an
  `application/pdf` attachment named `Component_Inventory_*.pdf`; an unknown
  `format` returns HTML; the dashboard HTML contains all three
  `export_component_inventory` links. The full `pytest` suite stays green.

## Notes
- No schema change, so no migration.
- Row building stays inline in the route; there is no shared helper with
  `export_data_inventory`, which must stay untouched.
- Run `graphify update .` after implementation.
- Deferred: exporting the authorisation note; importing this format.
- **Deviation (implementation):** the tests live in
  `tests/test_bia_component_tier.py`, not `tests/test_bia_routes.py`. The shared
  `login` fixture no longer authenticates, because `/auth/login` redirects local
  accounts to MFA enrolment, so tests using it already fail on the baseline.
  The tier test module has a working `logged_in` fixture and a `_request`
  helper. The new translation keys are also covered by its en/nl parity test.
- **Follow-up (outside this feature):** fix the `login` fixture in
  `tests/conftest.py` so the older `test_bia_routes.py` tests run again.

## Progress
- [ ] Task 1: Route, row building and CSV export
- [ ] Task 2: HTML/PDF template and dashboard dropdown
