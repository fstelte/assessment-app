---
feature: authentication-mechanism-also-used-for-authorisation
status: completed
created: 2026-09-18
decisions:
  - 20260918-1700-authorisation-flag-scope-and-shape
  - 20260918-1730-authorisation-flag-checklist-gap-resolutions
---

# Authentication Mechanism Also Used for Authorisation - Design

## Overview

Today, when identifying the authentication mechanism for a component's
environment (dev/test/acceptance/production), there is no way to record
whether that same mechanism also handles authorisation. This feature adds a
boolean flag plus an optional free-text note to the existing per-environment
authentication mechanism selection, and surfaces it in exactly four surfaces
(see "Affected surfaces" below) — no others.

## User Stories

- As an assessor identifying a component's authentication mechanism, I want
  to mark that the same mechanism also handles authorisation, so I don't
  need a separate assessment step or free-text workaround to record this.
- As a reviewer reading the authentication overview export, I want to see
  which components' authentication mechanism also covers authorisation, so I
  can spot components that rely on a single mechanism for both concerns.

## Affected Surfaces (closed list)

1. Environment badge title (`components.html:281`)
2. Authentication overview export detail tables + unassigned table +
   method-summary table, including the unassigned row's count
   (`export_authentication.html`)
3. `get_component`, `create_component`, `update_component` JSON payloads
   (via `_serialize_environments`)
4. Component create/edit form environment rows (`components.html`,
   `edit_component.html`)

Explicitly NOT touched: `export_item.html`'s existing
`component.authentication_method.slug` display, and the
`AuthenticationMethod` admin CRUD screens.

## Components

### `ComponentEnvironment` model extension
New columns: `used_for_authorization` (boolean, not nullable, default
`False` via `server_default=sa.false()` so existing rows backfill
automatically) and `authorization_note` (nullable, unbounded `Text`, no
application-level max length — consistent with other free-text fields
like `Component.description`). These live alongside the existing
`authentication_method_id` on `ComponentEnvironment` — the same place the
mechanism is already identified per environment — not on the legacy
`Component`-level override (always `None` in practice, out of scope) and
not on the global `AuthenticationMethod` lookup (the same mechanism slug
can be authorisation-relevant in one environment and not another).

Both fields are independent of `authentication_method_id`: clearing the
method does not auto-clear them, and unchecking the flag does not force-
clear the note (it stays in the DB, just not surfaced, until re-checked).
Disabling an environment still deletes the whole `ComponentEnvironment`
row as today, which discards these fields along with everything else on
that row — no new special-casing.

### Migration
New Alembic migration adding the two columns to `bia_component_environments`
(mirroring the style of `20251124_0011_bia_component_environments.py`),
with `server_default=sa.false()` on the boolean column.

### Form
`ComponentEnvironmentForm` (forms.py:188-201) gains a `BooleanField`
(`used_for_authorization`) and a `StringField`/`TextAreaField`
(`authorization_note`), positioned next to the existing
`authentication_method` `SelectField`. The note field is only meaningfully
shown/enabled when the checkbox is checked (client-side toggle), but is not
required even when checked.

### Templates
`components.html` and `edit_component.html` environment-row rendering
(around lines 197/211, 107/121) add the checkbox + note field next to the
`authentication_method` dropdown. The environment badge (`components.html:281`)
gains a secondary indicator/title text when `used_for_authorization` is set.
The note renders via standard Jinja `{{ }}` auto-escaping (no `|safe`),
identical to how other free-text fields render in this export.

### Resolution & serialization
`_serialize_environments` (routes.py:251-266) is extended to include
`used_for_authorization` and `authorization_note` directly off each
`ComponentEnvironment` row (no resolution needed there — each row owns its
own values). A new `_resolve_component_authorization_usage(component)`
helper, mirroring `_resolve_component_authentication_method_id`
(routes.py:203-217), resolves a per-*component* value for the export by
reusing the exact same `_select_primary_environment_assignment` priority-
rank fallback (production > acceptance > test > development) — not a new
priority scheme. This helper intentionally never consults the legacy
`Component`-level override (accepted limitation, since that field is dead
code today).

### Authentication overview export
`export_authentication_overview` (routes.py:1720-1782) and
`export_authentication.html` add an "Also used for authorisation" column to
the per-method detail tables AND the unassigned table (with the note
surfaced as a `title` attribute on hover), plus an absolute count of
authorisation-flagged components as a new column on the existing
method-summary table — including its "unassigned" row. The count for a
group MUST equal the number of components in that group with a resolved
`used_for_authorization` of `true`. The Tier/Info-type nested summary
table is unaffected — it groups by tier/info type, not by this new flag.

### i18n
New keys following existing nesting/casing exactly:
`bia.components.environments.{used_for_authorization, authorization_note_label,
authorization_note_placeholder}` and
`bia.export.authentication_overview.columns.used_for_authorization` /
`.summary.used_for_authorization_count`, in `en.json` and `nl.json`.

**Spelling note:** code identifiers, DB columns, and form field names use
American spelling (`used_for_authorization`, `authorization_note`) per
general programming convention; user-facing English copy uses British
spelling ("authorisation") to match the engineer's own terminology for
this feature. This split is intentional — do not "fix" one to match the
other.

## Data Model

`ComponentEnvironment`:
- `used_for_authorization: bool` (default `False`, `server_default=false()`)
- `authorization_note: str | None` (unbounded `Text`)

No changes to `AuthenticationMethod` or `Component`.

## API / Interface

No new routes. Existing `ComponentEnvironmentForm` submission handling in
the component create/edit routes picks up the two new fields the same way
it already handles `authentication_method`. Existing AJAX response shapes
gain two additional keys (additive, non-breaking).

## Security / Audit Impact

No change. The authentication overview export remains gated by the
existing `@login_required` check and continues to log a single
`bia.exported` event; the new column/count do not broaden data exposure,
since the underlying `ComponentEnvironment` data is already visible to the
same users via the component edit form. No new role check, audit event,
or access-control change is required — mirrors the precedent set for the
prior Tier/Info-type column addition to this same export.

## Out of Scope

- No change to the `Component`-level authentication override field.
- No change to the `AuthenticationMethod` admin CRUD (lookup table stays a
  pure slug+label registry; the flag is per-environment-usage, not
  per-mechanism-definition). No read-only "flagged count" indicator added
  there either.
- No CSV or other export format - `export_authentication_overview` remains
  the only rendering surface, consistent with the prior authentication
  overview decisions.
- No granular sub-selection of authorisation aspects (roles, permissions,
  etc.) - a single boolean + free-text note covers the stated need.
- Concurrent-edit handling: unchanged last-write-wins behavior, same as
  every other field on the component edit form.

## Open Questions

None outstanding - scope, field shape, placement, and all checklist gaps
were resolved during the design conversation and the follow-up checklist
review (see decision records).

