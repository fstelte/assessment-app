---
type: decision
id: 20261118-1500-ssp-admin-option-lists
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/ssp/models.py
  - scaffold/apps/ssp/forms.py
  - scaffold/apps/ssp/routes.py
  - scaffold/apps/ssp/templates/ssp/edit.html
  - scaffold/apps/ssp/templates/ssp/view.html
  - scaffold/apps/ssp/templates/ssp/print.html
  - scaffold/apps/admin/routes.py
  - scaffold/apps/admin/forms.py
  - scaffold/apps/admin/templates/admin/users.html
  - scaffold/apps/admin/templates/admin/ssp_options.html
  - migrations/versions/*
tags: [ssp, admin, catalogue, data-model, monitoring]
participants: [Ferry Stelte, Claude]
---

# SSP laws/regulations/policies and monitoring frequency come from admin-managed lists

## Context

Two SSP edit fields are free text today: `laws_regulations` (Text) and
`monitoring_frequency` (String(100)). This leads to inconsistent wording across
plans. The user wants admins to maintain both lists from the admin hub
(`/admin/users`). Laws/regulations/policies are multi-select and monitoring
frequency is single-select.

## Options Considered

### Option 1: One generic `SSPOption` table with a `kind` discriminator
- ✅ One model, one admin page, one form set
- ✅ Adding another SSP list later only needs a new `kind`
- ❌ Both kinds must share the same fields

### Option 2: Two dedicated tables
- ✅ Explicit and allows different fields per list
- ❌ About twice the admin code for two lists that look the same

For existing data, keeping the free text as "additional notes" was also
considered. The user chose to replace it fully.

## Decision

We chose **Option 1, with a full replacement of the free-text UI**.

- `SSPOption`: `id`, `kind` (non-native enum `law_regulation` |
  `monitoring_frequency`), `name` (String 255, unique per kind and
  case-insensitive), `description` (Text, optional), `is_active` (bool),
  timestamps. Options are listed alphabetically. `sort_order` was dropped in
  20261118-1530 (CHK005).
- `ssp_plan_laws` M2M (`ssp_id`, `option_id`) gives `SSPlan.laws_regulations_options`.
- `SSPlan.monitoring_frequency_id` is a nullable FK to `ssp_options.id` with
  `ondelete=SET NULL`.
- Edit form: `SelectMultipleField` for laws (with descriptions as help text) and a
  `SelectField` for frequency with an empty "—" choice. Both list only active
  options, plus any inactive option the SSP already uses, so saving never drops it.
- Admin: one page `admin.ssp_options` (`/admin/ssp-options`) with two sections
  (create, edit, activate/deactivate, delete). It requires an admin and a fresh
  login and writes audit events, like `list_authentication_methods`. An option
  that is in use is deactivated instead of deleted. A link is added to the
  `/admin/users` hub.
- Option names are free text in whatever language the admin enters. They are
  not per-locale labels: laws are proper names (AVG, NIS2, BIO) and per-locale
  labels would add cost for little value.
- Migration: seed `monitoring_frequency` options from the distinct non-empty
  existing values, link each SSP to its option, then drop the
  `monitoring_frequency` column. The `laws_regulations` text is no longer shown
  or editable (see open question in the design about dropping the column).

## Consequences

### Positive
- ✅ Consistent terminology across SSPs and exports
- ✅ Admin-controlled lists, following the existing admin hub pattern

### Negative
- ❌ Existing free-text laws content disappears from the UI
- ❌ Option names are not translated per locale
