---
title: Resolve checklist gaps for authentication-mechanism-also-used-for-authorisation design
date: 2026-09-18
status: accepted
---

## Context

Running `/minispec.checklist` against the design in
[[20260918-1700-authorisation-flag-scope-and-shape]] surfaced 17 items
(`specs/20260918-165929-description-during-identification/checklists/general.md`)
covering unspecified behavior, ambiguous scope language, naming
consistency, and coverage gaps. This record resolves each, plus a
Constitution Principle II (Security, Auditability, and Least Surprise)
gap: the design had not yet stated audit/access-control implications for
a change touching an existing export.

## Decisions

- **CHK001 (flag survives method clearing)**: `used_for_authorization` and
  `authorization_note` are independent metadata on the
  `ComponentEnvironment` row. Clearing `authentication_method_id` does
  NOT auto-clear them; they are only ever changed by explicit user
  action on that row.
- **CHK002 (flag on disable)**: Unchanged from existing behavior —
  `_sync_component_environments` already deletes the `ComponentEnvironment`
  row entirely when an environment is unchecked/disabled
  (routes.py:289-291), which already discards `authentication_method_id`.
  The new fields are deleted along with the row, consistent with existing
  behavior; no special-casing added.
- **CHK003 (note length)**: `authorization_note` is an unbounded `Text`
  column with no application-level max-length validator, consistent with
  other free-text descriptive fields in this module (e.g.
- **CHK004 (conflicting flags across environments)** [Amended during
  implementation]: The per-component resolved value (used by the export)
  reuses the same environment priority order
  (production > acceptance > test > development) as
  `authentication_method_id` resolution, via
  `_select_primary_environment_assignment`. During implementation of Task
  4, testing surfaced that the shared helper additionally filtered out any
  environment with no `authentication_method_id` set — correct for
  authentication-method resolution, but wrong here, since an assessor can
  check "used for authorisation" independently of picking a method. Fixed
  by adding a `require_authentication_method: bool = True` parameter to
  `_select_primary_environment_assignment`, defaulting to the original
  behavior for existing callers, with
  `_resolve_component_authorization_usage` passing `False`. The priority
  order and the `is_enabled` filter remain shared and unchanged.
  scheme. This is now stated explicitly in design.md rather than implied.
- **CHK005 (note visibility when flag is false)**: The note is only
  rendered in the badge title, export column, and AJAX payload label
  when `used_for_authorization` is `true`. If a user unchecks the box, a
  previously-entered note is retained in the database (not force-cleared)
  but not surfaced, so re-checking the box later restores its visibility.
- **CHK006 (closed list of affected surfaces)**: The feature touches
  exactly these surfaces, and no others:
  1. Environment badge title (`components.html:281`)
  2. Authentication overview export detail tables + unassigned table +
     summary table (`export_authentication.html`)
  3. `get_component`, `create_component`, `update_component` JSON
     payloads (via `_serialize_environments`)
  4. Component create/edit form environment rows (`components.html`,
     `edit_component.html`)

  Explicitly NOT touched: `export_item.html`'s existing
  `component.authentication_method.slug` display (a different, narrower
  export not covered by this feature) and the `AuthenticationMethod`
  admin CRUD screens (already excluded in design.md's Out of Scope).
- **CHK007 (note rendering/sanitization)**: The note is rendered via
  standard Jinja `{{ }}` auto-escaping (no `|safe` filter), identical to
  how other user-entered free-text fields (e.g. `component.info_owner`)
  are already rendered in this export. No markdown or HTML interpretation
  is added.
- **CHK008 (summary count format)**: The new summary-table column is an
  absolute count of authorisation-flagged components within that
  method's group (e.g. "3"), shown as a sibling column next to the
  existing total "Components" count column in the same row — not a
  fraction or percentage — so a reader compares the two columns directly.
- **CHK009 (resolution helper vs. legacy Component override)**:
  `_resolve_component_authorization_usage` intentionally checks ONLY the
  environment fallback chain and never consults the legacy
  `Component`-level authentication override field. This is an accepted
  limitation: if that dead field were ever repopulated in the future,
  authentication-method resolution and authorisation-flag resolution
  would diverge in source (one checks the override, the other doesn't).
  Since the override is confirmed dead code today, this divergence is
  accepted rather than engineered around; revisit only if the override
  field is ever reactivated.
- **CHK010 (spelling consistency)**: Code identifiers, the DB column
  names, and the model/form field names use American spelling
  (`used_for_authorization`, `authorization_note`), consistent with
  general programming convention and this codebase having no prior
  precedent either way. User-facing English copy in `en.json` uses
  British spelling ("authorisation") to match the terminology the
  engineer used when requesting this feature; `nl.json` uses the
  appropriate Dutch term. This intentional code/copy spelling split is
  documented here to prevent future confusion or "fixing" one to match
  the other.
- **CHK011 (i18n key nesting)**: New keys follow the exact existing
  nesting/casing patterns: `bia.components.environments.{used_for_authorization,
  authorization_note_label, authorization_note_placeholder}` and
  `bia.export.authentication_overview.columns.used_for_authorization` /
  `bia.export.authentication_overview.summary.used_for_authorization_count`
  — matching sibling keys already present in both locale files.
- **CHK012 (measurability of "everywhere shown")**: Resolved by CHK006's
  enumerated list — the requirement is now a closed, checkable set of
  four surfaces rather than an open-ended sweep.
- **CHK013 (summary count acceptance criteria)**: The summary count for
  a method group MUST equal the number of components in `group.components`
  whose resolved `used_for_authorization` is `true`; the unassigned row's
  count MUST equal the same for `unassigned` (see CHK014).
- **CHK014 (unassigned table coverage)**: The authorisation indicator
  column IS rendered in the unassigned detail table (for the edge case of
  a component with `used_for_authorization=true` but no resolvable
  authentication method), and the existing "unassigned" row in the
  method-summary table also gets the same flagged-count column, for
  consistency with the per-method rows.
- **CHK015 (concurrent edits)**: Explicitly out of scope. The new fields
  follow the same last-write-wins behavior as every other field on the
  component edit form; this feature does not introduce a new concurrency
  concern.
- **CHK016 (pre-existing rows / migration default)**: The migration sets
  `server_default=sa.false()` on `used_for_authorization`, so existing
  `bia_component_environments` rows are backfilled to `False` (and
  `authorization_note` to `NULL`) automatically at migration time — no
  separate data migration step is needed.
- **CHK017 (admin CRUD indicator)**: Confirmed out of scope, consistent
  with design.md's existing Out of Scope entry — the `AuthenticationMethod`
  admin screens remain a pure slug+label registry unaffected by
  per-environment usage data.
- **Constitution Principle II (audit/access control)**: No change. The
  authentication overview export remains gated by the existing
  `@login_required` check and continues to log a single `bia.exported`
  event (routes.py:1776-1780); the new column/count do not broaden data
  exposure, since the underlying `ComponentEnvironment` data is already
  visible to the same users via the component edit form. No new role
  check, audit event, or access-control change is required, mirroring
  the precedent set in
  [[20260918-0552-authentication-overview-gap-resolutions]] for the prior
  Tier/Info-type column addition to this same export.

## Rationale

Most gaps were resolved by explicitly stating "reuse the existing
pattern" (fallback chain, deletion-on-disable, Jinja auto-escaping,
last-write-wins, audit posture) rather than inventing new behavior for
this small, additive feature — consistent with the project's preference
for matching existing conventions over introducing new ones. The two
genuinely new decisions are the code/copy spelling split (CHK010, needed
because "authorization" and "authorisation" are both defensible and the
codebase had no precedent) and extending the unassigned-row summary count
for consistency (CHK014, a two-line template change once decided).
