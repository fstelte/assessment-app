---
type: decision
id: 20261021-1424-consequence-edit-as-cia-group
date: 2026-10-21
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/bia/routes.py
  - scaffold/apps/bia/templates/bia/manage_item_consequences.html
  - scaffold/apps/bia/templates/bia/view_consequences.html
  - scaffold/apps/bia/templates/bia/manage_component_consequence.html
tags: [bia, consequences, ui, data]
participants: [Ferry Stelte, Claude]
---

# Consequences are edited per CIA group; one consequence per CIA property per component

## Context

The overview groups consequences by (component, security property); see
20261021-1424-consequence-overview-grouped-by-cia. Legacy data has one row per
category, so a group can contain several records whose impacts and
justifications may differ.

## Options Considered

### Edit interaction
- Expandable sub-rows with per-record edit: keeps records separate, but adds UI
  complexity.
- **Edit the group as one (chosen):** the edit form covers the whole group, and
  saving replaces all of its records with one row.
- Read-only overview with editing elsewhere: splits the workflow.

### Creating a property that already exists
- **Redirect to edit (chosen):** if the component already has a consequence for
  that property, the user is sent to the group edit instead of creating a new
  row.
- Allow it and merge on the next edit: silent loss of impacts or
  justifications.
- Merge on create: hidden write semantics.

### Prefill when merging a legacy group
- **Max + union + join (chosen):** labels are the union of all records; worst
  case and realistic are the highest values (via `get_impact_level`);
  justifications are the distinct non-empty texts joined with a blank line.
- First record only: can drop justifications.

## Decision

- The app enforces one consequence per (component, CIA property). There is no
  DB constraint and no data migration. Legacy groups converge when they are
  next edited.
- The edit form is prefilled with the merged values. The user reviews them, and
  saving deletes the other records in the group and keeps one row.
- Delete on a grouped row deletes the whole group.
- At least one label is required on create and edit.
- Stale group protection: if the group's record ids changed between GET and
  POST, the edit is not saved. The form reloads with fresh merged values.
- Audit: a merge is recorded as an update of the surviving row plus a delete of
  each other row (existing hooks, no new event type).
- CSV/SQL import may still create several rows per property. That is accepted;
  they converge on the next edit.

## Consequences

- No silent data loss: the merged values are visible in the form before save.
- Legacy data still shows correctly through the grouped display.
- The JSON endpoints and the HTML form must apply the same rules (a shared
  helper).
