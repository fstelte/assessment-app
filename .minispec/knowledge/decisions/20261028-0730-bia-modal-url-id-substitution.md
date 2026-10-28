---
type: decision
id: 20261028-0730-bia-modal-url-id-substitution
date: 2026-10-28
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/bia/templates/bia/context_form.html
  - tests/test_bia_routes.py
tags: [bia, component, ui, bugfix, javascript]
participants: [Ferry Stelte, Claude]
---

# Build component modal URLs by substituting the id segment of a url_for template

## Context

The view-component modal on the BIA edit page (`/bia/item/<id>/edit`,
`context_form.html`) builds four URLs in JavaScript: get, delete, edit and
view consequences. Each one renders `url_for(..., component_id=0)`, strips the
`0` with `.replace('/0', '/')`, then appends the id.

This only works when the id is the last path segment. The edit route is
`/component/<id>/edit`, so the result was `/bia/component//edit<id>/edit`,
and clicking **Edit** in the modal led to an error page.

## Options Considered

- Fix only the edit URL: rejected. It leaves the fragile pattern in place for
  the other three URLs and for any route added later.
- **One helper for all four URLs (chosen):** keep each `url_for(component_id=0)`
  output unchanged as a template and replace its last whole `/0` path segment
  with `/<id>` at click time.
- Have the `get_component` JSON return `edit_url`: rejected. It changes the API
  payload for a client-side bug, and only covers the URLs that come after a fetch.

## Decision

- In `context_form.html`, store the four `url_for(..., component_id=0)` strings
  unchanged.
- Add `withId(template, id)`, which returns
  `template.replace(/\/0(?=\/|$)(?!.*\/0(?:\/|$))/, '/' + id)`. This is the
  last whole `0` segment, so a forwarded URL prefix (ProxyFix `x_prefix`) is
  never touched.
- Every place that builds one of these URLs calls `withId`. Nothing appends
  path segments by hand.
- The view and delete handlers return early when `componentId` is empty.
- Regression test: render `/bia/item/<id>/edit`, assert the four unchanged templates,
  extract the shipped `withId` regex and apply it in Python to all four
  templates, with and without a `/0` prefix.

## Consequences

### Positive
- ✅ The Edit button in the modal opens the component edit form.
- ✅ The id can sit anywhere in the path and a URL prefix is left alone, so a
  new modal action won't hit this bug again.
- ✅ The test runs the regex that actually ships, not a copy of it.

### Negative
- ⚠️ Three URLs that already worked are touched. The regex test covers all four.
- ⚠️ If a route ever has a literal `0` segment after the id, the regex would
  pick the wrong segment. No current BIA route does.
- ⚠️ The click wiring has no automated test, only the manual check.

## Related Decisions

- None.
