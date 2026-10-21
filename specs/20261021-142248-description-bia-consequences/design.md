---
feature: 20261021-142248-description-bia-consequences
status: planned
created: 2026-10-21
decisions:
  - 20261021-1424-consequence-category-labels-storage
  - 20261021-1424-consequence-overview-grouped-by-cia
  - 20261021-1424-consequence-edit-as-cia-group
  - 20261021-1424-consequence-writes-consolidated-on-manage-page
---

# BIA Consequences per CIA with Category Labels

## Overview

A BIA consequence is recorded against one CIA security property
(Confidentiality, Integrity or Availability). The six consequence categories
(financial, operational, reputation and trust, regulatory, human and safety,
privacy) become multiselect **labels** on that consequence. Today each selected
category creates its own row.

Each component has at most one consequence per CIA property. Every overview
shows one row per (component, property), with the labels as chips and the
highest worst-case and realistic impacts. Legacy data (one row per category)
displays correctly through display-layer grouping. It converges to one row the
next time someone edits it.

All create and edit goes through the BIA manage-consequences page
(`manage_item_consequences`).

## User Stories

- As a BIA owner, I want to record one consequence for Confidentiality and tag
  it with several categories (e.g. Financial + Privacy), so that I don't have to
  repeat the same impact and justification per category.
- As a BIA owner, I want the overview to show C, I and A per component with
  their labels, so that I can read the impact profile at a glance.
- As a BIA owner editing a legacy consequence group, I want the form prefilled
  with the merged values (all labels, highest impacts, all justifications), so
  that I can review them before they are combined into one record.
- As a BIA owner adding a property that already exists for a component, I want
  to land on its edit form, so that I don't create a duplicate by accident.
- As a reader of BIA exports (HTML/PDF), I want the same CIA-grouped view as in
  the app.

## Components

### `group_consequences()` — `scaffold/apps/bia/utils.py`
Pure helper. Input: an iterable of `Consequences`. Output: an ordered list of
groups, one per (component, security_property), in C, I, A order within each
component:

```python
@dataclass
class ConsequenceGroup:
    component: Component
    security_property: str          # "confidentiality" | "integrity" | "availability"
    records: list[Consequences]     # sorted by id
    categories: list[str]           # union, in ConsequenceForm choice order
    worstcase: str | None           # highest via get_impact_level
    realisticcase: str | None       # highest via get_impact_level
    justification_worstcase: str    # distinct non-empty, joined by "\n\n"
    justification_realisticcase: str
    representative_id: int          # records[0].id, used in edit/delete links
```

Used by every overview template (via the route context) and by the edit prefill.
Property matching is `strip().lower()`, the same as `get_cia_impact`. Records
with an unknown or empty property go into a trailing "not set" group per component.

### `category_label()` — `scaffold/apps/bia/utils.py`
Maps a stored category key to its localised label via
`bia.consequence_category.<key>` (keys with spaces use `_`, e.g.
`reputation_and_trust`). Unknown values (legacy capitalised values, free text
from CSV import) are returned as is. Registered as template filter
`consequence_category` in `routes.py` next to `duration`.
`ConsequenceForm` choice labels use the same keys.

### `save_cia_consequence()` — `scaffold/apps/bia/utils.py`
`save_cia_consequence(component, security_property, categories, worst, worst_just, realistic, realistic_just, replace_ids)`:
updates the record with the lowest id in `replace_ids` (or creates one if there
is none), sets `consequence_category = ",".join(categories)`, and deletes the
other ids in `replace_ids`. Runs in one transaction.

### `manage_item_consequences` route (changed)
- **GET `?consequence_id=X`**: resolve X's group (same component and property)
  and prefill the form from `group_consequences()` merged values. A hidden
  field carries the group's record ids.
- **GET `?component_id=Y[&security_property=P]`**: preselect the component (and
  property) for create. This is the redirect target for the old add page.
