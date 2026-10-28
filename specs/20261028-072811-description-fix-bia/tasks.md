---
feature: 20261028-072811-description-fix-bia
status: completed
created: 2026-10-28
chunk_size: adaptive
total_tasks: 1
estimated_lines: 45
---

# Fix the BIA Component Modal Edit Link Tasks

## Overview

The view-component modal on `/bia/item/<id>/edit` currently sends **Edit** to
`/bia/component//edit<id>/edit`. This fix adds a `withId(tpl, id)` helper
that builds all four modal URLs from their unchanged
`url_for(..., component_id=0)` strings, guards against an empty id, and adds a
regression test that runs the shipped regex. See decision
[[20261028-0730-bia-modal-url-id-substitution]] and design §Expected URLs.

## Task List

### Core Implementation

#### Task 1: Fix modal URL building and add a regression test
- **Estimate:** ~45 lines
- **Files:**
  - `tests/test_bia_routes.py` (new test, ~35 lines)
  - `scaffold/apps/bia/templates/bia/context_form.html` (`extra_js` block, ~10 lines changed)
- **Description:** Test first. The line numbers below are a guide to the code
  as of commit `0219176`. Find the code by its content if the lines have moved.
  1. Add `test_context_edit_page_builds_component_modal_urls` to
     `tests/test_bia_routes.py`. Using the `app`, `client`, `login` fixtures,
     create a `ContextScope` with one `Component` (the same pattern as
     `test_bia_detail_shows_component_summary`; `author=user`, not archived, so `_can_edit_context` passes), GET `/bia/item/<id>/edit`
     and assert:
     - status 200
     - the four `var <name>Url = '<template>'` definitions (`getComponentUrl`,
       `deleteComponentUrl`, `editComponentUrl`, `viewConsequencesUrl`) match
       the templates in design §Expected URLs, with no trailing `.replace`
     - the regex is extracted with
       `re.search(r"function withId\(tpl, id\) \{ return tpl\.replace\(/(.+?)/, '/' \+ id\); \}", body)`.
       Applied with `re.sub(pattern, "/42", tpl, count=1)` to each template,
       it gives the built URLs in the table. Applied to
       `/0/bia/component/0/edit`, it gives `/0/bia/component/42/edit`.
  2. Run the test and confirm it fails on the current code, which still has
     `.replace('/0', '/')` after each template and has no `withId`.
  3. In `context_form.html` (around lines 350-353), remove
     `.replace('/0', '/')` from all four URL definitions.
  4. Add, directly below them:
     `function withId(tpl, id) { return tpl.replace(/\/0(?=\/|$)(?!.*\/0(?:\/|$))/, '/' + id); }`
     Write it on one line exactly like this, because the test extracts it.
  5. Switch the call sites to `withId`:
     - view handler (~397): `fetch(withId(getComponentUrl, componentId))`
     - edit link (~419): `editLink.href = withId(editComponentUrl, componentId)`
       (drop `+ '/edit'`)
     - consequences link (~421): `consLink.href = withId(viewConsequencesUrl, componentId)`
     - `doDeleteComponent` (~457): `fetch(withId(deleteComponentUrl, componentId), {`
  6. Empty-id guards:
     - view handler, right after reading `componentId` (~396):
       `if (!componentId) return;`
     - first line of `doDeleteComponent`, before `confirm`:
       `if (!componentId) return;`
- **Depends on:** None
- **Acceptance (manual, run by anyone):**
  1. Log in as any non-admin user. You become the author of the BIA you create in this step, and only the author can open BIA > Edit (`_can_edit_context`). Create a throwaway BIA named `URL check` with two
     throwaway components, `Keep` and `Remove`. Don't use real data, because
     step 4 deletes something.
  2. Open BIA > `URL check` > Edit. Click **View** on `Keep`, then **Edit** in
     the modal. The browser goes to `/bia/component/<Keep id>/edit` and shows
     the edit form for `Keep`.
  3. Go back. Open `Keep` again. The modal fields are filled in, and the
     consequences link opens `/bia/consequences/<Keep id>` in a new tab.
  4. Open `Remove` and click **Delete** in the modal, then confirm. Do the same
     with the card's delete button on another throwaway component if you want.
     The card disappears and the browser network tab shows a POST to
     `/bia/delete_component/<id>`.
  5. Delete the `URL check` BIA afterwards.
- **Evidence:**
  - The new test fails before the template change and passes after it.
  - `pytest tests/test_bia_routes.py` passes, then the full `pytest` suite passes.
  - Manual acceptance steps 2-4 pass.

## Notes

- Repo-wide `git grep` (excluding `specs/`, `.minispec/`, `graphify-out/`)
  finds the `.replace('/0', ...)` / `_id=0)` pattern only in
  `context_form.html` lines 350-353.
- `withId` stays inline in the template's IIFE. There's no shared JS module,
  since this is the only use.
- Edit-button visibility and the post-save redirect are unchanged on purpose
  (design §Authorisation and navigation).
- After the code change, run `graphify update .` (per CLAUDE.md).

## Progress
- [x] Task 1: Fix modal URL building and add a regression test
