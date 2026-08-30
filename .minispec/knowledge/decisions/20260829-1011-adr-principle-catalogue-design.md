---
type: decision
id: 20260829-1011-adr-principle-catalogue-design
date: 2026-08-29
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/ssp/models.py
  - scaffold/apps/admin/routes.py
  - scaffold/apps/admin/forms.py
  - scaffold/apps/ssp/routes.py
  - scaffold/apps/ssp/templates/ssp/*
  - migrations/versions/*
tags: [ssp, adr, architecture-principles, admin, data-model]
participants: [Ferry Stelte, Claude]
---

# Architecture Decision Records on the SSP, anchored to an admin-managed Principle catalogue

## Context

We need to add ADR (https://adr.github.io/) support to the System Security Plan (SSP)
module, where every ADR must start by selecting one Architecture Principle from a
catalogue. That catalogue must be administered the same way the existing Control
catalogue is administered (`scaffold/apps/admin/routes.py:156-269`,
`scaffold/apps/csa/models/control.py`), and must support bulk import like controls do
(`scaffold/apps/csa/services/control_importer.py`).

Three shape decisions were open: (1) whether an ADR links to one principle or one
primary plus optional secondary principles, (2) whether the ADR lifecycle needs formal
supersession linking or just a status field, (3) how rich the Principle catalogue's own
fields should be.

## Options Considered

### Option 1: Single principle per ADR, no supersession, minimal principle fields
Simplest possible model: one FK per ADR, a `status` enum with no cross-ADR links,
principle = `name` + `description` only.
- ✅ Fastest to build, smallest schema
- ✅ Matches the literal phrasing "starts with selecting one ... principle"
- ❌ No way to model that an ADR revises an earlier one, other than free text
- ❌ Can't attach an ADR to more than one relevant principle when a decision genuinely touches several

### Option 2: Primary + secondary principles (many-to-many), self-referential supersession chain, minimal principle fields
One required primary principle FK (gates ADR creation, per the request), an optional
many-to-many link table for secondary principles, and a nullable self-referential
`supersedes_id` FK so a new ADR can formally supersede an older one (old ADR's status
flips to "Superseded" automatically). Principle catalogue kept lean (`name` +
`description`, no domain/owner fields) since it doesn't need Control's richer
classification.
- ✅ Matches how real-world ADR tooling (MADR) and this org's expected usage (decisions get revised) actually work
- ✅ Reuses the exact `SSPControlEntry`-style child-of-`SSPlan` pattern already proven in `scaffold/apps/ssp/models.py`
- ✅ Principle catalogue stays simple to administer/import despite the ADR side being richer
- ❌ More schema surface: one join table (`adr_secondary_principles`) plus one self-referential FK to build, test, and migrate
- ❌ UI must handle both principle pickers (primary required + secondary optional) and a "does this supersede an existing ADR" picker

## Decision

We chose **Option 2** because the engineer explicitly confirmed wanting both the
many-to-many secondary-principle linkage and the supersession chain after an explicit
complexity push-back (see Notes). The catalogue itself stays minimal (`name` +
`description`, no owner/domain) since — unlike controls, which are tied to compliance
frameworks and ownership — architecture principles are simple governance statements
that don't need per-principle ownership tracking for this feature to deliver value.

Placement: `ArchitecturePrinciple` and `ADRRecord` models live in
`scaffold/apps/ssp/models.py`, not in `scaffold/apps/csa/`, because — per the
constitution's Modular Domain Boundaries principle — shared code only moves to a
cross-cutting surface when at least two modules benefit, and today only the SSP/ADR
feature consumes the principle catalogue. Admin CRUD routes still live in
`scaffold/apps/admin/routes.py`, matching the existing precedent that `Control`'s model
lives in `csa` while its admin UI lives in `admin` — the admin blueprint is the
established home for catalogue administration regardless of which module owns the
underlying model.

Permission checks reuse the existing `_require_control_admin()`-style pattern (role
`admin` or the existing catalogue-owner role) rather than introducing a new role, since
the request framed this as "the same manner as control catalogue administration."

## Consequences

### Positive
- ✅ ADRs can express real decision revision history (supersession), which is the main practical value of ADRs over a flat changelog.
- ✅ An ADR that touches multiple principles (common in practice) doesn't force an artificial primary-only choice.
- ✅ Reusing the `SSPControlEntry` child-of-`SSPlan` pattern and the `Control` admin-catalogue pattern means most of the plumbing (cascade delete, permission checks, import summary UX) is a known-good template, not a novel design.

### Negative
- ⚠️ More tables/migrations to write and test than the minimal version (principles, ADRs, secondary-principle association, self-referential supersession FK).
- ⚠️ The "supersedes" UI needs a picker scoped to ADRs within the same SSP, plus validation that an ADR can only be superseded once (see design.md Edge Cases).

### Neutral
- The principle catalogue being simpler than `Control` (no domain/owner fields) means the admin form/import code is close to, but not a literal copy of, `ControlCreateForm`/`ControlImportForm` — some fields are simply omitted.

## Code References

- Control catalogue admin CRUD to mirror: `scaffold/apps/admin/routes.py:156-269` (`controls()` view), `:112-121` (`_require_control_admin()`)
- Control forms to mirror: `scaffold/apps/admin/forms.py:21` (`ControlImportForm`), `:34` (`ControlCreateForm`), `:60` (`ControlUpdateForm`), `:67` (`ControlDeleteForm`)
- SSP child-record pattern to mirror: `scaffold/apps/ssp/models.py` (`SSPControlEntry`: `ssp_id` FK cascade delete, `back_populates` on `SSPlan`)
- Import logic pattern to mirror: `scaffold/apps/csa/services/control_importer.py` (`upsert_control()`, `import_controls_from_mapping()`, `ImportStats`)

## Related Decisions

- [[20260829-1011-principle-bulk-import-format]]

## Notes

The engineer was offered a trimmed-down option (single principle, no supersession) as
a scope challenge before this decision was finalized, and explicitly chose to keep both
the secondary-principle linkage and the supersession chain, anticipating that ADRs will
be revised over time and sometimes touch more than one principle.
