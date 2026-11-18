---
type: decision
id: 20261118-1450-ssp-edit-drop-fips-overrides
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/ssp/forms.py
  - scaffold/apps/ssp/routes.py
  - tests/*ssp*
tags: [ssp, bugfix, forms]
participants: [Ferry Stelte, Claude]
---

# SSP metadata edit: drop the unrendered FIPS override fields from the form

## Context

Saving the SSP metadata page (`ssp.edit`) never persists anything. Root cause:
`SSPEditForm` declares three `SelectField`s (`fips_confidentiality`,
`fips_integrity`, `fips_availability`) that `ssp/edit.html` never renders. On POST
the fields are absent, WTForms keeps the object data (a `FipsRating` enum coerced
to the string `"FipsRating.NOT_SET"`), which is not a valid choice, so
`validate_on_submit()` returns False. The template does not render those fields'
errors, so the user sees the page reload with no feedback. Reproduced with a
form-level probe: errors were exactly the three FIPS fields.

The overrides are shown nowhere in the app; the SSP view derives C/I/A from the
BIA consequences (`get_cia_impact`).

## Options Considered

### Option 1: Drop the overrides from the form, keep the columns
- ✅ Smallest fix, no migration
- ✅ C/I/A keeps a single source of truth (the BIA)
- ❌ Dormant columns remain on `ssp_plans`

### Option 2: Render the overrides on the edit page and view/print
- ✅ Feature becomes usable
- ❌ More UI surface; overrides can silently contradict the BIA

### Option 3: Drop form fields and columns (migration)
- ✅ Cleanest schema
- ❌ Migration for no user-visible gain; destructive

## Decision

We chose **Option 1**. Remove the three fields from `SSPEditForm` and the
corresponding assignments / GET prefill in `routes.edit`. Leave the DB columns
(server default `not_set`) untouched. Add a regression test that a POST to
`ssp.edit` persists `laws`/monitoring fields.

## Consequences

### Positive
- ✅ Metadata saves again
- ✅ No migration

### Negative
- ❌ Unused columns stay; can be removed in a later cleanup
