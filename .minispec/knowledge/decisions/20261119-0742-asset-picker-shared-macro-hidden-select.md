---
type: decision
id: 20261119-0742-asset-picker-shared-macro-hidden-select
date: 2026-11-19
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/templates/partials/asset_picker.html
  - scaffold/static/js/ui.js
tags: [ui, jinja, javascript]
participants: [Ferry Stelte, Claude]
---

# One shared macro drives the picker, and the hidden select is still what gets submitted

## Context

Both pages need the same list, overlay and behaviour. `ui.js` already opens and
closes modals through `data-modal-target` and `data-modal-close`, and the BIA
pages use it.

## Options Considered

- **A: Shared Jinja macro with the hidden native select (chosen).**
- B: Separate markup in each template. Rejected because it duplicates the
  markup and the JS.

## Decision

- The macro `asset_picker(field, add_label, readonly=False, readonly_note=None)`
  renders three things: the original `<select multiple>` (hidden, still named
  and submitted as before), the selected list, and an overlay that uses the
  existing modal classes and attributes.
- A small handler in `ui.js` (`[data-asset-picker]`) builds the list and the
  overlay from the select's `<option>`s and sets `option.selected` on add and
  remove. No new endpoints.
- Server validation does not change: `_resolve_components_for_edit`,
  `validate_component_ids` and `set_scenario_assets`.

## Consequences

### Positive
- ✅ Routes, forms and existing tests stay as they are.
- ✅ The overlay uses the modal system the app already has.

### Negative
- ⚠️ The picker does not work without JS. That matches the rest of the app's
  modals.

## Related Decisions

- [[20261119-0740-affected-assets-list-with-add-overlay]]
