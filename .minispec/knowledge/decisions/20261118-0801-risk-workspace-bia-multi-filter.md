---
type: decision
id: 20261118-0801-risk-workspace-bia-multi-filter
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/risk/routes.py
  - scaffold/apps/risk/templates/risk/dashboard.html
  - scaffold/translations/en.json
  - scaffold/translations/nl.json
tags: [risk, bia, filter, dashboard]
participants: [Ferry Stelte, Claude]
---

# Risk workspace filters by one or more BIAs on the server

## Context

The risk dashboard (`risk.dashboard`) shows every risk with no filtering. Risks
link to BIA components, and each component belongs to a BIA (`ContextScope`).
Users want to look at the risks of specific BIAs.

## Options Considered

- A: Server-side, single BIA (`?bia=<id>`).
- B: Client-side JS that hides and shows cards.
- **C: Server-side, multi-select (chosen).**

## Decision

- Use a repeatable query param: `GET /risk/?bia=3&bia=7`. No param, or an
  empty one, means all risks.
- A risk matches when **any** of its components belongs to **any** selected
  BIA. Use an `EXISTS` / `any()` filter on `Risk.components`.
- The filter applies to the cards, the hero metrics and the matrix alike.
- A filter form at the top of the dashboard: a multi-select of BIAs that have
  at least one component, plus Apply and Clear. Use the Tailwind styling
  already on the page.
- Risks with no components never match a BIA filter. They show only when no
  filter is set.
- Invalid or unknown ids are ignored.

## Consequences

### Positive
- ✅ The metrics and matrix stay consistent with the visible cards.
- ✅ A filtered view has a URL you can bookmark and share.

### Negative
- ⚠️ Changing the filter reloads the page.
