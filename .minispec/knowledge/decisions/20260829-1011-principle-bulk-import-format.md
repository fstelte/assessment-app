---
type: decision
id: 20260829-1011-principle-bulk-import-format
date: 2026-08-29
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/ssp/principle_importer.py
  - scaffold/apps/admin/forms.py
  - scaffold/apps/admin/routes.py
tags: [import, architecture-principles, json]
participants: [Ferry Stelte, Claude]
---

# Bulk import file format for Architecture Principles

## Context

Architecture Principles must be bulk-importable by an admin, the same way controls are
(`scaffold/apps/csa/services/control_importer.py`, which accepts a JSON file shaped
`{"controls": [...]}` plus a plain-text NIST fallback parser). We needed to decide
whether to literally reuse the control payload shape (with its `section`/`domain`
fields, which principles don't have) or define a payload tailored to principles.

## Options Considered

### Option 1: Reuse the control import payload shape verbatim
`{"controls": [...]}`-style objects with `section`/`domain`/`description`/`owner`
fields repurposed for principles.
- ✅ Maximum code reuse from `control_importer.py`
- ❌ Forces principle authors to fill in irrelevant fields (`section`, `domain`, `owner`) that don't apply to a principle catalogue
- ❌ Confusing for anyone hand-writing an import file — the field names don't match what a principle actually is

### Option 2: New payload shape tailored to principles, same import mechanics (JSON only, upsert-by-key, created/updated/errors summary)
`{"principles": [{"name": ..., "description": ...}]}` — same overall approach
(single JSON file upload, `FileAllowed(["json"])`, upsert semantics, `ImportStats`
result) but with a payload shape that matches what a principle actually is.
- ✅ Import file is self-explanatory and matches the leaner principle model decided in [[20260829-1011-adr-principle-catalogue-design]]
- ✅ Still reuses the *mechanics* of `control_importer.py` (file handling, upsert pattern, stats reporting) — only the payload schema and field mapping are new
- ❌ Slightly more new code than pure copy-paste (a new `principle_importer.py` module instead of extending the existing one)

## Decision

We chose **Option 2**. The import *mechanism* (JSON file upload via `FileAllowed`,
upsert-by-key semantics, `ImportStats(created, updated, errors)` summary shown to the
admin) is copied from `control_importer.py`, but the *payload shape* is defined fresh
for principles: `{"principles": [{"name": "...", "description": "..."}]}`, matching the
leaner principle model (no `section`/`domain`/`owner`).

Import is JSON-only (no CSV, no plain-text fallback) — the control catalogue's
plain-text NIST parser exists only because NIST controls ship as plain-text exports in
practice; there is no equivalent external plain-text format for architecture
principles, so that fallback path is deliberately not replicated.

Upsert key: case-insensitive `name`. A principle already referenced by an ADR is
still upsertable (fields update in place) but not deletable via import — deletion
guards from [[20260829-1011-adr-principle-catalogue-design]] apply only to the
delete action, not to import-driven updates.

## Consequences

### Positive
- ✅ Admins get an import file format that's self-documenting — a non-technical reviewer can read `principles.json` and understand every field.
- ✅ Reuses proven mechanics (file validation, upsert-by-key, summary reporting) instead of inventing new import UX.

### Negative
- ⚠️ A new `principle_importer.py` module is needed rather than extending `control_importer.py` — some duplication of the "read JSON, validate shape, upsert, collect stats" boilerplate between the two importers.

### Neutral
- If a future feature needs a shared "generic catalogue importer," this duplication is the natural trigger to extract one — but per the constitution, that extraction should wait until a second real need appears, not be built preemptively here.

## Code References

- Pattern to mirror (mechanics only, not payload shape): `scaffold/apps/csa/services/control_importer.py` (`upsert_control()`, `import_controls_from_mapping()`, `ImportStats`)
- Form to mirror: `scaffold/apps/admin/forms.py:21` (`ControlImportForm` → new `PrincipleImportForm`, `FileField` + `FileAllowed(["json"])`)
- Route to mirror: `scaffold/apps/admin/routes.py:206-259` (file upload + `json.loads` handling in `controls()`)

## Related Decisions

- [[20260829-1011-adr-principle-catalogue-design]]

## Notes

Example import file (also included in `specs/20260829-095929-description-adr-https/design.md`):

```json
{
  "principles": [
    {
      "name": "Least Privilege by Default",
      "description": "Grant the minimum access required for a role or service to perform its function; expand access only with documented justification."
    },
    {
      "name": "Prefer Managed Services",
      "description": "Use cloud-managed services over self-hosted equivalents unless a documented constraint (cost, compliance, latency) requires otherwise."
    },
    {
      "name": "Encrypt Data In Transit and At Rest",
      "description": "All data, internal or external, must be encrypted using approved algorithms both while stored and while moving between systems."
    },
    {
      "name": "Single Source of Truth per Domain",
      "description": "Each data domain has exactly one authoritative system of record; other systems consume copies, never compete as the source."
    }
  ]
}
```
