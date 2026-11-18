---
type: checklist
domain: ux
feature: 20261118-074624-risk-workspace-sync-bia-filter
created: 2026-11-18
status: completed
---

# UX Requirements Quality Checklist: Open-Only Workspace, Risk Overview and Collapsible Cards

**Purpose:** Check that the Part 3 requirements are complete, clear and
consistent before implementation (design §15–18, Tasks 17–21).
**Feature:** 20261118-074624-risk-workspace-sync-bia-filter, Part 3

## Completeness

- [x] CHK001 - Does the design say which empty state the workspace shows
  when risks exist but all are closed? The current fallback, "No risks
  recorded yet. Capture the first risk", would be wrong. [Gap, Design §15]
  - Resolved: "No open risks." with a link to the overview. "No risks recorded yet" only shows when there are no risks at all (§15, Task 17/19).
- [x] CHK002 - Does the design say what the user sees after closing a risk
  from a workspace card, now that the card disappears? For example, a flash
  message pointing to the overview. [Gap, Design §15]
  - Resolved: the `risk.flash.archived` text now points to the Risk overview (§15, Task 17).
- [x] CHK003 - Is the content of the summary row for a collapsed card fully
  listed, including the threat or PASTA source badge, and does the design
  say whether those stay in the body only? [Completeness, Design §17]
  - Resolved: the summary has severity, title, score, approval, due and Mitigated. The treatment pill, description and PASTA badge stay in the body (§17).
- [x] CHK004 - Does the design say whether the Expand all and Collapse all
  controls appear when there are no cards? [Gap, Design §17]
  - Resolved: the buttons only render when there are cards (§17, Task 18).
- [x] CHK005 - Does the overview show a risk's source (manual, threat or
  PASTA) somewhere? If not, is leaving it out stated as a choice?
  [Gap, Design §16]
  - Resolved: a muted "Threat" or "PASTA" label in the title cell, nothing for manual risks (§16).
- [x] CHK006 - Does the design define the BIA cell for a risk with no linked
  components, and the owner cell for a deleted owner?
  [Completeness, Design §16]
  - Resolved: "–" for no BIA, and for no owner or a deleted one (SET NULL). "Severity pending" for a missing severity (§16).
- [x] CHK007 - Is the "Closed on D" date format given for the overview and
  the edit-page banner, and is it the same `'%d %b %Y'` the approval panel
  uses? [Completeness, Design §16, §18]
  - Resolved: `'%d %b %Y'` with the `risk.status.closed_on` key on both pages (§16, §18).

## Clarity

- [x] CHK008 - Does the overview status column say which status wins for a
  risk that is both closed and mitigated: "Closed on D" or "Mitigated"?
  [Clarity, Design §16]
  - Resolved: closed wins. Mitigated only shows for open risks (§16).
- [x] CHK009 - Is the order within the overview's closed group stated? It
  could be by actual score, as for open risks, or by most recent close.
  [Clarity, Design §16]
  - Resolved: the same rule in both groups: actual score descending, no score last, then title (§16).
- [x] CHK010 - Is there a tie-breaker for the row order when two risks have
  the same actual score, or no score? [Clarity, Design §16]
  - Resolved: tie-breaker is title, case-insensitive (§16, Task 19).
- [x] CHK011 - Does the design define a "compact" collapsed card? For
  example: one line, the title truncated or wrapped, and how the grid lines
  up cards of different heights. [Clarity, Design §17]
  - Resolved: one line with the title truncated on wide screens, wrapping on narrow ones. Grid `align-items: start` (§17).
- [x] CHK012 - Does the design say where the closed banner goes on the edit
  page relative to the approval panel and the threat-managed note?
  [Clarity, Design §18]
  - Resolved: the first card on the form, above the approval panel and the threat note (§18).

## Consistency

- [x] CHK013 - Are decision 0830 and its amendment aligned with design §15,
  so that no remaining text says closed risks show on the matrix or on
  filtered views? [Consistency]
  - Resolved: decision 0830 has an Amendments note pointing to 1200. §15 says the same.
- [x] CHK014 - Does the overview's BIA filter match the workspace's: the
  same parameter, unknown ids ignored, and the same Clear behaviour?
  [Consistency, Design §16, Task 19]
  - Resolved: the shared `_bia_filter_args()`, same `bia` parameter, and Clear resets everything (§16, Task 17/19).
- [x] CHK015 - Are the severity and approval pills on the overview, the
  workspace summary row and the edit page specified with the same labels
  and classes? [Consistency]
  - Resolved: the same `severity_class` and `approval_pills` mappings and `risk.approval.state.*` labels (§16, decision 1210).
- [x] CHK016 - Does the release-notes requirement (Rollout) match the
  docs/risk.md text in Task 21? docs/risk.md calls it the "dashboard", the
  design the "workspace". [Consistency]
  - Resolved: new docs text says "risk workspace (`/risk`)", and existing sections keep "dashboard" (Task 21).

## Measurability

- [x] CHK017 - Can "removed from the workspace" be checked objectively for
  each surface: cards, the four hero metrics, the matrix and `mine_count`?
  [Measurability, Design §15]
  - Resolved: Task 17 acceptance names the cards, metrics, matrix and `mine_count`.
- [x] CHK018 - Is "cards start collapsed" stated in a testable form: no
  `open` attribute, with the fragment exception for `#risk-<id>`?
  [Measurability, Design §17]
  - Resolved: no `open` attribute in the rendered HTML. The hash only opens a card in JS (Task 18 acceptance).

## Coverage

- [x] CHK019 - Does the design cover accessibility for the collapsible
  cards? That means keyboard focus on `<summary>`, a visible focus style,
  and button labels for Expand all and Collapse all. [Coverage, Design §17]
  - Resolved: native `<summary>` with `:focus-visible`, plus text-labelled `type="button"` controls with `aria-controls` (§17).
- [x] CHK020 - Does it say what happens when `#risk-<id>` names a risk that
  is closed or filtered out, so there is no card to open?
  [Edge Case, Design §17]
  - Resolved: a hash that matches no card does nothing (§17).
- [x] CHK021 - Is the edit-page Reopen flow defined for a closed PASTA risk
  whose conclusion needs revalidation? Can it be reopened, or does
  republishing control it? [Edge Case, Design §18]
  - Resolved: PASTA risks reopen by hand like manual ones, with no revalidation guard. Republishing reopens them too, which already happens (§18).
- [x] CHK022 - Is the threat-linked note correct for a closed risk whose
  scenario has already been reopened? Opening the page re-syncs the risk, so
  the banner might never show. [Edge Case, Design §18]
  - Resolved: the edit page re-syncs first, so a reopened scenario means an open risk and no banner. The note only shows while the scenario closes the risk (§18).
- [x] CHK023 - Is the overview's behaviour stated for narrow screens? Eight
  columns could scroll sideways or collapse. [Coverage, Design §16]
  - Resolved: the table sits in an `overflow-x-auto` wrapper (§16, Task 19).

## Summary

- **Status:** all 23 items resolved in decision
  `20261118-1210-risk-workspace-overview-checklist-resolutions`, design.md Part 3
  and Tasks 17–21.

- **Total items:** 23
- **Focus areas:** workspace empty and close feedback; the overview columns,
  order and states; the collapsible card interaction and accessibility; the
  edit-page reopen edge cases.
- **Key gaps found:**
  - The all-closed empty state on the workspace (CHK001).
  - No feedback after a card disappears on close (CHK002).
  - Status precedence and sort order within the closed group (CHK008,
    CHK009).
  - Narrow-screen behaviour of the overview table (CHK023).
