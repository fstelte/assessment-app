---
type: decision
id: 20261021-1424-consequence-writes-consolidated-on-manage-page
date: 2026-10-21
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/bia/routes.py
  - scaffold/apps/bia/templates/bia/view_consequences.html
  - scaffold/apps/bia/templates/bia/manage_component_consequence.html
  - scaffold/apps/bia/templates/bia/components.html
  - tests/test_bia_routes.py
tags: [bia, consequences, routes, simplification]
participants: [Ferry Stelte, Claude]
---

# All consequence create/edit goes through the BIA manage-consequences page

## Context

Consequences could be created or edited in five places: the standalone add page
(`/component/<id>/consequences/new`), the JSON add/get/edit endpoints behind the
modal in `view_consequences.html`, and the `manage_item_consequences` form.
Enforcing one consequence per CIA property per component with group edit
(20261021-1424-consequence-edit-as-cia-group) in all of them would mean three
forms to keep in line, including the modal JS.

## Options Considered

### Option 1: Keep all paths and share helpers
- ✅ No change in navigation.
- ❌ Most work; the modal JS needs a 409/redirect-to-edit flow.

### Option 2: Consolidate on the manage page (chosen)
- ✅ One form holds the one-per-CIA, group-edit and merge-prefill rules.
- ✅ Removes the JSON add/get/edit endpoints and the modal JS.
- ❌ Users editing from a component page move to the BIA manage page.

### Option 3: Middle ground (modal kept for display and delete)
- ❌ Still splits the behaviour across two UIs.

## Decision

- Remove the `add_consequence`, `get_consequence` and `edit_consequence` JSON
  endpoints and the add/edit modal in `view_consequences.html`.
- `/component/<id>/consequences/new` becomes a redirect to
  `manage_item_consequences` for that component's BIA, with the component
  preselected. Existing links and `return_to` keep working.
- `view_consequences.html` becomes a grouped read-only list with a "Manage"
  link to the manage page.
- `delete_consequence` stays, but deletes the whole (component, property) group
  of the given record.

## Consequences

- Route tests for `/consequences/new` change from asserting creation to
  asserting the redirect.
- `manage_component_consequence.html` is no longer rendered and can be deleted.
