---
type: decision
id: 20260925-0620-component-tier-inherit-from-bia
date: 2026-09-25
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/bia/models/__init__.py
  - scaffold/apps/bia/forms.py
  - scaffold/apps/bia/utils.py
  - migrations/versions/*
tags: [bia, tier, component]
participants: [Ferry Stelte, Claude]
---

# Component tier is a nullable override that falls back to the BIA tier

## Context

Tier (`BiaTier`) is only set per BIA (`ContextScope.tier_id`). Components have no
tier; the Authentication Overview borrows the BIA's tier for each component.
The engineer wants tiering per component while keeping the per-BIA tier, both
using the same `BiaTier` definition.

## Options Considered

### Option 1: Nullable override with fallback (chosen)
- ✅ Existing data and exports keep working unchanged.
- ✅ Only deviating components need input.
- ❌ Two sources of truth; readers must use an `effective_tier` helper.

### Option 2: Independent, explicit only
- ✅ Simple.
- ❌ Existing reports lose tier values until every component is filled in.

### Option 3: Backfill then independent
- ✅ No fallback logic.
- ❌ Later BIA tier changes silently drift from components; data migration.

## Decision

We chose **Option 1**. `Component.tier_id` (nullable FK to `bia_tiers.id`). A
`Component.effective_tier` property returns the component's tier, else the
BIA's tier. No ceiling/floor rule between component and BIA tier (a component
may be higher or lower). Duplicating a BIA copies component tiers.

## Consequences

### Positive
- ✅ One tier definition shared by BIA and component.

### Negative
- ⚠️ Every consumer of a component's tier must use `effective_tier`.

## Related Decisions

- [[20260918-0552-authentication-overview-tier-infotype-summary]]
- [[20260925-0625-tier-goals-drive-component-rto-rpo]]