---
type: decision
id: 20261119-0740-affected-assets-list-with-add-overlay
date: 2026-11-19
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/risk/templates/risk/form.html
  - scaffold/apps/threat/templates/threat/scenario_form.html
tags: [risk, threat, ui, assets, components]
participants: [Ferry Stelte, Claude]
---

# Affected assets show as a list with an "Add component" overlay

## Context

The risk edit page ("Related components") and the threat scenario edit page
("Threatened assets") both use a native `<select multiple>`. Users cannot see at
a glance which items are selected, and adding one with ctrl-click deselects the
others too easily.

## Options Considered

Overlay content:
- **A: Pick existing items only (chosen).** The overlay is a searchable
  checklist of the options not selected yet.
- B: Pick or create new items inline. Rejected because it needs a new create
  endpoint and validation, and nobody needs it today.

Removal:
- **A: × button per listed row (chosen).** The overlay only adds.
- B: The overlay toggles both ways. Rejected because removing would then take
  two clicks and the list would no longer be the place to edit.

Pages:
- **A: Edit pages only (chosen).** `/risk/<id>/edit` and
  `/threat/<id>/scenarios/<id>/edit`. The create pages keep the native select.
- B: Create and edit pages. The engineer chose to limit scope to edit.

## Decision

- On the two edit pages, the multi-select is replaced by a list of the selected
  items. Each row has a × remove button.
- An add button opens an overlay. It reads "Add component" on the risk page
  and "Add asset" on the scenario page, per
  [[20261119-0800-asset-picker-checklist-gap-resolutions]]. The overlayhas a search box and checkboxes
  for every allowed option that is not selected yet. "Add" adds the checked
  items to the list. "Cancel" or closing the overlay changes nothing.
- The allowed options are the field's existing `choices`: BIA components on the
  risk page, threat-model assets on the scenario page.
- The threat finding form and both create pages keep their current select.

## Consequences

### Positive
- ✅ The selected assets are visible and easy to edit.
- ✅ No backend change, because the allowed options are the existing ones.

### Negative
- ⚠️ Create and edit pages now pick assets differently.
- ⚠️ Nothing can be created from the overlay. New assets still have to be added
  on the threat model or the BIA first.

## Related Decisions

- [[20261119-0741-threat-synced-risk-components-read-only-list]]
- [[20261119-0742-asset-picker-shared-macro-hidden-select]]
- [[20261119-0800-asset-picker-checklist-gap-resolutions]]
