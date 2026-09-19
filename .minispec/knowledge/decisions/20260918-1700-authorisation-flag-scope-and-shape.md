---
title: Scope and shape of the "used for authorisation" flag on authentication mechanism identification
date: 2026-09-18
status: accepted
---

## Context

The authentication overview feature (see
[[20260918-0552-authentication-overview-gap-resolutions]] and related
records) currently has no way to record that a component's authentication
mechanism also handles authorisation. The authentication mechanism itself
is identified per environment on `ComponentEnvironment.authentication_method_id`
(a `SelectField` in `ComponentEnvironmentForm`), with a legacy per-component
override on `Component.authentication_method_id` that is always set to
`None` on create and only ever used as a fallback. There is currently no
"authorisation" concept anywhere in the codebase.

## Decisions

- **Field shape**: a single boolean flag (`used_for_authorization`) plus an
  optional free-text note (`authorization_note`). No granular sub-selection
  of authorisation aspects (roles, permissions, resource-level access,
  etc.) — the stated need is covered by "yes/no, plus context."
- **Placement**: the new fields live on `ComponentEnvironment`, the same
  place the authentication mechanism is already identified per environment.
  They are NOT added to the legacy `Component`-level override field, since
  that field is always `None` in practice and extending it would maintain a
  dead code path for no benefit.
- **Not on the lookup table**: the flag is not stored on the global
  `AuthenticationMethod` lookup (e.g. "SSO is always also authorisation"),
  because the same mechanism slug can be authorisation-relevant in one
  environment/component and not in another. Per-environment-usage is the
  correct granularity, not per-mechanism-definition.
- **Downstream surfaces**: the flag/note must be reflected everywhere the
  authentication mechanism is currently shown or serialized —
  `_describe_environment_authentication()`, the AJAX serialization blocks
  in `routes.py`, the environment badge in `components.html`, and the
  `export_authentication_overview` / `export_authentication.html` report
  (detail table column + summary count). No new export format is
  introduced, consistent with the earlier finding that no CSV variant of
  this export exists.

## Rationale

Keeping the flag per-environment (rather than per-component or
per-mechanism-definition) matches how the authentication mechanism is
already modeled and avoids incorrect generalization — a mechanism's role in
authorisation is a property of how it's actually deployed in a given
environment, not an inherent property of the mechanism type. Skipping the
legacy `Component`-level override keeps the change scoped to the code path
that is actually used, rather than mirroring a dead pattern for symmetry's
sake. A boolean + note (rather than a structured sub-selection) matches the
lightweight, admin-managed-lookup style already used for authentication
mechanisms themselves.
