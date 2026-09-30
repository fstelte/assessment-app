---
type: checklist
domain: general
feature: component-inventory-export
created: 2026-09-30
status: completed
---

# General Requirements Quality Checklist

**Purpose:** Check that the requirements for the Component inventory export are
complete, clear, consistent and testable before implementation.
**Feature:** component-inventory-export

## Completeness

- [x] CHK001 - Does the design define the CSV character encoding (UTF-8 with or without BOM), so that Dutch characters open correctly in Excel? [Gap, Design §Route step 4]
- [x] CHK002 - Does the design define the CSV delimiter (comma, as in the existing inventory, or semicolon for Dutch-locale Excel)? [Gap]
- [x] CHK003 - Does the design say who may download the export, and whether it covers all non-archived BIAs or only those the user can see or edit? [Gap, Security]
- [x] CHK004 - Are requirements defined for the empty state, when there are no components or no non-archived BIAs, for CSV (headers only?) and HTML/PDF (an empty table or a message?)? [Gap, Edge Case]
- [x] CHK005 - Does the design specify the page layout of the HTML/PDF (e.g. landscape orientation for 8 columns, how long text wraps)? [Gap, Design §Template]
- [x] CHK006 - Are the exact translation key names or a key namespace (e.g. `bia.export.component_inventory.*`) specified, so that en/nl stay in sync? [Completeness, Design §Translations]

## Clarity

- [x] CHK007 - Is "Tier source" defined for a component whose own tier equals the BIA tier? The current rule says "Component" whenever `tier_id` is set; is that the intended rule? [Clarity, Design §Data Model]
- [x] CHK008 - Is the sort order defined for rows that have the same BIA and component name? [Clarity]
- [x] CHK009 - Is it stated which environment decides Authentication and Authorisation (the primary enabled one: production > acceptance > test > development), and that the two may come from different environments? [Clarity, Design §Data Model]
- [x] CHK010 - Is it clear whether the tier label in the CSV is locale-dependent (`TIER n > <translated name>`), which affects anyone filtering on it? [Clarity]

## Consistency

- [x] CHK011 - Are the placeholder values consistent? Information, Owner and Authentication use the untranslated "N/A", while Tier uses the translated "Not set". [Consistency, Design §Data Model]
- [x] CHK012 - Is the open question about unknown `format` values resolved the same way in design.md (still open) and tasks.md (falls back to HTML)? [Consistency]
- [x] CHK013 - Is the `format` value recorded in the audit log defined for PDF downloads? The existing HTML exports log `"html"` even when a PDF is sent. [Consistency, Design §Route step 6]
- [x] CHK014 - Are the column names and order identical between the CSV and the HTML/PDF table? [Consistency]
- [x] CHK015 - Is the default format (`html` when `format` is absent) consistent with the dashboard links, where HTML has no `format` parameter and CSV passes `format='csv'`? [Consistency, Design §Dashboard entry]

## Measurability

- [x] CHK016 - Can "the existing Data Inventory is unchanged" be checked objectively (exact header list and row shape)? [Measurability, Task 1]
- [x] CHK017 - Are the acceptance criteria for the PDF variant defined beyond the content type (e.g. the file name ends in `.pdf`, and what happens when PDF generation fails)? [Acceptance, Task 2]

## Coverage

- [x] CHK018 - Is CSV/formula injection handled for values starting with `=`, `+`, `-` or `@` (component or owner names)? [Coverage, Security]
- [x] CHK019 - Are requirements defined for components with no enabled environments (Authentication "N/A", Authorisation "No")? [Coverage, Edge Case]
- [x] CHK020 - Is the behaviour defined when the PDF engine (Playwright) is unavailable, i.e. is the existing flash + redirect behaviour explicitly accepted? [Coverage, Design §API]

## Summary

- **Total items:** 20
- **Focus areas:** CSV format details, placeholder and label consistency, edge cases, access scope
- **Key gaps identified:**
  - CSV encoding and delimiter not specified (CHK001–002)
  - "N/A" vs "Not set" inconsistency (CHK011)
  - Empty state and PDF layout not defined (CHK004–005)
  - Open question on unknown `format` values not closed in design.md (CHK012)
  - CSV injection not addressed (CHK018)

## Resolutions (2026-09-30)

All items are resolved in `design.md` and `tasks.md`:

- **CHK001–002:** UTF-8 with BOM (`utf-8-sig`), comma delimiter.
- **CHK003:** `@login_required` only, covering all non-archived BIAs, like the
  other BIA exports.
- **CHK004:** with no components, the CSV holds only the header row and the
  HTML/PDF shows a "no components" line.
- **CHK005:** no orientation setting is needed; `html_to_pdf_bytes` renders at
  1280px wide into one page sized to the content.
- **CHK006:** translation keys live under `bia.export.component_inventory.*`.
- **CHK007:** the rule is literal: an own `tier_id` means "Component", even if
  it equals the BIA tier.
- **CHK008:** sort by BIA, then component name, then component id.
- **CHK009:** both values come from the existing resolvers and may come from
  different environments; this is documented.
- **CHK010:** the tier label follows the exporting user's locale; this is
  documented.
- **CHK011:** every missing value shows the translated "Not set".
- **CHK012:** unknown `format` values fall back to HTML; the open question is
  closed in the design.
- **CHK013:** the audit log records the format actually sent (`csv`, `html` or
  `pdf`).
- **CHK014:** CSV and HTML use the same columns in the same order.
- **CHK015:** the HTML link has no `format` parameter (the default); the CSV
  and PDF links pass one explicitly.
- **CHK016:** the Task 1 test asserts the exact old header list.
- **CHK017:** the PDF test checks `application/pdf` and a
  `Component_Inventory_*.pdf` file name; on Playwright failure, the existing
  flash and redirect applies.
- **CHK018:** CSV text cells starting with `=`, `+`, `-` or `@` get a `'`
  prefix. This applies to the CSV only.
- **CHK019:** a component without enabled environments shows "Not set" for
  Authentication and "No" for Authorisation.
- **CHK020:** the existing flash and redirect behaviour is accepted.
