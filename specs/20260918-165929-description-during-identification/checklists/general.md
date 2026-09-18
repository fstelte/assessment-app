---
type: checklist
domain: general
feature: authentication-mechanism-also-used-for-authorisation
created: 2026-09-18
status: completed
---

# General Requirements Quality Checklist

**Purpose:** Validate that the design for the "used for authorisation" flag
is complete, clear, and consistent before implementation.
**Feature:** authentication-mechanism-also-used-for-authorisation

## Completeness

- [x] CHK001 - Does the design specify what happens to
  `used_for_authorization`/`authorization_note` when an environment's
  `authentication_method` is cleared (unset) while the flag remains
  checked? [Gap, Design §Components]
- [x] CHK002 - Does the design specify what happens to the flag/note when
  an environment row is disabled (`is_enabled` unchecked) rather than
  deleted — are they retained, or cleared? [Gap, Design §Components]
- [x] CHK003 - Is the maximum length of `authorization_note` specified
  (e.g. matching another free-text field's limit), or is "unbounded text"
  an explicit choice? [Completeness, Design §Data Model]
- [x] CHK004 - Does the design specify how the per-component resolved
  value (used by the export) behaves when a component has multiple
  enabled environments with conflicting flag values, beyond stating it
  reuses the existing priority-rank fallback? [Completeness, Design §Components]
- [x] CHK005 - Are requirements defined for whether the note is shown/used
  anywhere when the flag itself is false (e.g. a note left over from a
  previously-checked state)? [Gap]

## Clarity

- [x] CHK006 - Is "reflect this in the overview and all other parts where
  the authentication part is used" translated into a concrete, closed list
  of surfaces (badge, export detail table, export summary, AJAX payloads),
  or could a reader interpret it as also covering surfaces the design
  explicitly excluded (e.g. `export_item.html`'s existing
  `component.authentication_method.slug` display)? [Clarity, Design §Overview]
- [x] CHK007 - Is "boolean + optional free-text note" precise about
  whether the note is capped, sanitized, or rendered as-is (HTML-escaped
  only), given it will appear in an exported HTML document? [Clarity,
  Design §Components]
- [x] CHK008 - Is the summary-table addition ("count of
  authorisation-flagged components") fully specified — e.g. is it a count
  out of the group's total, or an absolute number requiring the reader to
  cross-reference the existing components column? [Clarity, Design
  §Authentication overview export]

## Consistency

- [x] CHK009 - Is the decision to key the flag off the per-environment
  fallback chain (same as `authentication_method_id`) explicitly reconciled
  with the fact that the legacy `Component`-level override was excluded —
  i.e. does the resolution helper's behavior stay correct if that legacy
  field is ever populated again? [Consistency, Design §Out of Scope]
- [x] CHK010 - Are the naming conventions for the new fields
  (`used_for_authorization`, `authorization_note` — US spelling) checked
  against the feature's own British-English framing ("authorisation") and
  the existing codebase's spelling convention, to avoid a naming mismatch
  between UI copy and field names? [Consistency, Design §Data Model]
- [x] CHK011 - Do the i18n key names planned for
  `bia.components.environments.*` and
  `bia.export.authentication_overview.*` follow the exact nesting/casing
  pattern of sibling keys already in `en.json`/`nl.json`, or is that left
  to implementation-time judgment? [Consistency, Design §i18n]

## Measurability

- [x] CHK012 - Can "reflected everywhere the authentication mechanism is
  shown" be objectively checked against a finite, enumerated list of
  files/surfaces, or does it rely on a subjective sweep at implementation
  time? [Measurability, Design §Overview]
- [x] CHK013 - Are acceptance criteria defined for the export summary
  count (e.g. "must equal the number of components in that group with
  `used_for_authorization=true`"), or only described narratively?
  [Measurability, Design §Authentication overview export]

## Coverage

- [x] CHK014 - Are requirements defined for the "unassigned" export table
  (components with no resolvable authentication method) — should the
  authorisation column still render for these, given they have no method
  group to summarize into? [Coverage, Design §Authentication overview export]
- [x] CHK015 - Does the design address concurrent edits to the same
  component's environments (e.g. two admins editing different environment
  rows) with respect to the new fields, or is this explicitly deferred as
  out of scope? [Coverage, Gap]
- [x] CHK016 - Are requirements defined for existing `ComponentEnvironment`
  rows created before this migration — is the boolean's `False` default
  sufficient, or does backfill/data-migration behavior need to be stated
  explicitly? [Coverage, Design §Migration]
- [x] CHK017 - Does the design specify whether the admin
  `AuthenticationMethod` CRUD screens need a read-only indicator showing
  how many environments have flagged that method for authorisation, or is
  that explicitly out of scope? [Coverage, Design §Out of Scope]

## Summary

- **Total Items:** 17 (all resolved)
- **Focus Areas:** Completeness (5), Clarity (3), Consistency (3),
  Measurability (2), Coverage (4)
- **Resolution:** All 17 items resolved in
  `.minispec/knowledge/decisions/20260918-1730-authorisation-flag-checklist-gap-resolutions.md`
  and folded back into `design.md` (Overview, Affected Surfaces, Components,
  Security/Audit Impact, and Out of Scope sections updated accordingly).


