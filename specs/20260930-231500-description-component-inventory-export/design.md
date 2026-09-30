---
feature: component-inventory-export
status: planned
created: 2026-09-30
decisions:
  - 20260930-2315-component-inventory-export-scope
---

# Component Inventory Export Design

## Overview

A new BIA export, "Component inventory", holds the same data as the existing
Data Inventory CSV but drops the "Beheer" (technical administrator) column and
adds each component's effective tier, the tier's source (component or
inherited from the BIA) and whether the authentication mechanism is also used
for authorisation. It can be downloaded as CSV, HTML or PDF from a single
dropdown in the dashboard sidebar. The existing Data Inventory export stays
unchanged.

## User Stories

- As a BIA user, I want to download an inventory of all components with their
  tier so that I can see which systems fall into which tier.
- As a BIA user, I want to see whether a component's tier was set on the
  component or inherited from the BIA so that I can find components that still
  need an explicit tier.
- As a BIA user, I want to see whether a component's authentication also
  covers authorisation so that I can review access control per system.
- As a BIA user, I want the same inventory as HTML or PDF so that I can share
  it as a readable report, like the other exports.

## Components

### Route `bia.export_component_inventory`

`GET /export_component_inventory?format=csv|html|pdf`, with `@login_required`.
Defaults to `html`, like the other report exports.

1. Query the components of non-archived BIAs, as `export_data_inventory` does,
   with `joinedload` on `context_scope` → `tier`, `tier`,
   `authentication_method` and `environments` → `authentication_method`.
2. Sort by BIA name, then component name (case-insensitive).
3. Build one list of row dicts (see Data Model). The CSV and the template
   both use this list.
4. `format=csv`: write the headers and rows with `csv.writer` (comma
   delimiter, like the existing inventory) to
   `ensure_export_folder() / Component_Inventory_<YYYYmmdd_HHMMSS>.csv`,
   encoded as **UTF-8 with BOM** (`utf-8-sig`) so Excel shows Dutch characters
   correctly, and `send_file` it as an attachment. Every text cell that starts
   with `=`, `+`, `-` or `@` gets a `'` in front of it, so spreadsheets do not
   run it as a formula (CSV only; HTML/PDF show the raw value).
5. Any other `format` value (`html`, `pdf`, missing or unknown) renders
   `bia/export_component_inventory.html` with `export_mode=True` and
   `export_css=_load_export_css()`, then returns
   `_send_export_response(html, "Component_Inventory_<ts>.html")`. That
   function sends PDF for `format=pdf` and HTML for everything else, so an
   unknown value falls back to HTML. If Playwright is unavailable, the
   existing flash message and redirect behaviour applies.
6. `log_event(action="bia.exported", entity_type="bia_component_inventory",
   details={"format": <fmt>, "filename": <name>})` and `db.session.commit()`.
   `<fmt>` is the format actually sent (`csv`, `html` or `pdf`).

Access: `@login_required` only, like every other BIA export. The export covers
all non-archived BIAs, not only those the user can edit.

### Template `bia/export_component_inventory.html`

A standalone export page that follows the existing export templates (e.g.
`export_authentication.html`): a title, the generation timestamp and one table
with the columns below, in the same order as the CSV. If there are no
components, it shows the table header and a single "no components" line. The
CSV then contains only the header row.

PDF layout needs no extra work: `html_to_pdf_bytes` renders at 1280px wide
into one page sized to the content, so 8 columns fit without an orientation
setting.

### Dashboard entry

A new `data-export-dropdown` block in the sidebar exports list of
`bia/dashboard.html`, placed after the existing exports. It has three entries:
CSV (`format='csv'`), HTML and PDF (`format='pdf'`), with the same icons and
classes as the other dropdowns.

### Translations

New keys in `en.json` and `nl.json`:
- the sidebar button label
- the report title
- the column headers
- the tier source values "Component" and "BIA"
- the empty-state line ("no components")

All new keys live under `bia.export.component_inventory.*`, including a new
`not_set` key; there is no shared "Not set" key to reuse. Reuse
`bia.common.yes` / `bia.common.no` and `bia.export.generated_at` for the
timestamp.

### Documentation

Add an entry to `docs/history.md` describing the new export.

## Data Model

No schema changes. Each row is computed per component:

| Column | Source |
|---|---|
| BIA | `component.context_scope.name` |
| Component | `component.name` |
| Information | `component.info_label.get_label()`, else `component.info_type`, else "Not set" |
| Owner | `component.info_owner` or "Not set" |
| Authentication | `_describe_authentication(component)` or "Not set" |
| Tier | `component.effective_tier.get_label()` or "Not set" |
| Tier source | "Component" if `component.tier_id` is set, "BIA" if `effective_tier` comes from the BIA, empty if there is no tier |
| Authorisation | Yes/No from `_resolve_component_authorization_usage(component)[0]` |

- **Empty values:** every missing value shows the translated "Not set",
  never "N/A". This differs on purpose from the old Data Inventory.
- **Translated text:** headers, "Not set", Yes/No and tier source values
  follow the current locale in the CSV, HTML and PDF. So does the tier label
  (`TIER n > <translated name>`), which means filtering a CSV on tier names
  depends on the exporting user's language.
- **Tier source:** the rule is literal. A component with its own `tier_id`
  shows "Component" even when that tier equals the BIA tier.
- **Environment for Authentication and Authorisation:** both come from the
  existing resolvers, which use the primary enabled environment in the order
  production > acceptance > test > development. Authentication falls back to
  the first environment with a method set, so the two values may come from
  different environments. A component without enabled environments shows
  "Not set" for Authentication and "No" for Authorisation.
- **Sort order:** BIA name, then component name, both case-insensitive, with
  component id as the final tie-breaker so the output is stable.

## API/Interface

- `GET /bia/export_component_inventory` → HTML attachment (default)
- `GET /bia/export_component_inventory?format=html` → HTML attachment
- `GET /bia/export_component_inventory?format=pdf` → PDF attachment; on a
  Playwright failure, a flash message and a redirect (existing behaviour)
- `GET /bia/export_component_inventory?format=csv` → CSV attachment

The URL prefix is whatever the `bia` blueprint is registered under.

## Out of Scope

- Any change to the existing `export_data_inventory` CSV.
- Exporting the authorisation note.
- The "Beheer" / technical administrator column.
- Importing this format back into the app.

## Testing

- The CSV contains the translated headers and one row per component of
  non-archived BIAs; archived BIAs are excluded.
- Tier and tier source are correct for three cases: a component with its own
  tier, a component that inherits the BIA tier, and a component with no tier.
- Authorisation shows Yes/No from the primary enabled environment.
- The CSV starts with a UTF-8 BOM, missing values show "Not set", and a
  component name starting with `=` is prefixed with `'`.
- With no components, the CSV holds only the header row and the HTML shows
  the "no components" line.
- The HTML export renders and the PDF branch calls `html_to_pdf_bytes`
  (mocked).
- The existing Data Inventory CSV still has its original columns.
- The dashboard shows the new dropdown with CSV, HTML and PDF links.

## Resolved Questions

- An unknown `format` value falls back to HTML, like the other exports; it
  does not return a 400.
- See `checklists/general.md` for the other requirement gaps that were
  resolved on 2026-09-30.
