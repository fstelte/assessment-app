---
type: checklist
domain: general
feature: 20261021-142248-description-bia-consequences
created: 2026-10-21
status: completed
---

# General Requirements Quality Checklist

**Purpose:** Validate that the requirements for CIA-grouped consequences with
category labels are complete, clear and consistent before implementation.
**Feature:** 20261021-142248-description-bia-consequences

## Completeness

- [x] CHK001 - Does the design say whether a consequence needs at least one category label, or whether zero labels is allowed? Legacy rows can have an empty `consequence_category`. [Gap, Design §Data Model]
- [x] CHK002 - Are requirements defined for category values outside the six choices (e.g. capitalised `Operational` in test fixtures, free text from CSV import), both for the union ordering ("choice order") and for chip display? [Gap, Design §group_consequences]
- [x] CHK003 - Is the display of label chips specified: raw stored key or a localised label (en/nl)? [Gap, Constitution IV]
- [x] CHK004 - Does the design define whether a component with no consequence for a CIA property shows an empty or placeholder row in grouped views, or no row? [Gap, Design §Templates] → **Resolved:** no row (Design §Rules "Missing property"; matches the implemented `group_consequences`).
- [x] CHK005 - Are requirements defined for editing or deleting the "not set" group (records with an empty or unknown property), given that the form requires a property? [Gap, Design §group_consequences]
- [x] CHK006 - Does the design say what the delete confirmation tells the user when a group contains several records? [Gap, Decision consequence-edit-as-cia-group] → **Resolved:** Design §Rules "Delete confirmation". The manage page currently says "Delete this component?"; fix scheduled in Task 11.
- [x] CHK007 - Is the behaviour defined for invalid `component_id` / `security_property` preselect parameters (wrong BIA, unknown property)? [Gap, Design §manage_item_consequences]

## Clarity

- [x] CHK008 - Is "highest impact" defined for values that `get_impact_level` doesn't recognise, and for a group where only some records have a realistic value? [Clarity, Design §group_consequences]
- [x] CHK009 - Is the joined-justification format fully specified (separator, de-duplication by exact text or trimmed text, order by record id)? [Clarity, Design §group_consequences]
- [x] CHK010 - Is "re-render in edit mode with the user's submitted labels added to the union" clear about whether the user's submitted *impacts and justifications* are kept or replaced by the existing group's values? [Clarity, Design §manage_item_consequences]
- [x] CHK011 - Is the sort order of grouped rows specified for every screen, in particular `all_consequences` and the global export where BIA is an extra level? [Clarity, Tasks §Shared Contracts 1]

## Consistency

- [x] CHK012 - Does the location of `save_cia_consequence` agree between the design ("routes.py (or utils.py)") and the tasks (utils.py)? [Consistency, Design §Components vs Tasks Contract 3]
- [x] CHK013 - Does the design ("delete per group where it exists today" for `context_detail.html`) agree with Task 9 ("read-only, as today")? [Consistency]
- [x] CHK014 - Is the one-consequence-per-CIA rule consistent with CSV/SQL import, which can still create several rows per property? Is that explicitly accepted as converge-on-edit? [Consistency, Design §API/Interface "Unchanged"]
- [x] CHK015 - Are the grouped HTML/PDF exports and the ungrouped CSV/SQL exports reconciled, so that both carry "the same meaning and terminology" as the UI? [Consistency, Constitution IV]
- [x] CHK016 - Is the merge hint ("N records, will be merged on edit") specified as UI-only, or does it also appear in read-only views and exports? [Consistency, Design §Templates]

## Coverage (edge cases & non-functional)

- [x] CHK017 - Are concurrent edits addressed: a group's `group_ids` going stale because a record was added or deleted between GET and POST? [Edge Case, Gap]
- [x] CHK018 - Is the retarget rule (changing the component or property while editing) defined for the case where the *source* group is legacy multi-row and the target is empty? [Edge Case, Design §manage_item_consequences]
- [x] CHK019 - Does the design state which roles can delete a group from `all_consequences` (cross-BIA view), and that `_can_edit_context` applies per group? [Security, Constitution II]
- [x] CHK020 - Is the audit trail for a merge (one update plus N-1 deletes) shown to be enough to reconstruct the pre-merge state, or is an explicit "merged" audit event needed? [Security/Audit, Constitution II]
- [x] CHK021 - Are redirect requirements defined for `/consequences/new` when the user lacks edit rights (flash + target) and that `return_to` is still validated through `_safe_return_target`? [Security, Design §Removed]

## Measurability

- [x] CHK022 - Does every user story map to at least one acceptance criterion in tasks.md (e.g. the "export reader" story → Tasks 9/10)? [Acceptance]
- [x] CHK023 - Is the doc update in Task 11 tied to a specific file under `docs/`, so the constitution's documentation gate can be checked objectively? [Measurability, Constitution V]

## Summary

- **Total Items:** 23
- **Focus Areas:** label semantics, merge rules, grouped display, import/export consistency, audit/authorization
- **Key Gaps Identified:**
  - Required-label rule and handling of unknown or legacy category values (CHK001–003)
  - Stale `group_ids` under concurrent edits (CHK017)
  - Two small design/tasks inconsistencies (CHK012, CHK013)
  - Whether a merge needs its own audit event (CHK020)
