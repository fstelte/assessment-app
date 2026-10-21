---
type: decision
id: 20261021-1730-rto-rpo-prefill-checklist-gap-resolutions
date: 2026-10-21
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/bia/models/__init__.py
  - scaffold/apps/bia/utils.py
  - scaffold/apps/bia/templates/bia/_recovery_marker.html
tags: [bia, tier, rto, rpo, checklist]
participants: [Ferry Stelte, Claude]
---

# RTO/RPO pre-fill: checklist gap resolutions

## Context

The requirements checklist `checklists/rto-rpo-prefill.md` (23 items) found
gaps in the Part 2 design. The engineer asked to resolve them all. Each
resolution below picks the simplest option that removes a wrong or surprising
"manual" flag.

## Decision

### Parser (CHK001–003, 010–012, 018, 020)
`parse_duration_seconds` accepts:

| Input | Seconds |
|---|---|
| empty / `None` | `None` |
| `immediate`, `0`, `none`, `-` (any case) | 0 |
| `<number> <unit>`, number with `.` or `,` as decimal separator | number × unit, rounded to an int |
| bare number other than `0` (e.g. `60`) | `None` (unparseable) |
| anything else | `None` (unparseable) |

Units are matched on the lowercased word after the number, **longest prefix
first**:

| Prefix | Unit | Covers |
|---|---|---|
| `mo`, `maand`, `mnd` | 30 d | month(s), maand(en), mnd |
| `mi`, `m` | 60 s | min, minute(s), minuut, minuten, m |
| `s` | 1 s | s, sec, second(s), seconde(n) |
| `h`, `u` | 3600 s | h, hour(s), u, uur, uren |
| `d` | 86400 s | d, day(s), dag(en) |
| `w` | 7 d | w, week(s), weken |
| `y`, `j` | 365 d | y, year(s), j, jaar, jaren |

This deliberately changes today's behaviour, where `month` counts as minutes.
The pre-filled value uses the viewer's UI locale (`4 h` / `4 u`). Both parse,
so equality doesn't depend on the locale. "Unparseable → manual" is
deliberate: a reviewer should look at text the app can't compare.

### Imports (CHK004)
CSV/SQL imports store text as given. They do not normalise text equal to the
goal to empty. Imported data is an explicit statement, and a lossless round
trip matters more. Its source is computed when read, the same as any stored
text. The CSV import skips availability rows whose four stored columns (MTD,
RTO, RPO, MASL) are all empty, so the extra rows from CHK014 don't create
empty records.

### Reporting surfaces (CHK005, 006, 014, 022)
- The availability CSV writes **one row per component**, including components
  with no availability record (stored columns empty, effective columns from
  the tier).
- The availability summary export (aggregated per BIA) shows no marker. One
  aggregated value can come from several components, and the detailed export
  already shows the markers.
- Incident steps copy the effective value without a marker. That is out of
  scope.
- Read-only viewers (archived BIA, or not the author) see the marker in
  tables and exports like everyone else.

### Marker wording, style and accessibility (CHK007–009, 013, 015, 021)
- Internal source values are `tier`, `manual`, `free_text` and `None`. The CSV
  labels are `tier`, `manual`, `free text` and `not set`. Only the CSV labels
  appear outside code.
- The table/export marker is **visible text**, not a tooltip, placed directly
  after each RTO and RPO value: en `manual · tier 4 h`, nl
  `handmatig · tier 4 u`. In-app it uses the existing amber chip style
  (`rounded-full border border-amber-400/60 bg-amber-500/10 px-2 py-0.5 text-xs`).
  In HTML/PDF exports it is plain text in parentheses.
- The form hint uses the existing key `bia.availability.tier_goal`
  ("From {tier}: {value}"), with the inherited suffix as now. When the value
  is manual, a second amber line reads en "Manually configured; differs from
  the tier goal", nl "Handmatig ingesteld; wijkt af van het tierdoel".
- "Manually configured" is the full term and "manual" is the short one.
- No extra message when a typed value equals the goal and is dropped. The
  normal success flash is enough, and the field shows the formatted goal on
  the next GET with no manual line. That is the feedback.
- Both availability pages use the same `_tier_goal_notes` and the same macro,
  so their hints are identical (CHK016).

### Weaker vs. stricter overrides (CHK019)
Both are flagged the same way. Grading direction is deferred: it would need a
policy decision on whether a weaker RTO is allowed at all.

### Release note (CHK023)
`docs/history.md` gets an explicit behaviour-change note: hidden legacy
RTO/RPO text becomes effective again, so incident steps and summary exports
can change.

## Consequences

### Positive
- ✅ Common Dutch and English durations no longer produce false "manual" flags.
- ✅ The CSV is complete and stays lossless on import.
- ✅ The marker can be read without hovering and shows in PDF.

### Negative
- ⚠️ A month counts as 30 days. Values like "1 maand" against a 30 d goal
  match; "1 maand" against a 4 w goal does not.
- ⚠️ The CSV gains rows for components without an availability record. The
  import ignores those rows.

## Related Decisions

- [[20261021-1655-tier-goal-prefills-component-rto-rpo]]
- [[20261021-1655-availability-csv-rto-rpo-source-columns]]
