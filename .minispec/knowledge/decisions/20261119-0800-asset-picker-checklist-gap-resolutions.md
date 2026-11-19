---
type: decision
id: 20261119-0800-asset-picker-checklist-gap-resolutions
date: 2026-11-19
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/threat/routes.py
  - scaffold/templates/partials/asset_picker.html
  - scaffold/static/js/ui.js
  - scaffold/apps/risk/templates/risk/form.html
tags: [risk, threat, ui, accessibility, validation]
participants: [Ferry Stelte, Claude]
---

# Asset picker: resolutions for the UX checklist gaps

## Context

The UX checklist
(`specs/20261119-073747-affected-assets-list-add-overlay/checklists/ux.md`)
found gaps in the picker design. The engineer decided the four key gaps. The
rest are resolved with the defaults below.

## Decision

### Engineer decisions
- **CHK001: empty threatened assets.** The scenario edit page requires at least
  one threatened asset. Submitting an empty `asset_ids` gives a validation error
  on the field, and nothing is saved. Before this, an empty submission was
  silently ignored.
  **Legacy exemption (decided in /minispec.analyze):** if the submission is
  empty and the scenario has a legacy `asset_id` and no `assigned_assets`, the
  existing backfill runs and no error is raised. This keeps
  `test_legacy_single_asset_scenario_saves_without_reassignment` passing. The
  accepted gap is that on a legacy scenario, removing the pre-filled asset is
  still silently backfilled.
- **CHK002: read-only note link.** It points to the scenario **detail** page
  (`threat.scenario_detail`), which every logged-in user can open, not the edit
  page.
- **CHK007: button label per page.** "Add component" on the risk page and "Add
  asset" on the scenario page. Overlay titles match.
- **CHK004 / CHK013: errors and summary.** The macro shows `field.errors` under
  the list. On the risk edit page, the "Linked components" summary block is
  removed, because the list replaces it.

### Defaults
- **CHK003:** read-only note: "These components come from the threatened assets
  of the linked threat scenario." followed by a link "Open scenario". If a
  synced risk has zero components, the list shows `empty_selected` and the note
  stays.
- **CHK005:** a separate "No matching items" line when the search matches
  nothing.
- **CHK006:** list rows follow the choice order (the order of the select's
  options), not the order they were added.
- **CHK008:** the search is a case-insensitive substring match on the full
  label, BIA part included.
- **CHK009:** the overlay option list is capped at `max-height: 60vh` and
  scrolls.
- **CHK010:** changes apply only when the form is saved. No extra "unsaved"
  indicator, matching the rest of the form.
- **CHK015:** opening the overlay moves focus to the search input. Closing it
  returns focus to the Add button.
- **CHK016:** after ×, focus moves to the next row's ×, or to the previous
  row's × if there is none, or else to the Add button.
- **CHK017:** the × button has `aria-label` "Remove <label>". The search has a
  visible label or an `aria-label`. Each checkbox is wrapped in its `<label>`.
- **CHK018:** the list is `aria-live="polite"`.
- **CHK019 / CHK022:** only theme CSS variables (`--color-*`). The overlay is
  full width with a 16px gutter on phones, and × targets are at least 32px.
- **CHK023:** the read-only list is rendered on the server from the selected
  options. The JS skips pickers that have no Add button.

## Consequences

### Positive
- ✅ The × button behaves as users expect: a scenario cannot end up with silently
  kept assets.
- ✅ The read-only link works for every user who can open the risk.

### Negative
- ⚠️ Existing scenarios with no assets (and no legacy `asset_id`) cannot be
  saved from the edit page until an asset is added.
- ⚠️ Legacy single-asset scenarios keep the old silent backfill when the field
  is submitted empty.

## Related Decisions

- [[20261119-0740-affected-assets-list-with-add-overlay]]
- [[20261119-0741-threat-synced-risk-components-read-only-list]]
- [[20261119-0742-asset-picker-shared-macro-hidden-select]]
