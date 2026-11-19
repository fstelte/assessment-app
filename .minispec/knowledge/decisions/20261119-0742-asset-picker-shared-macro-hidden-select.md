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
  existing modal classes and attributes. (Amended below: the picker opens
  and closes its own overlay.)
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

## Amendment (2026-11-19, during Task 2)

`ui.js` `openModal` and `closeModal` only toggle a `.show` class, and no CSS
styles it. The BIA modals this design copied open with page-local scripts
instead. So the picker **owns its overlay**:

- The macro uses `data-asset-picker-modal`, `-dialog` and `-close` instead of
  `.modal`, `data-modal-target` and `data-modal-close`.
- `bindAssetPickers` toggles the same Tailwind classes as the BIA modals
  (`opacity-0`, `invisible`, `scale-95`). It closes on Esc (listening on
  `document` while open), backdrop click, × and Cancel.
- The wrapper uses `transition-opacity` and the dialog uses `transition`, not
  `transition-all`. Visibility is inherited, and transitioning it delayed
  focus: the search box was still `visibility: hidden` in the first frame.

The engineer chose this over fixing the shared `ui.js` helpers, which would
also change the DPIA page's modals.

## Related Decisions

- [[20261119-0740-affected-assets-list-with-add-overlay]]
