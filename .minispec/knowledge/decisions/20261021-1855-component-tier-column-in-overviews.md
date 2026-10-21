---
type: decision
id: 20261021-1855-component-tier-column-in-overviews
date: 2026-10-21
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/bia/routes.py
  - scaffold/apps/bia/templates/bia/components.html
  - scaffold/apps/bia/templates/bia/context_detail.html
  - scaffold/translations/en.json
  - scaffold/translations/nl.json
tags: [bia, tier, component, ui]
participants: [Ferry Stelte, Claude]
---

# Show the effective component tier as a read-only column in component overviews

## Context

Components already have a tier: a nullable override that falls back to the BIA
tier through `effective_tier`. It can be set in the add and edit forms. The
overviews don't show it, though: the `/bia/components` table and the
components table on `/bia/item/<id>`. You have to open each component to see
its tier.

## Options Considered

### Scope
- **Tier column only (chosen):** read-only; editing stays in the component form.
- Column + tier filter: rejected for now.
- Column + inline edit: rejected; it adds a per-row POST and its own error handling.

### Inherited marker
- Muted text + "(inherited)": rejected.
- **Effective tier, no marker (chosen):** the reader wants the tier that
  applies, not where it comes from.
- Own tier only: rejected; it hides the tier of most components.

### Placement on `/bia/components`
- In place of the Context column: rejected.
- **Just before Availability (chosen):** the tier drives the RTO/RPO goals
  shown there.

## Decision

- `/bia/components`: remove the **Context** column. Filtering by BIA stays
  available through the existing `bia_id` dropdown (and the `scope` query
  parameter). Add a **Tier** column directly before **Availability**.
- `/bia/item/<id>`: add a **Tier** column after **Name** in the components
  table. The availability table is unchanged.
- The cell shows `component.effective_tier.get_label()`, or `—` when neither
  the component nor the BIA has a tier.
- `view_components` and `view_item` eager-load `Component.tier` and
  `ContextScope.tier`, so the column adds no per-row queries.

## Consequences

### Positive
- ✅ You can see each component's tier at a glance in both overviews.
- ✅ No model, migration or export change.

### Negative
- ⚠️ The `/bia/components` table no longer shows which BIA a component belongs to.
  The BIA filter is the only way to tell.
- ⚠️ Inherited and explicit tiers look the same in the overview.

## Related Decisions

- [[20260925-0620-component-tier-inherit-from-bia]]
- [[20261021-1655-tier-goal-prefills-component-rto-rpo]]
