---
feature: authentication-overview-environments
status: planned
created: 2026-09-19
decisions:
  - 20260919-1235-authentication-overview-environments-column
---

# Authentication Overview Export: Environments column, drop tier summary & Users

## Overview

Simplify the Authentication Overview export
(`export_authentication_overview` in `scaffold/apps/bia/routes.py`,
template `scaffold/apps/bia/templates/bia/export_authentication.html`):
remove the "Components by tier and info type" summary and the "User types"
column, and add an **Environments** column showing each component's enabled
environments with their authentication method, so environments that differ
from the grouping method (Application integrated / Centrally managed (IdP))
become visible.

## User Stories

- As a reviewer, I want to see which environments a component uses and how
  each authenticates, so I can spot components that are IdP-managed in
  production but application-integrated elsewhere.
- As a reviewer, I no longer want the tier/info-type summary or the user
  types column cluttering the export.

## Components

### Removed
- Summary section "Components by tier and info type" (template section).
- `_build_tier_summary()` and the `tier_summary=` render argument in the route.
- `bia.export.authentication_overview.tier_summary` keys in `en.json`/`nl.json`.
- "Users" `<th>`/`<td>` (`columns.users` key + `component.user_type`) in the
  method tables and the unassigned table.
- Test `test_export_authentication_overview_tier_summary_merges_and_orders`.

### Added
- **Environments column** in every per-component table, placed where Users
  was (after Owner, before "Also used for authorisation").
  - Content: one line per *enabled* `ComponentEnvironment`, in the existing
    `ENVIRONMENT_TYPES` order (development, test, acceptance, production),
    formatted `<environment label>: <method label>`.
  - Environment label: existing `bia.components.environments.types.<type>`
    translation, resolved in the route with `_environment_label`.
  - Method label: `_describe_environment_authentication(env)`; environments
    with no method show the existing `columns.not_set` string.
  - Components with no enabled environments show `columns.not_set`. This
    includes a component still grouped by the legacy
    `Component.authentication_method_id` override (always `None` for new
    saves): it stays under its method but its Environments cell reads
    `Not set`. Accepted edge case; a test covers it.
  - Rendering: each entry is its own line inside the cell (`<br>`-separated
    text, no list markup); the method label uses the current locale only,
    like the other environment displays.
- Built in the route as `environment_usage = {component.id: [(env_label,
  method_label_or_None), ...]}` from the already-loaded
  `component.environments` (no extra query) and passed to the template.
- New translation key `bia.export.authentication_overview.columns.environments`
  ("Environments" / "Omgevingen") in `en.json`/`nl.json`.

### Unchanged
- Tier and Info type detail columns, grouping logic, method-summary table
  and counts, authorisation column/counts, `bia.exported` audit event.

## Security, Audit & Access

No change to access control or audit. The export stays behind
`@login_required` and logs the same single `bia.exported` event. The new
Environments column shows each environment's authentication method, which
is already visible to the same users on the component pages, so no new
exposure is introduced.

## Other Formats

The dashboard also offers a PDF variant (`format=pdf`) rendered from the
same template. It gets the same changes; the PDF output is checked once in
Task 3 since the extra column widens the table.

## Data Model

No schema changes. `Component.user_type` stays in the model, forms, and
other views; only its display in this export is removed.

## API/Interface

No route signature change. `export_authentication_overview` drops
`tier_summary` and gains `environment_usage` in the template context.

## Open Questions

- None outstanding. Test changes are tracked in tasks.md (the summary test is
  removed in Task 1; Environments and legacy-override tests are added in Task 3).

## Deferred

- Flagging the environment used for authorisation inside the Environments
  cell (the authorisation column already covers the primary environment).
