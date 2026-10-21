---
type: decision
id: 20261021-1424-consequence-category-labels-storage
date: 2026-10-21
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/bia/models/__init__.py
  - scaffold/apps/bia/routes.py
tags: [bia, consequences, data-model]
participants: [Ferry Stelte, Claude]
---

# Consequence category labels stored comma-joined in the existing column

## Context

A BIA consequence is recorded against one CIA security property. The six
consequence categories (financial, operational, reputation and trust,
regulatory, human and safety, privacy) become multiselect labels on that
consequence. Today the form is already multiselect, but every selected category
creates its own `Consequences` row, which duplicates the impact and
justification for each one.

## Options Considered

### Option 1: Comma-joined values in `consequence_category` (chosen)
Store e.g. `financial,operational` in the existing Text column.
- ✅ No schema change and no migration.
- ✅ `Consequences.get_categories()` and the chip rendering in
  `manage_item_consequences.html` already handle comma-separated values.
- ✅ CSV/SQL import/export, cloning and audit hooks keep working unchanged.
- ❌ Filtering by one category needs a LIKE match (not needed today).

### Option 2: Association table
- ✅ Normalised and easy to query per label.
- ❌ Needs a migration and changes to import/export, cloning and audit.

### Option 3: JSON column
- ❌ Needs a type-change migration without a real query benefit over option 1.

## Decision

Keep `consequence_category` as Text and store the selected category values
joined by commas, using the existing lowercase choice keys from
`ConsequenceForm`. Read them through `get_categories()`.

## Consequences

- Create and edit write a single row for all selected categories.
- Edit stops rejecting more than one category.
- Category values must never contain a comma (true for the current six).
- Display goes through `category_label()` / filter `consequence_category`, which
  maps keys to `bia.consequence_category.<key>` (Constitution IV). Unknown legacy
  values are shown raw and sort after the six known ones.
