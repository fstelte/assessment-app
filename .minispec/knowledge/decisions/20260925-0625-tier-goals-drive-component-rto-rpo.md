---
type: decision
id: 20260925-0625-tier-goals-drive-component-rto-rpo
date: 2026-09-25
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/bia/models/__init__.py
  - scaffold/apps/bia/forms.py
  - scaffold/apps/incident/services.py
  - scaffold/apps/bia/utils.py
tags: [bia, tier, rto, rpo, availability]
participants: [Ferry Stelte, Claude]
---

# Tier RTO/RPO goals are applied directly to components

## Context

`BiaTier.rto_goal_seconds` / `rpo_goal_seconds` are integers that nothing
consumes today. `AvailabilityRequirements.rto` / `.rpo` are free-text strings,
copied into incident steps and exports.

## Options Considered

### Option 1: Derived, read-only, free text as fallback (chosen)
- ✅ Tier is the single source of truth; tier goal changes propagate.
- ✅ No data loss: old text stays in the DB and is used when no goal exists.
- ❌ A component cannot deviate from its tier's goal when the tier defines one.

### Option 2: Tier goal as default, editable override
- ❌ Stale free text silently beats the tier; not "applied directly".

### Option 3: Derived plus "deviates" flag
- ❌ Requires parsing free text; most work.

## Decision

We chose **Option 1**. Effective RTO/RPO = effective tier's goal formatted with
auto-units using the largest unit that divides the value evenly (14400 -> "4 h",
5400 -> "90 min", 90 -> "90 s"); if the goal is null, the stored free text; if
that is empty, "Not set". The availability form shows the tier value read-only
when a goal applies and keeps the text input otherwise. MTD and MASL are
unchanged. Stored `rto`/`rpo` columns are kept and exported as-is so CSV/JSON
round-trips stay lossless.

## Consequences

### Negative
- ⚠️ Stored free text becomes hidden (but retained) when a tier goal applies.

## Related Decisions

- [[20260925-0620-component-tier-inherit-from-bia]]