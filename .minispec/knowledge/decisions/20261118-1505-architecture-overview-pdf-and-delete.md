---
type: decision
id: 20261118-1505-architecture-overview-pdf-and-delete
date: 2026-11-18
status: accepted
supersedes: 20260829-1230-architecture-overview-image-design
superseded_by: null
impacts:
  - scaffold/apps/ssp/forms.py
  - scaffold/apps/ssp/routes.py
  - scaffold/apps/ssp/templates/ssp/view.html
  - scaffold/translations/*
tags: [ssp, architecture-overview, file-upload, pdf]
participants: [Ferry Stelte, Claude]
---

# Architecture overview: accept PDFs, allow deleting any version, explain what can be uploaded

Partially supersedes `20260829-1230-architecture-overview-image-design`. DB-blob
storage, version numbering and copy-forward restore stay as they are. Two things
change: "image only" and "append-only, never delete".

## Context

Users report that uploads "don't always" work. The code shows several silent
failure modes: only PNG/JPEG are accepted, the limits are 5 MB and 8000 px, the
file input has no `accept` attribute or hint, and errors only appear as a flash
message after a redirect. The stored `mime_type` is the browser-supplied one,
which may be `application/octet-stream` and then renders badly. Users also want
to upload PDFs and remove uploads.

The app's security headers (`X-Frame-Options: DENY`, `object-src 'none'`,
`frame-ancestors 'none'`) block embedding a PDF inline.

## Options Considered (removal)

### Option 1: Hard-delete any single version
- ✅ A wrong upload can be removed; the previous version becomes current again
- ❌ Ends strict immutability (the audit log keeps the record)

### Option 2: Remove all versions only
- ✅ Keeps the history immutable otherwise
- ❌ No way to drop one wrong upload

### Option 3: Soft delete
- ✅ Bytes are kept for audit
- ❌ Data is not actually removed; needs a migration

## Decision

- **Removal**: Option 1. `POST /ssp/<id>/architecture-overview/<version_id>/delete`
  shows a confirm prompt, deletes the row and writes the audit event
  `ssp_architecture_overview_deleted` (with `ssp_id`, `version_number`,
  `original_filename`). "Current" is still the highest remaining
  `version_number`. The next upload uses max+1 of the remaining rows, so a
  deleted top number may be reused (clarified in 20261118-1530, CHK010). A
  delete button appears on the current version and on each history entry.
- **PDF support**: accept `.pdf` next to PNG/JPEG. A PDF is validated by its
  `%PDF-` magic bytes. It is not rendered server-side.
- **MIME type** comes from the detected content (`image/png`, `image/jpeg`,
  `application/pdf`), not from the browser.
- **Display**: an image is shown inline as today. A PDF is shown as a file card
  (filename, size, uploader, date) with a "Download PDF" button. The stream
  route serves PDFs with `Content-Disposition: attachment` and `nosniff`, so
  they are never rendered from the app origin (amended by 20261118-1530,
  CHK020). CSP is not changed.
- **Limits**: one size limit of 10 MB for all types (raised from 5 MB so PDFs
  fit). The 8000 px limit applies to images only.
- **Guidance**: the input gets `accept=".png,.jpg,.jpeg,.pdf"` and a help text
  under the input: "PNG, JPEG or PDF, max 10 MB, images max 8000×8000 px.
  Export Visio/draw.io/SVG diagrams as PNG or PDF first." Validation errors
  name the exact reason (type, size or dimensions).

## Consequences

### Positive
- ✅ The common failure causes are explained up front
- ✅ PDFs are supported without weakening the security headers

### Negative
- ❌ PDFs are not previewed inline
- ❌ Deleted versions cannot be recovered (only the audit entry remains)
