---
feature: 20261021-142248-description-bia-consequences
status: implemented
created: 2026-10-21
decisions:
  - 20261021-1424-consequence-category-labels-storage
  - 20261021-1424-consequence-overview-grouped-by-cia
  - 20261021-1424-consequence-edit-as-cia-group
  - 20261021-1424-consequence-writes-consolidated-on-manage-page
  - 20261021-1655-tier-goal-prefills-component-rto-rpo
  - 20261021-1655-availability-csv-rto-rpo-source-columns
  - 20261021-1730-rto-rpo-prefill-checklist-gap-resolutions
---

> This branch has two parts. **Part 1** (CIA-grouped consequences, below) is
> implemented. **Part 2** ([Tier RTO/RPO pre-fill](#part-2-tier-rtorpo-pre-fill-with-manual-overrides),
> at the end) is implemented (Tasks 12–16).

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
- **Missing property:** a component with no consequence for a CIA property
  gets **no row** for it in grouped views. There are no empty or placeholder
  rows, because groups are built only from existing records.
- **Delete confirmation:** both delete entry points (manage page,
  `all_consequences.html`) ask about a *consequence*, not a component. They use
  `bia.all_consequences.confirm_delete` ("Delete this consequence? This action
  cannot be undone."). For a group with more than one record, the manage page
  uses `bia.consequences.group.confirm_delete` (next to `merge_hint`: "Delete
  this consequence? All {count} records for this property are removed."), so
  the merge hint and the confirmation agree. The text is passed per button in
  `data-confirm`, not baked into the JS.

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

---

# Part 2: Tier RTO/RPO pre-fill with manual overrides

Decisions: [[20261021-1655-tier-goal-prefills-component-rto-rpo]] (supersedes
[[20260925-0625-tier-goals-drive-component-rto-rpo]]),
[[20261021-1655-availability-csv-rto-rpo-source-columns]].

## Overview

Today the effective tier's RTO/RPO goal always replaces a component's RTO/RPO.
The form shows it read-only, and stored free text is hidden. After this change
the tier goal is a **pre-filled default**. Stored text that differs from the
goal takes effect and is reported as **manually configured** on forms, in-app
tables, HTML/PDF exports and the availability CSV. Existing stored values are
not changed.

## User Stories

- As a BIA owner, I want the RTO/RPO fields pre-filled from the component's
  tier, so that I only type a value when the component deviates.
- As a BIA owner, I want to set an RTO that differs from the tier goal, so that
  the BIA records the real recovery objective.
- As a reviewer, I want to see which components have a manually configured
  RTO/RPO and what the tier goal is, so that I can challenge deviations.
- As a BIA owner, I want to clear the field to go back to the tier goal, so
  that the component follows future tier changes again.

## Components

### `parse_duration_seconds()` (moved and extended)
`_parse_duration` moves out of the availability summary export and becomes
`parse_duration_seconds(text) -> int | None`. It returns seconds, or `None` for
empty or unparseable text. The summary export calls it and treats `None` as
infinity.

- `immediate`, `0`, `none`, `-` (any case) → 0.
- `<number> <unit>`: `.` or `,` as decimal separator, result rounded to an int.
- A bare number other than `0` → `None`.
- Units are matched on the lowercased word after the number, longest prefix
  first:

| Prefix | Unit | Covers |
|---|---|---|
| `mo`, `maand`, `mnd` | 30 d | month(s), maand(en) |
| `mi`, `m` | 60 s | min, minute(s), minuut, minuten |
| `s` | 1 s | s, sec, second(s), seconde(n) |
| `h`, `u` | 3600 s | hour(s), uur, uren |
| `d` | 1 d | day(s), dag(en) |
| `w` | 7 d | week(s), weken |
| `y`, `j` | 365 d | year(s), jaar, jaren |

Months used to be read as minutes; that changes on purpose.
See [[20261021-1730-rto-rpo-prefill-checklist-gap-resolutions]].

It lives next to `format_duration_seconds` in
`scaffold/apps/bia/models/__init__.py`, because the model needs it and `models`
must not import `bia.utils`.

### `Component` recovery helpers in `scaffold/apps/bia/models/__init__.py`
- `recovery_source(field) -> "tier" | "manual" | "free_text" | None`, where
  `field` is `"rto"` or `"rpo"`:
  - stored text non-empty, goal exists, `parse_duration_seconds(text) == goal` → `tier`
  - stored text non-empty, goal exists, otherwise → `manual`
  - stored text non-empty, no goal → `free_text`
  - stored text empty, goal exists → `tier`
  - neither → `None`
- `_effective_recovery`: stored text if non-empty, else the formatted goal,
  else `None`. Stored text that matches the goal is shown as typed.
- `tier_goal_display(field) -> str | None`: the formatted goal, for the hints
  and the "tier goal is …" text.
- Convenience properties `rto_source` / `rpo_source` for templates.

### Availability form handling in `scaffold/apps/bia/routes.py`
- `_tier_goal_notes(component)` keeps its shape (`{"rto": str|None, "rpo": …}`).
  It now means "hint text", not "locked".
- **GET** (`manage_item_availability`, `manage_component_availability`): if the
  stored value is empty and a goal exists, set `form.rto.data` /
  `form.rpo.data` to the formatted goal.
- `_apply_availability`: for RTO and RPO, store `""` when the submitted text
  is empty or parses to the goal; otherwise store it as typed. It no longer
  skips fields that have a goal. `update_availability` (JSON) uses the same
  function, so it gets the same behaviour.
- Availability summary export (`/availability/export?type=summary`): remove the
  "tier goal replaces stored text" branch and compare durations of the
  effective value (goal seconds when nothing is stored, else
  `parse_duration_seconds(stored)`).

### Templates
- `manage_item_availability.html`, `manage_component_availability.html`: drop
  the read-only box. Always render the input, with the existing hint below it
  (`bia.availability.tier_goal`: "From Tier 1: 4 h (inherited from BIA)"). If
  the value is manual, add a second amber line: en "Manually configured;
  differs from the tier goal", nl "Handmatig ingesteld; wijkt af van het
  tierdoel". When a typed value equals the goal it is dropped without an extra
  message; the next GET shows the formatted goal and no manual line.
- Marker macro `_recovery_marker.html` → `recovery_marker(component, field, plain=False)`.
  It renders only when the source is `manual`, as **visible text** directly
  after the RTO or RPO value: en `manual · tier 4 h`, nl `handmatig · tier 4 u`.
  No tooltip.
  - In-app (`plain=False`): the existing amber chip
    (`inline-flex items-center rounded-full border border-amber-400/60 bg-amber-500/10 px-2 py-0.5 text-xs`).
    Used in the `manage_item_availability.html` list, `components.html` (after
    each of RTO and RPO in the "RTO: x / RPO: y" line), `context_detail.html`
    and `requirements.html`.
  - In exports (`plain=True`): plain text in parentheses, so it survives PDF.
    Used in `export_availability_requirements.html` and `context_detail.html`
    when rendered as the item export.
- Terms: "manually configured" is the full term (form), "manual" the short one
  (marker, CSV).
- The availability **summary** export (aggregated per BIA) gets no marker,
  because one value can come from several components. Incident steps copy the
  value without a marker (out of scope). Read-only viewers see the marker the
  same as editors.

### Availability CSV in `scaffold/apps/bia/utils.py`
Append `RTO Source`, `Effective RTO`, `RPO Source` and `Effective RPO`. Source
labels are `tier` / `manual` / `free text` / `not set`, mapped from the
internal `tier` / `manual` / `free_text` / `None`. The `Recovery Time
Objective` / `Recovery Point Objective` columns keep the stored text.

The CSV writes **one row per component**, including components without an
availability record (stored columns empty, effective columns from the tier).
The import ignores the four new columns and **skips rows whose MTD, RTO, RPO
and MASL are all empty**, so those rows don't create empty records.

## Rules

- **No migration.** Stored text stays as is. Text that was hidden behind a goal
  becomes effective again, flagged `manual` when it deviates. This is intended.
- **Revert to tier:** clear the field, or enter a value equal to the goal.
- **Tier changes:** components with empty stored text follow the new goal.
  Components with stored text keep it, and their source is re-evaluated against
  the new goal, so they can switch between `tier` and `manual`.
- **Goal but no availability record:** the effective value is the goal and the
  source is `tier`, so it shows in tables (as now).
- **Imports store text as given.** CSV/SQL import does not normalise text equal
  to the goal to empty. The source is computed when read, so imported "4 h"
  against a 4 h goal is `tier`, and becomes `manual` if the goal later changes.
- **Unparseable text with a goal is `manual`.** This is deliberate: a reviewer
  should look at text the app can't compare (e.g. "next business day").
- **Locale:** the pre-filled value uses the viewer's locale (`4 h` / `4 u`).
  Both parse, so equality doesn't depend on the locale.
- **Weaker and stricter overrides** are flagged the same way. Grading by
  direction is deferred.
- **Goal of 0 s:** `immediate`, `0`, `none` or `-` match it (source `tier`).
- **MTD and MASL:** unchanged.
- **Audit:** nothing new. Changes to `AvailabilityRequirements` use the
  existing hooks.

## Data Model

No schema change. `bia_availability_requirements.rto` / `.rpo` (Text) now mean
"manual or free-text value; empty = follow the tier".

## API/Interface

| Surface | Change |
|---|---|
| Item and component availability pages | Input always editable, pre-filled from the tier goal, manual hint |
| `POST /bia/update_availability/<id>` | Same save rule (through `_apply_availability`) |
| Availability summary export | Uses the new precedence |
| Availability CSV export | +4 columns |
| `Component.effective_rto/rpo` | Stored text wins over the tier goal |
| Incident steps (`incident/services.py`) | No code change; they follow `effective_*` |

Unchanged: SQL export/import, CSV import, BIA clone (copies stored text),
admin tier management.

## Constitution Check

- **Module ownership:** changes stay in `scaffold/apps/bia/`. `incident` only
  reads `effective_*`.
- **Validation:** pytest for `parse_duration_seconds` (units, en/nl,
  unparseable), `recovery_source` (all five branches), pre-fill on GET, the save
  rule (unchanged pre-fill → empty, deviating → stored, cleared → empty), the
  summary export precedence, and the CSV columns. The parser tests are derived
  from the unit table above. The legacy fixture set is: hidden stale text, text
  matching the goal, unparseable text, and no availability record. Update the tests in
  `tests/test_bia_component_tier.py` that assert "tier goal wins" (e.g.
  `test_summary_export_takes_lowest_of_tier_goal_and_stored_text`).
- **Localization:** en/nl keys for the manual badge, the manual hint ("Manually
  configured (tier goal: {value})") and its tooltip. `bia.availability.tier_goal`
  is reused.
- **Docs:** `docs/models.md` (the `Component` / `AvailabilityRequirements`
  entries) and `docs/history.md`, with an explicit behaviour-change note:
  hidden legacy RTO/RPO text becomes effective again, so incident steps and
  summary exports can change.

## Open Questions

None. The checklist gaps are resolved in
[[20261021-1730-rto-rpo-prefill-checklist-gap-resolutions]].
Deferred: grading overrides by direction (weaker vs. stricter); a marker in
the summary export and in incident steps.
