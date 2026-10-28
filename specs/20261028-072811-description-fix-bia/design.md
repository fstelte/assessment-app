---
feature: 20261028-072811-description-fix-bia
status: implemented
created: 2026-10-28
decisions:
  - 20261028-0730-bia-modal-url-id-substitution
---

# Fix the BIA Component Modal Edit Link

## Overview

On the BIA edit page (`/bia/item/<id>/edit`), clicking a component opens the
view-component modal. Clicking **Edit** in that modal leads to
`/bia/component//edit<id>/edit` and an error page.

**Root cause:** `context_form.html` builds the modal URLs by rendering
`url_for(..., component_id=0)`, removing `0` with `.replace('/0', '/')`, then
appending the id. The edit route puts the id in the middle of the path, so
this produces `/bia/component//edit`, and the code then appends
`<id>/edit` to that. The bug came in with commit `95b1895`.

The fix moves all four modal URLs to a single substitution helper. It replaces
the **last** `/0` path segment of each `url_for` template with the component
id, so it works whether the id is at the end of the path or in the middle.

## User Stories

- As a BIA editor, I want **Edit** in the component modal to open that
  component's edit form so that I can change it without going through the
  components overview.

## Expected URLs

With no URL prefix and component id `42`:

| Modal action       | Route endpoint            | Template (`component_id=0`) | Built URL                 |
|--------------------|---------------------------|-----------------------------|---------------------------|
| View (fetch JSON)  | `bia.get_component`       | `/bia/get_component/0`      | `/bia/get_component/42`   |
| Delete (POST)      | `bia.delete_component`    | `/bia/delete_component/0`   | `/bia/delete_component/42`|
| Edit (link)        | `bia.edit_component_form` | `/bia/component/0/edit`     | `/bia/component/42/edit`  |
| Consequences (link)| `bia.view_consequences`   | `/bia/consequences/0`       | `/bia/consequences/42`    |

Under a forwarded URL prefix (ProxyFix `x_prefix`), `url_for` puts the prefix
in front of each template, and the built URL keeps it. Only the last `/0`
segment is replaced, so a prefix that itself contains a `/0` segment (for
example `/0`) is left alone: `/0/bia/component/0/edit` becomes
`/0/bia/component/42/edit`.

## Components

### `context_form.html` (the `extra_js` block)

- Keep the four `url_for(..., component_id=0)` strings exactly as rendered,
  with no `.replace`.
- Add a helper inside the existing IIFE:
  `function withId(tpl, id) { return tpl.replace(/\/0(?=\/|$)(?!.*\/0(?:\/|$))/, '/' + id); }`
  - `\/0(?=\/|$)` matches only a whole `0` segment, so `/10` and `/05` are
    never matched.
  - `(?!.*\/0(?:\/|$))` makes it the last such segment, so a prefix is never
    matched.
- Build all four URLs with `withId`. Nothing appends path segments by hand.
- **Id source:** `componentId` always comes from a server-rendered
  `data-component-id="{{ component.id }}"` (an integer). The view handler sets
  the edit link, the consequences link and the modal's delete button from the
  same `componentId`, so the three can't disagree.
- **Missing id:** the modal's delete button starts with `data-component-id=""`.
  The view-button handler and `doDeleteComponent` return early, with no
  request and no confirm dialog, when `componentId` is empty or missing.

### Regression test (`tests/test_bia_routes.py`)

The test GETs `/bia/item/<id>/edit` as an editor and asserts:

- Each of the four `var ...Url = '...';` definitions renders the unchanged
  template from the table above, with no trailing `.replace`. (A check for
  `/component//edit` in the body was dropped during implementation. That URL
  is only assembled in the browser, so the check passed even on the broken code.)
- The `withId` regex is extracted from the rendered script and applied in
  Python with id `42` to each template. The results must match the table.
  It is also applied to `/0/bia/component/0/edit`, which must give
  `/0/bia/component/42/edit`.

This tests the shipped regex rather than a copy of it. The `click → withId`
wiring has no automated test because there is no JS harness. The manual check
covers it (see tasks).

## Authorisation and navigation

- **Edit button visibility: unchanged.** The modal only renders on
  `/bia/item/<id>/edit`. Its route (`edit_item`) already redirects users who
  fail `_can_edit_context`, and `edit_component_form` checks it again on the
  server.
- **After saving the component: unchanged.** `edit_component_form` still
  redirects to `/bia/components?scope=<context name>`. Returning to the BIA
  edit page is a possible follow-up, not part of this fix.

## Constitution Check

Every plan has to confirm these five areas (Delivery Workflow and Quality Gates):

| Area | Impact |
|------|--------|
| Module ownership (I) | BIA module only: `scaffold/apps/bia/templates/bia/context_form.html` and `tests/test_bia_routes.py`. `withId` stays inline in the template, with no shared code, because only one module uses it. |
| Security and audit (II) | No change to who can view, edit or delete. `edit_item`, `edit_component_form` and `delete_component` keep their server-side `_can_edit_context` checks, and the delete POST keeps its `X-CSRFToken` header. No audit events change. |
| Validation (III) | A pytest regression test is added (see §Regression test). `pytest tests/test_bia_routes.py` and then the full suite are run and recorded in the task evidence. |
| Localization (IV) | No user-facing text changes, so no translation updates. |
| Operations and migration (V) | No schema change, no migration, no new environment variables. ProxyFix `x_prefix` deployments are handled (see §Expected URLs). No README or `docs/` update, because the fix restores intended behaviour and doesn't change documented behaviour. |

Simpler options that were rejected, and why, are recorded in decision
[[20261028-0730-bia-modal-url-id-substitution]].

## Data Model

No changes.

## API/Interface

No route or JSON changes.

## Out of Scope

- The **Edit** link on `/bia/components` (`components.html:346`) already uses
  `url_for` with the real id and works. It is not changed.
- A repo-wide `git grep` for `replace('/0` / `replace("/0` and `_id=0)`
  (excluding `specs/`, `.minispec/` and `graphify-out/`) found matches only in
  `context_form.html` lines 350-353. No other JS URL builder in the repo uses
  this pattern.
- The post-save redirect target (see above).

## Open Questions

- None.
