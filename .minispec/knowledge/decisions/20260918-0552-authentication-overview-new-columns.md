---
title: Add Info type and Tier columns to Authentication Overview export
date: 2026-09-18
status: accepted
---

## Context

The Authentication Overview export (`export_authentication_overview` in
`scaffold/apps/bia/routes.py`, rendered by
`scaffold/apps/bia/templates/bia/export_authentication.html`) lists BIA
components grouped by authentication method, showing BIA name, Component
name, Information owner, and User types. There was no visibility into a
component's information type or the risk tier of its owning BIA context.

## Decision

Add two columns to every per-component table in the export (each
authentication-method group's table, and the "components without an
authentication type" table):

- **Info type** - `Component.info_type`
- **Tier** - `component.context_scope.tier.get_label(locale)` (via the
  nullable `ContextScope.tier` relationship to `BiaTier`)

Both use the existing `columns.not_set` translation string as a placeholder
when the underlying value is empty/null (consistent with how `info_owner`
and `user_type` are already handled).

## Rationale

- Reuses fields that already exist on `Component`/`ContextScope`/`BiaTier`;
  no schema change needed.
- Matches the existing not-set placeholder convention rather than
  introducing a new one, keeping the export visually consistent.
- Full tier label (`get_label`) chosen over the bare integer level for
  readability in a human-facing export, consistent with how tier is
  displayed elsewhere in the BIA module.

## Related

[[20260918-0552-authentication-overview-tier-infotype-summary]]
