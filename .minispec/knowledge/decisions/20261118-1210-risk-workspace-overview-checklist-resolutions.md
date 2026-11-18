---
type: decision
id: 20261118-1210-risk-workspace-overview-checklist-resolutions
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/risk/routes.py
  - scaffold/apps/risk/templates/risk/dashboard.html
  - scaffold/apps/risk/templates/risk/overview.html
  - scaffold/apps/risk/templates/risk/form.html
  - scaffold/translations/en.json
  - scaffold/translations/nl.json
tags: [risk, overview, workspace, ux, checklist]
participants: [Ferry Stelte, Claude]
---

# Gap resolutions from the Part 3 UX checklist

## Context

The UX checklist for Part 3 (`checklists/workspace-overview.md`) found gaps
in the design for the open-only workspace, the overview page, the collapsible
cards and the reopen flow. The engineer accepted the proposed resolutions.

## Decision

**Workspace (§15)**
- **Empty state, no filter set, and closed risks exist:** "No open risks."
  with a link to the Risk overview. "No risks recorded yet" stays for a
  database with no risks at all. A BIA filter that matches nothing keeps
  today's fallback. (CHK001)
- **Close feedback:** the existing `risk.flash.archived` text becomes
  'Risk "{title}" closed. You can find it on the Risk overview.' The key is
  unchanged. (CHK002)

**Collapsible cards (§17)**
- **The summary row is one line that wraps on narrow screens:**
  - the severity pill;
  - the title, truncated with an ellipsis on wide screens;
  - the actual score;
  - the approval pill;
  - the due status pill;
  - the Mitigated pill, when set.
- **Stays in the body:** the treatment pill, the description, the PASTA
  source badge and everything below them. (CHK003, CHK011)
- **Grid:** cards align to the top, so an open card doesn't stretch its
  closed neighbours. (CHK011)
- **Expand all and Collapse all** only render when there are cards. (CHK004)
- **`#risk-<id>` with no matching card** (closed or filtered out) does
  nothing. There's no error and no scrolling. (CHK020)
- **Accessibility:**
  - The native `<summary>` is keyboard-focusable.
  - It gets a visible focus outline in the page `<style>` block
    (`:focus-visible`).
  - Expand all and Collapse all are `<button type="button">`s with text
    labels, and have `aria-controls` pointing to the grid's id. (CHK019)

**Overview (§16)**
- **Source:** shown as a small muted label in the title cell: "Threat" for
  a risk linked to a scenario, "PASTA" for one with a PASTA origin, and
  nothing for a manual risk. (CHK005)
- **Empty cells:**
  - a risk with no BIA components shows "–" in the BIA column;
  - the owner column shows "–" when there's no owner, including when the
    owner was deleted (the FK is SET NULL);
  - a risk without a severity shows "Severity pending", as the workspace
    does. (CHK006)
- **Dates:** the overview and the edit-page banner both use `'%d %b %Y'`
  and the existing `risk.status.closed_on` key. (CHK007)
- **Status:** closed wins. A closed and mitigated risk shows "Closed on D".
  Mitigated only shows for open risks. (CHK008)
- **Order:**
  1. open risks before closed ones;
  2. then actual score, highest first, with no score last;
  3. then title, case-insensitive.

  The same rule applies within both groups. (CHK009, CHK010)
- **Narrow screens:** the table sits in an `overflow-x-auto` wrapper, so it
  scrolls sideways inside its container and never the page. (CHK023)
- **Pill classes and labels:** the severity pills use the workspace's
  `severity_class` mapping, and the approval pills use the same
  `approval_pills` mapping and `risk.approval.state.*` labels as the
  workspace. The mapping is duplicated in the overview template, where it's
  about six lines. (CHK015)
- **BIA filter:** the same `bia` parameter, parsed by the shared
  `_bia_filter_args()`. Unknown ids are ignored, and Clear resets every
  filter. (CHK014)

**Edit page (§18)**
- **Position:** the closed banner is the first card in the form, above the
  approval panel and the threat-managed note. (CHK012)
- **PASTA risks:** reopened by hand like manual risks. Republishing the
  conclusion also reopens the risk, as `publish_pasta_conclusion_to_risk`
  already does. There's no revalidation guard. (CHK021)
- **Threat-linked risks:** the edit route re-syncs before rendering. If the
  scenario has already been reopened, the risk is open by the time the page
  renders and the banner doesn't show. That's correct, and the note only
  shows while the scenario still closes the risk. (CHK022)

**Docs (Task 21)**
- `docs/risk.md` keeps "dashboard" in existing sections. New text says
  "risk workspace (`/risk`)" the first time it's used. (CHK016)

## Consequences

- **New translation keys:**
  - `risk.dashboard.no_open_risks`
  - `risk.dashboard.no_open_risks_hint`
  - `risk.overview.source_threat`
  - `risk.overview.source_pasta`
- `risk.flash.archived` changes its text in EN and NL.
- Tests that assert the old archived wording need updating.
