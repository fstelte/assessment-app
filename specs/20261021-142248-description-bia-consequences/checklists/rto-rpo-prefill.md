---
type: checklist
domain: general
feature: 20261021-142248-description-bia-consequences
scope: Part 2 — Tier RTO/RPO pre-fill with manual overrides
created: 2026-10-21
status: completed
---

# RTO/RPO Pre-fill Requirements Quality Checklist

**Purpose:** Check that the requirements for Part 2 (tier goal as pre-fill,
manual overrides reported) are complete, clear and consistent before
implementation.
**Feature:** 20261021-142248-description-bia-consequences (design.md Part 2,
decisions `20261021-1655-*`)

## Completeness

- [x] CHK001 - Does the design define which Dutch unit words the parser accepts beyond `u`/`uur`? `jaar` (j) is not in the prefix list, so "1 jaar" would count as manual. [Gap, Design §parse_duration_seconds] → **Resolved:** `j`/`jaar` (and `y`) map to 365 d.
- [x] CHK002 - Are decimal inputs specified, including the Dutch decimal comma (`1,5 u`) next to `1.5 h`? [Gap, Design §parse_duration_seconds] → **Resolved:** `.` and `,` are both decimal separators; result rounded to an int.
- [x] CHK003 - Is the result for a bare number without a unit (`60`) defined? Today's parser returns "unknown", which would make it manual. [Gap] → **Resolved:** Bare number other than `0` → `None` (manual when a goal exists).
- [x] CHK004 - Does the design say whether CSV/SQL import should store text that equals the tier goal as empty, the way the form does? If not, why do imports and form saves differ? [Gap, Design §Rules] → **Resolved:** Imports store text as given; source computed when read (Design §Rules).
- [x] CHK005 - Does the design define whether the availability summary export (aggregated per BIA) marks a lowest value that comes from a manual override? [Gap, Design §Templates] → **Resolved:** No marker in the summary export (aggregated value).
- [x] CHK006 - Is it specified whether incident steps (which copy `effective_rto`/`effective_rpo` as text) should say that the value is manual? [Gap, Design §API/Interface] → **Resolved:** No marker in incident steps; out of scope.
- [x] CHK007 - Does the design say what the user sees after typing a value that equals the goal (e.g. "240 min" against 4 h)? The text is dropped and the next GET shows "4 h". [Gap, Design §Rules "Revert to tier"] → **Resolved:** No extra message; next GET shows the goal and no manual line.

## Clarity

- [x] CHK008 - Is the "warning-style line" on the form tied to a specific existing style (class or chip) and exact wording in en and nl? [Clarity, Design §Templates] → **Resolved:** Amber chip classes; exact en/nl wording in Design §Templates.
- [x] CHK009 - Is "a small 'manual' badge" specified with its exact label and placement for both RTO and RPO in compact cells such as `components.html` ("RTO: x / RPO: y")? [Clarity, Design §Templates] → **Resolved:** Visible `manual · tier 4 h` after each of RTO and RPO.
- [x] CHK010 - Is it clear which locale's format is used for the pre-filled value (the viewer's UI locale), and that a value pre-filled in nl ("4 u") still counts as equal for an en viewer? [Clarity] → **Resolved:** Viewer's locale; both `h` and `u` parse.
- [x] CHK011 - Is "unparseable → manual" stated as a deliberate rule? For example, "next business day" against a goal is flagged even though it may be intended. [Clarity, Decision 20261021-1655-tier-goal-prefills] → **Resolved:** Stated as deliberate in Design §Rules.
- [x] CHK012 - Is it said explicitly that the `m` prefix means minutes, so "1 month"/"1 maand" is read as 1 minute and becomes manual? Or is that a known limitation to fix? [Clarity, Design §parse_duration_seconds] → **Resolved:** Fixed: `mo`/`maand`/`mnd` = 30 d, matched before `m`.

## Consistency

- [x] CHK013 - Is the source label consistent? The decision says `free_text` (internal), the CSV says `free text`, and the tests may use either. [Consistency, Decision §Decision vs. CSV decision] → **Resolved:** Internal `free_text`; CSV label `free text`; mapping in Design §CSV.
- [x] CHK014 - Does "Readers see the real value" (CSV decision) agree with the CSV skipping components that have no availability row? Components that only follow the tier would be missing from the effective columns. [Conflict, Tasks §Task 15] → **Resolved:** CSV writes one row per component; import skips all-empty rows.
- [x] CHK015 - Does the design use one name for the marker's meaning everywhere: "manually configured" (form), "manual" (badge, CSV)? [Consistency] → **Resolved:** Full term on the form, short term on the marker/CSV.
- [x] CHK016 - Are the hint texts consistent between the item availability page and the component availability page (inherited suffix, tier label)? [Consistency, Design §Availability form handling] → **Resolved:** Both pages use the same `_tier_goal_notes` and macro.

## Measurability

- [x] CHK017 - Can "legacy text becomes effective again" be checked against a defined set of fixtures (hidden stale text, matching text, unparseable text)? [Measurability, Design §Rules] → **Resolved:** Fixture set named in Design §Constitution Check.
- [x] CHK018 - Is the full parser input → seconds table listed (or referenced) so the parser tests can be derived from the requirements? [Measurability, Tasks §Task 12] → **Resolved:** Unit table in Design §parse_duration_seconds.

## Coverage

- [x] CHK019 - Is a manual override that is *weaker* than the tier goal (e.g. RTO 1 d against a 4 h goal) treated the same as a stricter one, or should it be marked differently? [Coverage, Gap] → **Resolved:** Flagged the same; grading by direction deferred.
- [x] CHK020 - Is the behaviour defined when a tier goal is 0 s ("immediate") and the stored text is "immediate", "0" or "-"? [Edge Case] → **Resolved:** `immediate`/`0`/`none`/`-` match a 0 s goal → `tier`.
- [x] CHK021 - Are accessibility requirements defined for the marker? A tooltip only in `title` is not enough for screen readers or PDF output. [Coverage, Gap] → **Resolved:** Visible text, no tooltip; plain text in exports.
- [x] CHK022 - Is the effect on BIAs that can't be edited (archived, or the viewer isn't the author) defined? They see the marker but no editable input. [Coverage] → **Resolved:** Read-only viewers see the marker the same as editors.
- [x] CHK023 - Is the change in behaviour (hidden legacy values reappear) listed as a release note in `docs/history.md`, so operators expect changed incident and summary values? [Coverage, Design §Constitution Check] → **Resolved:** Behaviour-change note in `docs/history.md` (Task 16).

## Summary

- **Total items:** 23
- **Focus areas:** duration parsing (CHK001–003, 010–012, 018, 020), import vs. form consistency (CHK004), reporting surfaces (CHK005–006, 014), UX wording and accessibility (CHK007–009, 021)
- **Resolution:** all 23 items are resolved in decision `20261021-1730-rto-rpo-prefill-checklist-gap-resolutions` and folded into design.md Part 2 and Tasks 12–16.
- **Key gaps (original):** CSV omits tier-only components (CHK014); import does not normalise goal-equal text (CHK004); Dutch `jaar` and decimal-comma parsing (CHK001–002); marker accessibility (CHK021)
