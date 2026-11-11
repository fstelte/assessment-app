---
type: decision
id: 20261111-0828-principle-description-no-length-cap
date: 2026-11-11
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/admin/forms.py
  - scaffold/apps/ssp/principle_importer.py
  - docs/architecture.md
  - tests/test_admin_principles.py
tags: [admin, forms, validation, principles]
participants: [Ferry Stelte, Claude]
---

# Principle descriptions have no length cap in the forms

## Context

`PrincipleCreateForm.description` (and through inheritance
`PrincipleUpdateForm`) has `Length(max=5000)`. The JSON importer
(`ssp/principle_importer.py`) only checks that a description isn't empty, and
the column is `Text` with no limit. An imported principle with a description
over 5000 characters can be opened on the edit page, but saving it always
fails validation. `update_principle` then redirects to the list with a flash
message, so it is easy to miss why. Such principles can't be edited.

## Options Considered

- A: give the importer the same limits (reject over 5000 per row) and show
  form errors on the edit page instead of redirecting.
- **B: remove the 5000 cap from the form (chosen).**

## Decision

- Remove `Length(max=5000)` from `PrincipleCreateForm.description` and keep
  `DataRequired()`. The update form inherits this, so create, update and import
  all accept the same descriptions.
- The name keeps `Length(max=255)`, which matches `String(255)` in the database.
- The database stays the same.

### Amendment (2026-11-11, from `/minispec.analyze`)

There is still a limit: Flask 3.1.3 rejects any single form field over
`MAX_FORM_MEMORY_SIZE` (default 500,000 bytes) with a 413. `MAX_CONTENT_LENGTH`
is unset, so a JSON file upload isn't limited, and the importer could create a
principle that the form can never save. Therefore:

- The importer skips rows whose description is over
  `current_app.config["MAX_FORM_MEMORY_SIZE"]` bytes in UTF-8, with a per-row
  error in `stats.errors`. If the value is `None`, it checks nothing.
- Form and import then apply the same limit, and every principle that exists
  can be saved through the form.

Considered and rejected: keeping the importer unchanged and documenting the
500 KB edge case as a known limitation. That would break the requirement
that every principle is editable.

## Consequences

### Positive
- ✅ Every principle created after this change, including through import, can
  be saved through the form. Existing principles over 5000 characters can be
  saved without first being shortened.
- ✅ Small change; the form, the importer and the column agree.

### Negative
- ⚠️ The only upper bound on description size is Flask's 500 KB form field
  limit. The editors are admins and control owners, so the risk is low.
- ⚠️ A principle imported before this change with a description over 500 KB
  (very unlikely) still can't be saved through the form.
- ⚠️ Validation errors on the edit page still go through a redirect plus a
  flash message (out of scope).

## Related Decisions

- [[20261111-0827-principles-admin-navigation]]
