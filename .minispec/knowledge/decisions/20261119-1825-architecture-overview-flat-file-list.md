---
type: decision
id: 20261119-1825-architecture-overview-flat-file-list
date: 2026-11-19
status: accepted
supersedes: 20261118-1505-architecture-overview-pdf-and-delete
superseded_by: null
impacts:
  - scaffold/apps/ssp/models.py
  - scaffold/apps/ssp/forms.py
  - scaffold/apps/ssp/routes.py
  - scaffold/apps/ssp/templates/ssp/view.html
  - scaffold/translations/*
tags: [ssp, architecture-overview, file-upload]
participants: [Ferry Stelte, Claude]
---

# Architecture overview: a flat list of files shown together, no versioning

Partially supersedes `20261118-1505-architecture-overview-pdf-and-delete`.
That decision's file types (PNG/JPEG/PDF), magic-byte MIME detection, 10 MB /
8000 px limits, PDF-as-download handling and help text stay. What changes is
the "one current version plus history" model.

## Context

An SSP's architecture is often described by more than one diagram (context,
network, data flow, deployment). Today the overview is a single slot: each
upload is a new version, only the highest version is shown, and older ones can
be restored or deleted. Users want to upload several files and see them all.

## Options Considered

### Option 1: Flat list
Each file is added or deleted on its own. There are no versions and no restore.
- ✅ Simplest model and UI, and it matches "show them all"
- ✅ Reuses the existing table and blob storage
- ❌ Changing a diagram means delete + upload; the old bytes are gone (the audit log keeps the event)

### Option 2: Flat list + in-place replace
- ✅ Keeps a file's position and identity when it is updated
- ❌ Extra route and UI for a small gain over delete + upload

### Option 3: Snapshot the whole set
Every change creates a new version of the set, which can be restored as a unit.
- ✅ Full history
- ❌ New set/version tables, a more complex UI, and restore semantics for a set

## Decision

Option 1. The architecture overview is an unordered-by-version list of files.
Every stored row is shown. The restore route and the "history" UI are removed.
Upload and delete keep their audit events (`ssp_architecture_overview_uploaded`,
`ssp_architecture_overview_deleted`).

## Consequences

### Positive
- ✅ Several diagrams can be shown together
- ✅ Less code: restore, version numbering and history UI go away

### Negative
- ❌ No way to roll a file back; only the audit log records what was there
- ❌ Existing SSPs with history need a migration decision (see the follow-up decision)
