---
type: decision
id: 20261021-1655-tier-goal-prefills-component-rto-rpo
date: 2026-10-21
status: accepted
supersedes: 20260925-0625-tier-goals-drive-component-rto-rpo
superseded_by: null
impacts:
  - scaffold/apps/bia/models/__init__.py
  - scaffold/apps/bia/routes.py
  - scaffold/apps/bia/utils.py
  - scaffold/apps/bia/templates/bia/manage_item_availability.html
  - scaffold/apps/bia/templates/bia/manage_component_availability.html
tags: [bia, tier, rto, rpo, availability]
participants: [Ferry Stelte, Claude]
---

# Tier RTO/RPO goal pre-fills the component value; deviations are reported as manual

## Context

Under [[20260925-0625-tier-goals-drive-component-rto-rpo]] a tier goal always
replaced the component's RTO/RPO, and the form showed it read-only. Stored free
text stayed in the DB but was hidden. The engineer now wants the tier goal to
be a pre-filled default that the user can change, with existing stored values
kept and reported as "manually configured".

## Options Considered

### Precedence
- **Stored text wins, tier goal is the default (chosen).** Existing values stay
  in effect. Users can deviate from the tier.
- Tier keeps winning, stored text is only reported. Rejected: then "pre-fill"
  would mean nothing.

### Saving an unchanged pre-fill
- **Store nothing (chosen).** The component keeps following the tier, so later
  tier changes still apply. Clearing the field also reverts to the tier.
- Store a copy. Rejected: it freezes the value and makes it look manual.

### When a value counts as "manual"
- **Stored text is non-empty, a tier goal exists, and the text does not equal
  the goal (chosen).** Only real deviations from the tier are flagged.
- Any stored text. Rejected: almost all legacy data would be flagged.

### Equality test
- **Parse to seconds (chosen).** `"4 hours"`, `"240 min"` and `"4 u"` all
  equal a 14400 s goal. Text that can't be parsed counts as manual.
- Formatted-string match. Rejected: too strict for legacy free text.

## Decision

The effective RTO/RPO is the stored text if it is non-empty, else the effective
tier's goal (formatted with `format_duration_seconds`), else not set. Each field
has a source:

| Source | When |
|---|---|
| `tier` | no stored text and a goal exists, **or** stored text parses to the goal |
| `manual` | stored text, a goal exists, and the text doesn't parse to the goal (or can't be parsed) |
| `free_text` | stored text, no tier goal |
| `None` | nothing stored, no goal |

On save, a submitted value that is empty or parses to the goal is stored as
empty. The availability forms always show the input, pre-filled with the goal
when nothing is stored, and show a hint with the tier goal. When the source is
`manual`, a "manually configured" marker appears on forms, in-app tables,
HTML/PDF exports and the availability CSV.

No data migration. Legacy text that was hidden behind a goal becomes effective
again, which is intended.

## Consequences

### Positive
- ✅ Users can deviate from a tier, and the deviation is visible everywhere.
- ✅ Components that follow the tier still pick up tier goal changes.

### Negative
- ⚠️ Incident steps and summary exports change for components whose hidden
  legacy text differs from the tier goal.
- ⚠️ Equality depends on the duration parser, so odd free text counts as
  manual.

## Related Decisions

- [[20260925-0625-tier-goals-drive-component-rto-rpo]] (superseded)
- [[20260925-0620-component-tier-inherit-from-bia]]
- [[20261021-1655-availability-csv-rto-rpo-source-columns]]
