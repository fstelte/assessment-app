---
type: checklist
domain: general
feature: 20261111-082222-description-create-link
created: 2026-11-11
status: active
---

# General Requirements Quality Checklist (security emphasis)

**Purpose:** Check that the requirements for the principles menu links and the
removed description cap are complete, clear and consistent.
**Feature:** 20261111-082222-description-create-link
**Sources:** design.md, tasks.md,
[[20261111-0827-principles-admin-navigation]],
[[20261111-0828-principle-description-no-length-cap]]

## Completeness

- [x] CHK001 - Does the design define the upper bound that actually applies to a
  description edited in the form? Flask 3.1.3 rejects any single form field
  over `MAX_FORM_MEMORY_SIZE` = 500,000 bytes with a 413, and the decision only
  says "beyond the request size limit". [Gap, Decision 0828 §Consequences]
- [x] CHK002 - Is it specified what happens to principles imported with a
  description over 500 KB? A JSON file upload has no limit
  (`MAX_CONTENT_LENGTH` is unset), so such a principle still can't be saved,
  which contradicts "every principle is editable". [Gap, Design §User Stories]
- [ ] CHK003 - Is the user-facing result of a 413 on the update route defined
  (error page, flash message, lost input)? [Gap, Edge Case]
- [ ] CHK004 - Are display requirements defined for very long descriptions on the
  principles list? The full text ends up in the `title` tooltip of a
  `line-clamp-2` cell. [Gap, Design §Components]
- [ ] CHK005 - Are display requirements defined for long descriptions where ADRs
  show their principles (ADR list, view, print)? [Completeness]
- [x] CHK006 - Is the nav button's active/highlighted state defined for when
  the current page is `admin.principles` or its edit page? [Completeness, Design §Top navigation]
- [x] CHK007 - Is the button's behaviour in the collapsed mobile navigation
  (`#navbarNav`) specified? [Completeness]

## Clarity

- [ ] CHK008 - Is "the Profile button style" for the nav button tied to a
  specific class set, given that Profile and Admin use different visual weights?
  [Clarity, Design §Top navigation]
- [ ] CHK009 - Is "after the sensitivity labels link, before the audit trail"
  the only allowed position, or is ordering free? [Clarity, Design §Admin button row]
- [ ] CHK010 - Are the Dutch label ("Principes") and English label
  ("Principles") confirmed as final wording, consistent with how ADR pages name
  them in nl.json? [Clarity, Constitution IV]
- [x] CHK011 - Is "no length cap" stated as "no application-level cap" so it
  doesn't contradict the framework's 500 KB form field limit? [Clarity, Decision 0828]

## Consistency

- [x] CHK012 - Is the nav button's visibility rule (`has_role('admin')`)
  consistent with the access rule of the Users page that hosts the button row,
  so that admins see both and nobody sees a link that leads to a 403?
  [Consistency, Decision 0827]
- [ ] CHK013 - Does the design say explicitly that users with **both** admin
  and control owner roles see the nav button? [Consistency, Edge Case]
- [ ] CHK014 - Are the validation rules for create, update and import
  consistent after the change (non-empty, whitespace stripped, no length cap)?
  Whitespace-only input fails `DataRequired` in the form and is rejected after
  `strip()` in the importer. [Consistency, Design §Principle form]
- [ ] CHK015 - Do the design's "Out of Scope" items match the "Deferred" notes in
  tasks.md and the negative consequences in both decisions? [Consistency]

## Measurability

- [ ] CHK016 - Does a 6000-character test case prove "editable regardless of
  length", or should the acceptance criteria also include a value near the
  500 KB form field limit? [Measurability, Tasks §Acceptance]
- [x] CHK017 - Is "a non-admin control owner does not see the nav button"
  testable without false positives? The Users page link and the ADR empty-state
  link also point to `/admin/principles`, so the assertion needs a specific
  marker. [Measurability, Tasks §Acceptance]
- [ ] CHK018 - Is "both language files have both keys" tied to a specific check
  (a test, `missing_used_keys.json` or `update_translations.py`)?
  [Measurability, Constitution IV]

## Coverage / Security

- [x] CHK019 - Is the security trade-off of removing the cap (larger request
  bodies, larger audit context, larger exports and backups) described with its
  accepted risk, given that only admins and control owners can write?
  [Coverage, Security]
- [x] CHK020 - Is it stated that the new links add no new route or permission,
  so authorization still relies only on `_require_control_admin` and
  `require_fresh_login`? [Coverage, Security]
- [ ] CHK021 - Is a regression requirement defined so the existing 403 test for
  non-admins (`test_non_admin_gets_403`) stays in scope? [Coverage, Constitution III]

## Summary

- **Total items:** 21
- **Focus areas:** completeness (7), clarity (4), consistency (4),
  measurability (3), coverage/security (3)
- **Main gaps found:**
  - The 500 KB `MAX_FORM_MEMORY_SIZE` default is still a cap, and imported
    principles above it stay uneditable (CHK001–CHK003, CHK011).
  - No display requirements for long descriptions (CHK004–CHK005).
  - The nav button's active state and mobile behaviour are undefined
    (CHK006–CHK007).

## Resolution (2026-11-11, `/minispec.analyze`)

- CHK001, CHK002, CHK011: the importer applies the same `MAX_FORM_MEMORY_SIZE`
  limit as the form; design §Overview and §Principle importer, decision 0828
  amendment.
- CHK006, CHK007: no active state (consistent with "Admin"); the button sits
  in the right-hand group inside `#navbarNav`, so it collapses with the mobile
  menu. Recorded in design §Out of Scope.
- CHK012: the Users page (`_require_admin`) and the nav button
  (`has_role('admin')`) are both admin-only.
- CHK017: the control-owner test looks for the nav button's label/markup; tasks §Acceptance.
- CHK019, CHK020: design §Constitution Check.
- Open: CHK003 (413 page on the edit form), CHK004/CHK005 (displaying long
  descriptions), CHK008–CHK010, CHK013–CHK016, CHK018, CHK021. Can be settled
  during implementation; they don't block it.