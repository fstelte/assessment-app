---
type: checklist
domain: general
feature: authentication-overview-environments
created: 2026-09-19
status: active
---

# General Requirements Quality Checklist

**Purpose:** Validate the Environments column / tier-summary removal / Users removal requirements are complete, clear, and consistent.
**Feature:** authentication-overview-environments

## Completeness

- [x] CHK001 - Is the Environments cell behaviour defined for a component grouped by the legacy `Component.authentication_method_id` override that has no enabled environments (grouped under a method, yet the cell shows "Not set")? [Gap, Design §Added]
- [ ] CHK002 - Is it specified what "enabled" means for an environment (`is_enabled` only) and how an environment that is disabled but still has a method assigned is treated? [Completeness, Design §Added]
- [ ] CHK003 - Are requirements defined for an environment whose assigned method is inactive (`is_active = False`) or no longer resolvable? [Gap, Design §Added]
- [ ] CHK004 - Is the treatment of the "used for authorisation" flag per environment stated, beyond deferring it to Open Questions? [Completeness, Design §Open Questions]
- [x] CHK005 - Is it stated whether other documents describing the removed summary/Users column (the 20260918 design.md, tasks.md, checklists, and the superseded decision record's status) are updated or left as history? [Gap]
- [ ] CHK006 - Is the empty-export case (zero components) still specified now that the summary table it referred to is removed? [Completeness, Decision 20260918-0552-gap-resolutions]

## Clarity

- [x] CHK007 - Is "one line per enabled environment" defined in terms of rendered output (line breaks, list, separate elements) rather than text format only? [Clarity, Design §Added]
- [x] CHK008 - Is the locale of the method label in the Environments cell specified, given the method summary shows both EN and NL while `_describe_environment_authentication` uses the current locale only? [Clarity, Design §Added]
- [ ] CHK009 - Is the separator/format `<environment label>: <method label>` specified for the "Not set" method case (e.g. "Test: Not set")? [Clarity, Design §Added]
- [ ] CHK010 - Is the column position ("after Owner, before Also used for authorisation") unambiguous for both table types, which currently share the same column order? [Clarity, Design §Added]

## Consistency

- [ ] CHK011 - Is the display order (development to production) consistent with the production-first priority used to decide grouping, and is the difference an intended decision? [Consistency, Design §Added]
- [ ] CHK012 - Does the requirement that the Environments cell lists every enabled environment stay consistent with the "Also used for authorisation" column, which reflects only the primary environment? [Consistency]
- [x] CHK013 - Does the "Tier"/"Info type" column ordering requirement from decision 20260918-0552-gap-resolutions (`BIA, Component, Tier, Info type, Owner, Users`) get explicitly amended to the new order? [Consistency, Decision]
- [ ] CHK014 - Are the design's Removed/Added lists consistent with tasks.md (every removed key/test and added key appears in a task)? [Consistency, Tasks 1-3]
- [x] CHK015 - Is the environment label source consistent (design cites `bia_environment_label` context helper, tasks cite `_environment_label`)? [Consistency, Design vs Tasks]

## Measurability

- [ ] CHK016 - Are acceptance criteria stated for each removed item ("Users", summary section, translation keys) in objective terms? [Measurability, Tasks 2-3]
- [ ] CHK017 - Can "Environments column shows differing methods" be verified with a defined example dataset (which environments, which methods, expected cell text)? [Measurability, Tasks 3]
- [ ] CHK018 - Is Task 1's evidence ("tests run") objective enough to show `environment_usage` was built for every component? [Measurability, Tasks 1]

## Coverage

- [ ] CHK019 - Are the NL rendering requirements (Dutch environment and column labels) covered in acceptance, not only EN? [Coverage, Design §Added]
- [ ] CHK020 - Are requirements defined for very long cells (four environments with long method names) in the printed/exported layout? [Edge Case, Design §Added]
- [ ] CHK021 - Is a component with all four environments assigned the same method addressed (repeat vs collapse)? [Edge Case]
- [ ] CHK022 - Is the impact on the method-summary counts and grouping explicitly confirmed unchanged by an acceptance criterion? [Coverage, Design §Unchanged]

## Summary

- **Total Items:** 22
- **Focus Areas:** Completeness (6), Clarity (4), Consistency (5), Measurability (3), Coverage (4)
- **Key Gaps Identified:** legacy-override components showing "Not set" (CHK001); superseded records not marked stale (CHK005, CHK013); rendered cell format and locale unspecified (CHK007, CHK008); inactive or disabled-environment methods (CHK002, CHK003).