- **POST create**: if the chosen component already has a consequence for the
  chosen property, do not save. Re-render in edit mode for that group (merged
  prefill, with the user's submitted labels added to the union) and flash
  `bia.flash.consequence_exists_edit`.
- **POST edit**: `save_cia_consequence(...)` with the group's ids. If the user
  changes the component or property while editing and the target already has a
  group, reject with a form error instead of merging silently.
- Remove the `single_category` validation.

### `delete_consequence` (changed)
Deletes every record in the given record's (component, property) group. The
caller pages are the manage page and `all_consequences.html`.

### Removed
- `add_consequence`, `get_consequence`, `edit_consequence` JSON endpoints.
- The add/edit modal and its JS in `view_consequences.html`.
- `manage_component_consequence.html`.
- `/component/<id>/consequences/new` now redirects to
  `manage_item_consequences(item_id=component.context_scope_id, component_id=id)`,
  keeping `return_to`.

### Templates switched to grouped rows
- `manage_item_consequences.html`: editable list with Edit/Delete per group.
- `view_consequences.html`: read-only grouped list plus a "Manage" link.
- `all_consequences.html`: grouped display, delete per group (as today).
- `context_detail.html`: grouped display, read-only (as today; it links to the
  manage page). It is also used by the `export_item` HTML/PDF export.
- `export_all_consequences.html`: grouped display (HTML/PDF).
- `export_item.html` is not rendered by any route, so it is deleted.
- Consequence counts in `components.html` and `context_detail.html` (component
  table) count **groups**, not records.

Row layout: **CIA property** (badge) · **labels** (chips, via the
`consequence_category` filter) · worst case · realistic · justifications.
On the **manage page only**, a legacy group with more than one record shows a
small "N records, will be merged on edit" hint. Read-only views and exports
don't show it.

## Rules

- **Labels required:** create and edit need at least one label. Legacy rows
  with an empty category show no chips and must get a label when edited.
- **Unknown category values** sort after the six known ones (in first-seen
  order), are shown as raw text, and are kept on edit unless the user removes
  them. The multiselect offers only the six choices, so any unknown value is
  dropped once the user saves the edit form.
- **Stale group:** the edit form carries the group's record ids. On POST, if the
  current ids for (component, property) differ from the submitted ones, don't
  save. Reload the edit form with fresh merged values and flash
  `bia.flash.consequence_group_changed`.
- **Audit:** a merge is audited as one update of the surviving row plus a delete
  of each other row, using the existing `Consequences` audit hooks. No new
  event type.
- **CSV/SQL import** can still create several rows per property. That is
  accepted: the grouped display shows them, and they converge on the next
  edit.

## Data Model

No schema change. `bia_consequences.consequence_category` (Text) holds the
lowercase choice keys comma-joined, e.g. `financial,privacy`. Read it through
`Consequences.get_categories()`. The app maintains one row per (component_id,
security_property) for new and edited data; there is no DB constraint.

## API/Interface

| Route | Change |
|---|---|
| `GET/POST /bia/item/<id>/consequences` | Group edit, create→edit redirect, `component_id`/`security_property` preselect |
| `GET /bia/component/<id>/consequences/new` | Now a redirect (302) |
| `POST /bia/delete_consequence/<id>` | Deletes the whole group |
| `POST /bia/add_consequence/<id>`, `GET /bia/get_consequence/<id>`, `POST /bia/edit_consequence/<id>` | Removed |

Unchanged: CSV/SQL export and import (one row per record; labels stay
comma-joined in the "Category of Consequence" column), JSON CIA export,
`get_cia_impact`, `get_max_cia_impact`, `_summary_impacts`, SSP FIPS mapping,
and BIA cloning.

## Constitution Check

- **Module ownership:** all changes are in `scaffold/apps/bia/`.
- **Security/audit:** same `_can_edit_context` checks. Group delete and merge
  are covered by the existing audit hooks on `Consequences` (row update and
  delete). No role changes.
- **Validation:** pytest for `group_consequences` (union, max, join, ordering,
  legacy), create→edit redirect, group edit merges and deletes extras, group
  delete, the `/consequences/new` redirect, and the multi-label round-trip.
- **Localization:** new en/nl keys for the six category labels, the
  exists-flash, the group-changed flash, the merge hint, the "Manage" link and
  the conflicting-target error. Remove keys that are no longer used.
- **Docs:** update `docs/models.md` (the `Consequences` entry).
- **Migration/ops:** none.

## Open Questions

- Should the CSV import start splitting comma-joined labels on the way in?
  It already stores them verbatim, so this is probably fine as is. Check during
  implementation.
- Exact placement of the "Manage" link on `view_consequences.html` (header
  button vs. empty-state link). Decide while implementing.
