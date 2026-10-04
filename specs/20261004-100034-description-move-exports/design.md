---
feature: 20261004-100034-description-move-exports
status: planned
created: 2026-10-04
decisions: [20261004-1005-landing-page-exports-layout]
---

# Move Global Exports to the Landing Page – Design

## Overview

The nine global BIA reports move from the "Exports" quick-card on `/bia/index`
to the root landing page (`/`, `template.index`). They appear only for
logged-in users, grouped into three themed cards, with each report's formats
(HTML / PDF / CSV) shown as inline pill links. This is a template and
translation change only. **No routes are added, removed or modified.**

## User Stories

- As a logged-in user, I want all global reports on the home page so I can
  export without first going to the BIA dashboard.
- As a logged-in user, I want reports grouped by theme with every format
  visible so I can find and download the right one in one click.
- As an anonymous visitor, I see the landing page exactly as before.

## Components

### 1. Landing page – `scaffold/apps/template/templates/template/index.html`
Add a "Reports & exports" section below the existing hero/nav buttons, inside:

```jinja
{% if current_user.is_authenticated and 'bia' in registered_blueprints() %}
```

The reports are defined once as a `{% set %}` list (group → reports → formats)
and rendered in a loop. Layout: responsive grid, 1 column on mobile and 3 on
`lg`, one card per group in the existing surface/border style.

| Group | Report | Formats → endpoint/args |
|---|---|---|
| Impact & requirements | CIA – detailed | HTML, PDF → `bia.export_all_consequences` (`format='pdf'`) |
| | CIA – summary | HTML, PDF → `bia.export_all_consequences` `type='summary'` |
| | Availability – detailed | HTML, PDF → `bia.export_availability_requirements` |
| | Availability – summary | HTML, PDF → `bia.export_availability_requirements` `type='summary'` |
| Inventories | Data inventory | CSV → `bia.export_data_inventory` |
| | Component inventory | CSV, HTML, PDF → `bia.export_component_inventory` |
| Architecture & security | Dependencies | HTML, PDF → `bia.export_all_dependencies` |
| | Tiers | HTML, PDF → `bia.export_all_tiers` |
| | Authentication overview | HTML, PDF → `bia.export_authentication_overview` |

Each row shows the report name on the left and pill links on the right, with
Font Awesome icons (`fa-file-code`, `fa-file-pdf`, `fa-file-csv`). The landing
page needs no JavaScript.

### 2. BIA dashboard – `scaffold/apps/bia/templates/bia/dashboard.html`
- Remove the third `bia-dashboard-actions__item` (the global "Exports" card).
- Remove the "Exports" `bia-chip` in the hero.
- **Keep** the per-context "Exports" dropdown on each BIA card and the
  dropdown `extra_js` that drives it.
- Check that the actions grid still looks balanced with 2 items instead of 3.
  Adjust the `.bia-dashboard-actions` columns if needed.

### 3. Translations – `scaffold/translations/en.json`, `nl.json`
New keys under `app.home.exports.*`: section title, short intro, three group
titles, nine report labels. Reuse existing `bia.dashboard.sidebar.export_*`
strings for wording. This also replaces the hardcoded "Export Dependencies" /
"Export Tiers".

## Data Model

None.

## API/Interface

None. All existing export routes, their `@login_required` guards and URLs stay
unchanged.

## Edge Cases

- **Anonymous user on `/`**: section not rendered.
- **BIA module disabled**: section not rendered, so `url_for` raises no `BuildError`.
- **Bookmarked export URLs**: still work (routes untouched).

## Testing

- Rendering `/` while logged in shows the section and links to every endpoint
  above. Logged out, it doesn't.
- Rendering `/bia/index` no longer contains `export_all_tiers` etc. but still
  contains the per-context `export_item` / `export_bia_sql` links.

## Constitution Check

- **Module ownership (I):** The export routes, their logic and the dashboard
  stay in `scaffold/apps/bia/`. The landing page (`scaffold/apps/template/`)
  only *links* to `bia.*` endpoints through `url_for`, which is a documented,
  deliberate cross-module reference. It's guarded by
  `'bia' in registered_blueprints()` so the template module still works without
  BIA. No BIA logic, queries or models are imported into the template module.
- **Security & audit (II):** Who can export doesn't change. Every export route
  keeps its `@login_required`. The links were previously visible to every
  logged-in user on `/bia/index` and are now visible to every logged-in user on
  `/`, so the affected roles are the same. Anonymous users still see no links,
  and calling a route directly still redirects to login. Audit logging
  (`bia.exported` events) sits inside the routes and is unaffected. Operational
  risk: none.
- **Validation (III):** pytest coverage for landing page visibility
  (logged in / anonymous), dashboard removal, and translation-key parity. No
  schema change, so no migration.
- **Localization (IV):** All new copy goes through `_()` with `en` + `nl` keys.
  The two hardcoded English labels become keys. Tailwind tokens only, no
  Bootstrap. Report names match the existing export titles.
- **Operational (V):** No new environment variables, config, deployment or
  scheduled-work changes. User-visible change documented in
  `docs/deployment.md` → "BIA Export Artefacts".

## Out of Scope

- Exports from other modules (CSA, risk, DPIA, …).
- Changing export content, formats or permissions.
- Per-BIA exports (stay on the dashboard).

## Open Questions

- Should the section also appear in the top navigation? (Not planned.)
