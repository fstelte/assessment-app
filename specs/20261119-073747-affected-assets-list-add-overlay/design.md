---
feature: 20261119-073747-affected-assets-list-add-overlay
status: planned
created: 2026-11-19
decisions:
  - 20261119-0740-affected-assets-list-with-add-overlay
  - 20261119-0741-threat-synced-risk-components-read-only-list
  - 20261119-0742-asset-picker-shared-macro-hidden-select
  - 20261119-0800-asset-picker-checklist-gap-resolutions
---

# Affected Assets List with "Add component" Overlay

## Overview

On `/risk/<id>/edit` ("Related components") and
`/threat/<id>/scenarios/<id>/edit` ("Threatened assets"), a list of the selected
items replaces the native multi-select. Each row has a × button to remove it. An
"Add component" button opens an overlay where the user picks more items from
the options already allowed. This is a template and JS change only. Routes,
forms and validation stay the same.

## User Stories

- As a risk owner, I want to see which components a risk affects as a clear
  list, so that I don't have to scan a multi-select for highlighted rows.
- As a threat modeller, I want to add threatened assets through an overlay
  without losing my current selection by accident.
- As a risk owner on a threat-linked risk, I want to see the synced components
  and know where to change them.

## Components

### `scaffold/templates/partials/asset_picker.html`: macro `asset_picker`
`asset_picker(field, add_label, readonly=False, readonly_note=None)` renders:
1. The original `field` (`<select multiple>`), hidden. It is still the submitted
   value, with the same name and the same server-side validation.
2. `<ul data-asset-picker-list>`: one row per selected option, showing the label
   and a × remove button (not shown when `readonly`).
3. An "Add component" button (`data-modal-target`), not shown when `readonly`.
4. The overlay, styled like the BIA modals but opened and closed by the picker
   itself (decision 0742 amendment): a
   search input, a checkbox list of the options not selected yet, and Add and
   Cancel buttons. If every option is already selected, it shows an empty-state
   message.
5. If `readonly_note` is given, the note appears under the list.

### `scaffold/static/js/ui.js`: `[data-asset-picker]` handler
- Builds the list from the selected `<option>`s and keeps it up to date.
- × sets `option.selected = false` and renders the list again.
- When the overlay opens, it fills the checkbox list from the unselected options
  and clears the search.
- The search filters rows by label, case-insensitive.
- "Add" sets `option.selected = true` for the checked rows, closes the overlay
  and renders the list again. "Cancel" or closing changes nothing.

### Call sites
- `risk/form.html`: use the macro only when `risk` is set (edit mode), with
  `readonly=form.managed_by_threat`. When read-only, the note links to the
  linked scenario's **detail** page (decision 0800). The "Linked components"
  summary block is removed in edit mode. Create mode keeps `render_field_with_help`.
- `threat/scenario_form.html`: use the macro only when `scenario` is set, for
  `form.asset_ids`. Create mode keeps the native select.

## UX Details

The label is "Add component" on the risk page and "Add asset" on the scenario
page. For errors, focus, accessibility, search, ordering and sizing, see
decision 20261119-0800.

## Data Model

No changes.

## API/Interface

No new endpoints. The form posts exactly what it posts today.

## Edge Cases

- **Manual risk, every component removed:** the existing
  `validate_component_ids` error comes back after submit. The list's empty
  state reads "No components selected".
- **Ineligible components already linked to a risk:** these are in `choices`
  through `extra_components`, so they show in the list. If one is removed, it
  shows in the overlay again until save. Re-adding it is harmless, because
  `_resolve_components_for_edit` accepts anything in `choices`. After save, it
  is no longer offered.
- **Scenario, every asset removed:** saving is blocked with a validation error
  on `asset_ids` (decision 0800). This is new: an empty submission used to be
  ignored. The exception is a legacy scenario (a legacy `asset_id` and no
  `assigned_assets`), which keeps the existing backfill.
- **Scenario with only the legacy `asset_id`:** the route already pre-fills
  `asset_ids` from it, so it shows in the list.
- **Disabled field (threat-linked risk):** a disabled select is not submitted.
  That is what happens today and is fine, because the sync owns the value.

## i18n

New keys for "Add component", the overlay title, the search placeholder, Add,
Cancel, the empty states and the read-only note. Add them to every locale the
app ships.

## Constitution Compliance

- **Module ownership:** the call sites stay in the `risk` and `threat`
  blueprints' templates. The empty-assets check lives in
  `threat/routes.py:scenario_edit`. The shared macro goes in
  `scaffold/templates/partials/` next to `forms.html`, and the JS goes in the
  existing `scaffold/static/js/ui.js`. No cross-domain shortcuts.
- **Security, roles and audit:** no role or permission changes. The read-only
  note links to the scenario **detail** page so that risk-only users don't get
  a 403. Asset changes are still recorded by the existing `_log_asset_audit`.
  Labels are inserted with `textContent` to avoid XSS.
- **Validation scope:** new pytest cases in `test_threat_routes.py`,
  `test_threat_pasta_scenarios.py`, `test_risk_routes.py` and
  `test_threat_risk_sync.py`, plus a manual browser check for the JS (the repo
  has no JS test harness).
- **Localization:** all new copy uses `_()` with `asset_picker.*` keys in
  `en.json` and `nl.json`.
- **UI language:** Tailwind utilities, theme variables and the existing `.modal`
  pattern. No Bootstrap.
- **Operational and migration impact:** no schema change, migration, setting or
  environment variable. Docs are updated in `docs/risk.md` and the release
  notes.
- **Simpler option rejected:** keeping the native multi-select. It doesn't meet
  the request to see the selected items and add them through an overlay.

## Out of Scope

- Creating new assets or components from the overlay.
- The create pages for risks and scenarios.
- The threat finding form's `asset_ids`.
- Adding components by hand to threat-linked risks.

## Open Questions

- None. Component labels already include the BIA name (`component_choice_label`).
