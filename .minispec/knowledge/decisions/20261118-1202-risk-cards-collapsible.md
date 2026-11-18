---
type: decision
id: 20261118-1202-risk-cards-collapsible
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/risk/templates/risk/dashboard.html
tags: [risk, workspace, ui]
participants: [Ferry Stelte, Claude]
---

# Workspace risk cards are native details elements, collapsed by default

## Context

The workspace cards are tall: score, scale, components, controls, tickets
and actions. The engineer wants them to take less space.

## Options Considered

- **A: Native `<details>`/`<summary>`, collapsed by default (chosen).**
- B: The same, but expanded by default.
- C: Collapsed by default, with each card's open or closed state remembered
  in the browser.

## Decision

- Each card is a `<details class="risk-card">`. Its `<summary>` row shows:
  - the severity pill;
  - the title;
  - the actual score;
  - the approval pill;
  - the due status pill;
  - the Mitigated pill, when the risk is mitigated.
- The full card body is the current content, unchanged.
- No `open` attribute, so cards start collapsed.
- "Expand all" and "Collapse all" buttons above the grid. A small script
  sets or removes `open` on every card, using a CSP nonce like the page's
  other inline scripts. Without JS, each card still toggles on its own.
- A `#risk-<id>` URL fragment (a bookmarked or shared link to one card) opens
  that card. The matrix doesn't link to cards today.

## Consequences

### Positive
- ✅ Native expand and collapse, accessible from the keyboard, with no
  framework needed.
- ✅ The page gets much shorter with many risks.

### Negative
- ⚠️ Open or closed state isn't remembered across page loads.
