---
title: Replace tier summary and Users column with per-component Environments column in Authentication Overview export
date: 2026-09-19
status: accepted
supersedes:
  - 20260918-0552-authentication-overview-tier-infotype-summary (summary table only)
---

## Context

The Authentication Overview export groups components under one
authentication method (e.g. "Application integrated", "Centrally managed
(IdP)"), chosen from the highest-priority enabled environment
(production > acceptance > test > development). Other environments of the
same component, which may use a different method, were invisible. The
nested "Components by tier and info type" summary added in
[[20260918-0552-authentication-overview-tier-infotype-summary]] and the
"User types" column are no longer wanted.

## Decisions

- **Remove the tier/info type summary**: the "Components by tier and info
  type" section, `_build_tier_summary`, the `tier_summary` template
  variable, and its `tier_summary` translation namespace are deleted. The
  per-component **Tier** and **Info type** detail columns stay (they were
  not part of the request).
- **Remove the Users column**: `component.user_type` is no longer shown in
  any table of the export (method tables and "without authentication type"
  table). The `user_type` field itself is untouched elsewhere.
- **Add an Environments column** to every per-component table (both method
  tables and the unassigned table, to keep the layout consistent). It lists
  every *enabled* environment of the component with the authentication
  method assigned to that environment, e.g.
  `Production: Centrally managed (IdP)`, `Test: Application integrated`.
  This makes environments that differ from the grouping method visible.
- **Legacy override**: a component with no enabled environments shows `Not set`
  in the Environments cell even if it is grouped by the legacy
  `Component.authentication_method_id`. That field is always `None` for
  new saves, so surfacing it would add code for a dead path. Revisit if real
  data shows populated overrides.
- **Security/audit**: unchanged. Same `@login_required` gate and single
  `bia.exported` audit event; environment methods are already visible on
  the component pages.
- **PDF variant**: the `format=pdf` export renders the same template and
  inherits the change; it is checked once during testing.
- Rejected alternatives: showing only the non-primary environments, showing
  environment names without method, and listing a component under every
  method group any of its environments uses (would double-count components
  in the method summary counts).

## Rationale

A per-row column answers "which environments use what" without changing
grouping or the method-summary counts, and needs no schema change. Listing
all enabled environments (not only "additional" ones) avoids the reader
having to infer which environment drove the grouping.
