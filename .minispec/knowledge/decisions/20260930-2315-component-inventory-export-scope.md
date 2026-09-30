---
type: decision
id: 20260930-2315-component-inventory-export-scope
date: 2026-09-30
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/bia/routes.py
  - scaffold/apps/bia/templates/bia/dashboard.html
tags: [bia, export, tier, authorisation]
participants: [Ferry Stelte, Claude]
---

# New tiered component inventory export alongside the Data Inventory

## Context

The existing `export_data_inventory` produces a CSV (BIA, Systeem, Informatie,
Eigenaar, Authenticatie, Beheer) with no HTML/PDF variant. Engineers want the
same inventory with component tiering and the authorisation flag, without the
"Beheer" (technical administrator) column, and available as CSV, HTML and PDF.

## Options Considered

### Option 1: New export, keep the existing one (chosen)
- ✅ Existing Data Inventory consumers are unaffected.
- ❌ Two similar exports to maintain.

### Option 2: Replace the existing Data Inventory
- ✅ One export instead of two near-duplicates.
- ❌ Silently changes the columns of a file others may already process.

## Decision

- **New export** next to the existing Data Inventory; the old one is untouched.
- **Dashboard**: one dropdown in the sidebar exports list with CSV, HTML and PDF
  entries, like the other exports.
- **Tier**: the component's `effective_tier` label, plus an indicator whether
  the tier is set on the component or inherited from the BIA
  (per [[20260925-0620-component-tier-inherit-from-bia]]).
- **Authorisation**: Yes/No only, from `_resolve_component_authorization_usage()`
  (primary environment). The note is not exported.
- **Removed**: "Beheer" (technical administrator).
- **Inherited marker**: a separate "tier source" column (Component / BIA), not a
  suffix in the tier cell, so it can be filtered in a spreadsheet.
- **Headers**: translated via i18n keys (en + nl), shared by CSV and HTML/PDF,
  rather than hardcoded Dutch like the old inventory.
- **Route**: one view with `?format=csv|html|pdf`; rows are built once, the
  CSV branch writes a file, the other branches render a template and go
  through `_send_export_response()`. Unknown formats fall back to HTML.
- **CSV details** (from the requirements checklist):
  - UTF-8 with BOM, comma delimiter.
  - Every missing value shows the translated "Not set" (no "N/A").
  - Text cells starting with `=`, `+`, `-` or `@` get a `'` prefix to prevent
    spreadsheet formula injection. This applies to the CSV only; the old
    exports are unchanged.

## Consequences

### Positive
- ✅ Reuses `_send_export_response()` for HTML/PDF and existing resolvers for
  authentication/authorisation.

### Negative
- ⚠️ Column logic duplicated in part with `export_data_inventory`.

## Related Decisions

- [[20260925-0620-component-tier-inherit-from-bia]]
- [[20260918-1700-authorisation-flag-scope-and-shape]]
