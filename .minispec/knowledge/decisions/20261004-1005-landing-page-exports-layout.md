---
type: decision
id: 20261004-1005-landing-page-exports-layout
date: 2026-10-04
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/template/templates/template/index.html
  - scaffold/apps/bia/templates/bia/dashboard.html
  - scaffold/translations/en.json
  - scaffold/translations/nl.json
  - docs/deployment.md
tags: [bia, export, landing-page, ui]
participants: [Ferry Stelte, Claude]
---

# Global BIA exports move to the landing page as grouped cards with inline format links

## Context

The nine global BIA reports (data inventory, CIA detailed/summary, availability
detailed/summary, dependencies, tiers, authentication overview, component
inventory) lived in an "Exports" quick-card on `/bia/index`, each behind a
format dropdown. We want them on the root landing page (`template.index`),
visible only to logged-in users, and removed from the BIA dashboard. Routes stay
unchanged.

## Options Considered

### Option 1: Grouped cards, inline format links (chosen)
Three themed cards: **Impact & requirements** (CIA ×2, availability ×2),
**Inventories** (data inventory, component inventory), **Architecture &
security** (dependencies, tiers, authentication overview). Each report is one
row: its name plus small HTML / PDF / CSV pill links.
- ✅ Every format visible and one click away.
- ✅ No dropdown JS on the landing page.
- ✅ Grouping gives the page a clear structure.
- ❌ Takes more vertical space than dropdowns.

### Option 2: Tile grid with dropdowns
- ✅ Reuses the existing dropdown pattern.
- ❌ Formats hidden behind a click; JS must be moved or duplicated.

### Option 3: Single flat-list card
- ✅ Minimal.
- ❌ Nine ungrouped rows are harder to scan.

## Decision

Option 1. The reports are defined as a `{% set %}` list in the landing template
and rendered in a loop. That keeps the change template-only with no Python
and no duplicated markup.

Related scope decisions:
- The per-BIA "Exports" dropdown (HTML/SQL for one context) **stays** on each
  dashboard card. It acts on a single BIA, not the whole set, so it belongs with
  Edit/Copy/Archive. The dashboard keeps its dropdown JS for this.
- The "Exports" chip in the dashboard hero is removed along with the card.
- Visibility guard: `current_user.is_authenticated and 'bia' in
  registered_blueprints()`, so the root page can't fail when the BIA module is
  disabled via `SCAFFOLD_APP_MODULES`.
- The hardcoded "Export Dependencies" / "Export Tiers" labels become i18n keys
  (en + nl).

## Consequences

- No route, permission or URL changes. Bookmarked export URLs keep working.
- Anonymous visitors see the landing page unchanged.
- Users who looked for exports on `/bia/index` must now go to `/`.
