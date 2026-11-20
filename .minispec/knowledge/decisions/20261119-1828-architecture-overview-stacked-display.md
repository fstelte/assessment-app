---
type: decision
id: 20261119-1828-architecture-overview-stacked-display
date: 2026-11-19
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/ssp/templates/ssp/view.html
  - scaffold/translations/*
tags: [ssp, architecture-overview, ui]
participants: [Ferry Stelte, Claude]
---

# Architecture overview display: files stacked full width, filename as the label

Follows from `20261119-1825-architecture-overview-flat-file-list`.

## Context

The SSP view page shows one current image, or one PDF card. With several files,
we need a layout and a way to tell the files apart.

## Options Considered

### Layout
- **Stacked full width**: ✅ diagrams stay readable, close to today's markup; ❌ a long page with many files
- **Thumbnail grid**: ✅ compact; ❌ diagrams are unreadable at thumbnail size, and needs a click-through

### Label
- **Filename only**: ✅ no new field or route; ❌ depends on users naming files well
- **Optional caption**: ✅ clearer labels; ❌ adds a column, an edit form and a route

## Decision

- Files are stacked in `uploaded_at` order (oldest first). Each file has a header
  row with the filename, size, uploader, date and a delete button with a confirm
  prompt. Below the header, an image is shown inline at full width, and a PDF
  is shown as today's download card.
- The filename is the only label. There is no caption field.
- *Amended by 20261120-0900:* every `<img>` gets `loading="lazy"
  decoding="async"` (CHK018). The header row truncates long filenames and
  keeps the delete button `shrink-0` (CHK021).
- The empty state ("none uploaded") and the upload form below the list stay;
  the form now accepts several files.
- The "history" `<details>` block and the restore buttons are removed, along
  with their translation keys.

## Consequences

### Positive
- ✅ Minimal template change; reuses the existing PDF card and image markup per file
- ✅ No new schema for labels

### Negative
- ❌ The page gets long when an SSP has many large diagrams (no collapse or grid)
