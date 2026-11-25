---
type: decision
id: 20261119-1827-architecture-overview-batch-upload-all-or-nothing
date: 2026-11-19
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/ssp/forms.py
  - scaffold/apps/ssp/routes.py
  - scaffold/apps/ssp/templates/ssp/view.html
tags: [ssp, architecture-overview, file-upload, validation]
participants: [Ferry Stelte, Claude]
---

# Architecture overview: multi-select upload, all-or-nothing validation, no count limit

Follows from `20261119-1825-architecture-overview-flat-file-list`.

## Context

The upload form takes one file today. With a set of files, users should be able
to pick several at once. That raises the question of what to do when only some
of the selected files are valid, and whether to limit how many there can be.

## Options Considered

### Partial failure
- **All or nothing**: ✅ predictable, nothing half-applied; ❌ the user re-submits the valid files
- **Save the valid ones**: ✅ fewer re-uploads; ❌ a partly applied result that is easy to miss in a flash message

### Count limit
- **10 per request + MAX_CONTENT_LENGTH**: ✅ bounds the request size; ❌ an arbitrary cap
- **Total cap per SSP**: ✅ bounds storage; ❌ arbitrary, and blocks legitimate large SSPs
- **No limit**: ✅ nothing to explain; ❌ one request can be very large

## Decision

- The file input gets `multiple`. The form field becomes a `MultipleFileField`,
  and each file is validated with the existing rules (type, magic bytes,
  10 MB, 8000 px for images).
- **All or nothing**: if any file fails, nothing is saved. Every error is
  flashed, prefixed with the offending filename (for example
  "network.svg: file type not allowed"). When all files pass, they are saved
  in one transaction, with one `ssp_architecture_overview_uploaded` audit event
  per file.
- **No count limit**, neither per request nor per SSP. `MAX_CONTENT_LENGTH` stays
  unset. This is an accepted risk: the app is used by authenticated internal
  users, and the per-file 10 MB limit still applies.
  *Amended by 20261120-0900 (CHK007):* the bundled nginx caps a request at
  12 MB, so the gateway limit is raised to `100m`, and a `ui.js` check blocks
  a selection over 100 MB in total before submit.
- An empty submission still fails with the existing "required" error.

## Consequences

### Positive
- ✅ Several diagrams in one action
- ✅ No partial state to explain

### Negative
- ❌ One bad file blocks the whole batch
- ❌ Request size is unbounded (accepted risk; revisit if it causes problems)
