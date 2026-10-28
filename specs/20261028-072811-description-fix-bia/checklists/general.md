---
type: checklist
domain: general
feature: 20261028-072811-description-fix-bia
created: 2026-10-28
status: completed
---

# General Requirements Quality Checklist

**Purpose:** Validate that the requirements for the component modal URL fix are complete, clear and consistent.
**Feature:** 20261028-072811-description-fix-bia

## Completeness

- [x] CHK001 - Is the expected URL for each of the four modal actions stated, or only the edit one? [Completeness]
  - Resolved: design §Expected URLs has a table with the template and the built URL for all four.
- [x] CHK002 - Does the design define which users see the modal's **Edit** button? [Gap]
  - Resolved: unchanged on purpose. `edit_item` and `edit_component_form` both check `_can_edit_context` on the server. See design §Authorisation and navigation.
- [x] CHK003 - Are the source and form of `componentId` stated? [Gap]
  - Resolved: it always comes from server-rendered `data-component-id="{{ component.id }}"` (an integer). See design §Components.
- [x] CHK004 - Does the design say whether the fetch, the edit link and the consequences link share one id source? [Completeness]
  - Resolved: all of them, plus the modal's delete button, are set from the same `componentId` in the view handler.

## Clarity

- [x] CHK005 - Is "the id can sit anywhere in the path" scoped precisely? [Clarity]
  - Resolved: the **last** whole `/0` segment is replaced. The design, decision and task all say so.
- [x] CHK006 - Is it explicit that the regex must not match `10` or `/05`, and has it been checked against all four route shapes? [Clarity]
  - Resolved: design §Components explains each part of the regex. It was run in Python against all four templates, a `/0` prefix and a `/x10` prefix, and all matched the expected output.
- [x] CHK007 - Is it clear that `.replace('/0', '/')` must be removed from all four definitions? [Clarity]
  - Resolved: task step 3 says "all four", and the test asserts no trailing `.replace` on any of them.

## Consistency

- [x] CHK008 - Do the design, decision and task name the same helper and regex? [Consistency]
  - Resolved: all three use `withId(tpl, id)` with `/\/0(?=\/|$)(?!.*\/0(?:\/|$))/`.
- [x] CHK009 - Does the claim "only `context_form.html`" match the grep scope? [Consistency]
  - Resolved: the grep was rerun repo-wide with `git grep` (excluding `specs/`, `.minispec/`, `graphify-out/`) and found matches only at lines 350-353.
- [x] CHK010 - Are the line references in the tasks marked as a guide only? [Consistency]
  - Resolved: the task says line numbers refer to commit `0219176` and to find the code by its content if they've moved.

## Measurability

- [x] CHK011 - Does the regression test cover the reported bug, not just the template? [Measurability]
  - Resolved: the test extracts the shipped `withId` regex from the page and applies it in Python to all four templates, plus a prefixed one. The click wiring stays manual-only and is listed as a known limit in the decision.
- [x] CHK012 - Is the `//edit` assertion reliable? [Measurability]
  - Resolved: dropped during implementation. The bad URL is only assembled in the browser at click time, so a server-side body check can't see it, and it passed on the broken code. The `var ...Url = '...';` and `withId` regex assertions are the real guards.
- [x] CHK013 - Can someone other than the author repeat the manual acceptance step? [Measurability]
  - Resolved: the task has numbered steps with a named throwaway BIA and components, and the expected URL for each step.
- [x] CHK014 - Does the manual delete check use throwaway data? [Measurability]
  - Resolved: steps 1 and 5 create and then delete the throwaway BIA `URL check`.

## Coverage

- [x] CHK015 - Is a URL prefix whose path contains a `/0` segment covered? [Edge Case]
  - Resolved: this is a real case, because ProxyFix `x_prefix` is configurable. The regex replaces only the last `/0` segment, and the test checks `/0/bia/component/0/edit`.
- [x] CHK016 - Is the behaviour for a missing or empty `data-component-id` defined? [Edge Case]
  - Resolved: the modal's delete button starts with `data-component-id=""`, so this does happen. The view handler and `doDeleteComponent` return early, with no request and no confirm dialog.
- [x] CHK017 - Does the design say where the edit form returns after saving? [Gap]
  - Resolved: unchanged, still `/bia/components?scope=<name>`. It's out of scope and noted as a possible follow-up.
- [x] CHK018 - Does Out of Scope rule out similar JS URL builders elsewhere? [Coverage]
  - Resolved: the repo-wide grep covered both quote styles and `_id=0)`. No other matches.

## Constitution Compliance

- [x] CHK019 - Does the plan explicitly confirm module ownership, security and audit impact, validation scope, localization impact, and operational or migration impact? [Constitution, Delivery Workflow]
  - Resolved: design §Constitution Check covers all five, and the decision records the rejected simpler options.

## Summary

- **Total Items:** 19, all resolved and checked against design.md, tasks.md and the decision record during `/minispec.analyze` (2026-10-28)- **Spec changes:** an Expected URLs table; the regex now replaces the last `/0` segment; empty-id guards; a stronger regression test; repeatable manual steps on throwaway data; edit visibility and the post-save redirect explicitly unchanged.
- **Remaining known limit:** the click → `withId` wiring is checked by hand only, because there is no JS test harness.
