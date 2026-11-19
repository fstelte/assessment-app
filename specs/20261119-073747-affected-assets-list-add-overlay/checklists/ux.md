---
type: checklist
domain: ux
feature: 20261119-073747-affected-assets-list-add-overlay
created: 2026-11-19
status: completed
---

# UX Requirements Quality Checklist

**Purpose:** Check that the UX requirements for the selected-items list and the
"Add component" overlay are complete, clear and consistent.
**Feature:** 20261119-073747-affected-assets-list-add-overlay

## Completeness

- [x] CHK001 - Does the design say what happens when a user removes **every**
  threatened asset on a scenario and saves? Today an empty `asset_ids` is
  ignored (`threat/routes.py` ~L1017), so the old assets stay. [Gap, Design §Edge Cases] ⚠️
- [x] CHK002 - Is the link target of the read-only note defined for users who
  may open the risk but not edit the scenario? Scenario edit requires the admin
  or assessment-manager role. [Gap, Decision 0741] ⚠️
- [x] CHK003 - Is the text of the read-only note defined, including the case
  where a synced risk has zero components? [Completeness, Design §Call sites]
- [x] CHK004 - Does the design say where validation errors for the hidden
  field (for example "invalid components") appear around the picker?
  [Gap, Design §Components]
- [x] CHK005 - Is there a "no results" state for an overlay search that
  matches nothing? It is separate from `empty_available`. [Completeness]
- [x] CHK006 - Is the order of list rows defined: choice order, or the order
  items were added? [Gap]

## Clarity

- [x] CHK007 - Is the button label defined per page? The request says "Add
  component", but the scenario page calls the items "Threatened assets"
  (should it be "Add asset"?). [Clarity, Decision 0740]
- [x] CHK008 - Is "searchable" described: substring or prefix match,
  case-insensitive, and does it match the BIA part of "<BIA> - <component>"?
  [Clarity, Design §JS handler]
- [x] CHK009 - Is the size of the overlay list defined (maximum height,
  scrolling) for BIAs with many components? [Clarity]
- [x] CHK010 - Is it stated whether changes made in the list (× or Add) count
  as unsaved until the form is submitted, and whether the user sees any sign of
  that? [Clarity]

## Consistency

- [x] CHK011 - Do the overlay markup, buttons and close behaviour (Esc,
  backdrop click, Cancel) match the existing `.modal` pattern in
  `bia/context_form.html`? [Consistency, Decision 0742]
- [x] CHK012 - Are the list rows, × buttons and empty state styled the same on
  the risk and scenario pages, apart from the label? [Consistency]
- [x] CHK013 - Does the read-only risk list look like the existing "Linked
  components" summary on the same page, or is that summary now duplicated?
  [Consistency, risk/form.html ~L430]
- [x] CHK014 - Are create and edit pages that differ (native select vs picker)
  called out as an accepted difference everywhere it applies? [Consistency,
  Decision 0740]

## Accessibility

- [x] CHK015 - Are focus rules defined: focus moves into the overlay when it
  opens and returns to the Add button when it closes? [Coverage]
- [x] CHK016 - Is the place where focus lands after a row is removed with ×
  defined? [Gap]
- [x] CHK017 - Are accessible names defined for the × buttons (including the
  item label), the search input and the checkbox rows? [Completeness]
- [x] CHK018 - Is it defined how list changes are announced to screen readers
  (for example an `aria-live` region)? [Gap]
- [x] CHK019 - Do the colours follow the app's theme variables, so the picker
  works in light and dark mode? [Coverage]

## Measurability

- [x] CHK020 - Can each acceptance item for Tasks 3 and 4 be checked from the
  rendered HTML (selectors and attributes named)? [Measurability, tasks.md]
- [x] CHK021 - Is the manual browser check for Task 2 written as a repeatable
  list of steps? [Measurability, tasks.md]

## Coverage

- [x] CHK022 - Is the picker's behaviour at phone width defined (overlay width,
  touch targets for ×)? [Coverage]
- [x] CHK023 - Is the case of a disabled field on a threat-linked risk covered,
  so the read-only list is still built from the selected options? [Edge Case,
  Decision 0741]

## Summary

- **Total Items:** 23
- **Focus Areas:** completeness of states, labels, accessibility, consistency
  with the existing modal pattern
- **Key Gaps Identified:**
  - CHK001: removing every scenario asset does not clear them on save
  - CHK002: the read-only note link may give a 403 for risk-only users
  - CHK004: no place defined for validation errors
  - CHK007: "Add component" vs "Add asset" label on the scenario page

## Resolution

All items are resolved in decision
`20261119-0800-asset-picker-checklist-gap-resolutions`. The engineer decided
CHK001, 002, 004, 007 and 013, and the rest use the defaults recorded there.
The design and tasks are updated to match.
