---
feature: 20261119-182410-ssp-architecture-overview-multiple-files
status: implemented
created: 2026-11-19
decisions:
  - 20261119-1825-architecture-overview-flat-file-list
  - 20261119-1826-architecture-overview-migration-keep-current
  - 20261119-1827-architecture-overview-batch-upload-all-or-nothing
  - 20261119-1828-architecture-overview-stacked-display
  - 20261120-0900-architecture-overview-multi-file-checklist-gap-resolutions
---

# SSP Architecture Overview: Multiple Files

## Overview

The architecture overview on the SSP view page changes from one versioned slot
(where only the highest version is shown) to a **flat list of files that are all
shown together**. Users can select several PNG, JPEG or PDF files in one upload
and delete any file on its own. Version numbers, history and restore are
removed. An upgrade migration keeps only the current version of each SSP, so
nothing changes visually right after deployment.

**Kept unchanged from `20261118-1505` / `20261118-1530`** (CHK015):
- the PNG, JPEG and PDF file types;
- MIME type detected from magic bytes, not taken from the browser;
- 10 MB per file, and 8000 px for images;
- PDFs streamed as `attachment` with `nosniff`, and the CSP unchanged;
- the `accept` attribute and the help text (extended to say several files can
  be selected);
- `_safe_upload_filename` for stored names;
- delete with a confirm prompt and the `ssp_architecture_overview_deleted` audit event.

**Replaced**: one current version plus history, restore, `version_number`,
and the 12 MB gateway limit (now 100 MB, decision 20261120-0900).

## User Stories

- As an SSP author, I want to upload several architecture diagrams (context,
  network, data flow) so that the SSP shows the whole architecture, not just one
  picture.
- As an SSP author, I want to select several files at once so that I don't have
  to upload them one by one.
- As an SSP author, I want to delete one wrong diagram without affecting the
  others.
- As a reviewer, I want to see all diagrams on the SSP page, readable at full
  width.

## Components

### Model: `scaffold/apps/ssp/models.py`, `SSPArchitectureOverview`
- Drop `version_number` and `uq_ssp_architecture_overview_version`.
- Docstring: "An uploaded architecture overview file for an SSP".
- `SSPlan.architecture_overview_versions` relationship: order by
  `SSPArchitectureOverview.uploaded_at.asc(), SSPArchitectureOverview.id.asc()`.
  Within one batch, `id` keeps the browser's submission order (CHK003).
  **Interim (Tasks 2→3 only):** order by `uploaded_at.desc(), id.desc()`, so
  the single-file template's `[0]` stays the newest file until the list
  display lands (CHK012).
- Names stay `architecture_overview_versions` /
  `ssp_architecture_overview_versions`. There is no rename (CHK010).

### Migration: `migrations/versions/20261119_0001_architecture_overview_flat_list.py`
1. Delete rows whose `version_number` is lower than the max for their
   `ssp_id`. Log `pruned N historical architecture overview versions across M
   SSPs` through the Alembic logger. No audit rows are written (CHK001).
2. In `batch_alter_table`: drop the unique constraint, then the column.
3. Downgrade: re-add `version_number` as nullable, number **every** row
   1..n per `ssp_id` by `uploaded_at, id` (computed in Python so it works on
   SQLite and Postgres), set it to NOT NULL and re-create the constraint. The
   newest row becomes current again. Pruned history is not restored (CHK011).

### Request size: gateway and browser check
- `docker/nginx/nginx.conf` and both `nginx.conf.example.*.md`: change
  `client_max_body_size` from `12m` to `100m` (CHK007).
- `scaffold/static/js/ui.js`: a handler for `form[data-max-total-bytes]`. On
  submit, it adds up the `size` of every selected file. If the total is over
  the limit, it blocks the submit and shows the text of
  `data-max-total-message` in the form's error slot. Otherwise it disables
  the submit button to prevent a double submit (CHK020).
- Flask `MAX_CONTENT_LENGTH` stays unset. Werkzeug's `max_form_parts = 1000`
  is accepted as is.

### Form: `scaffold/apps/ssp/forms.py`, `SSPArchitectureOverviewUploadForm`
- `image` becomes a `MultipleFileField` (rename it to `files`). `FileRequired`,
  `FileAllowed` and `FileSize` don't apply to a list as-is, so a field-level
  validator loops over the files. Per file, it checks the extension, size and
  `_validate_architecture_overview_file` logic, and collects errors as
  `"<filename>: <reason>"`. Here `<filename>` is the **raw browser filename**,
  shortened to 100 characters and autoescaped when flashed (CHK004). The
  validation logic is refactored into a helper that takes one
  `FileStorage`.
- Only parts with `filename == ""` are skipped as empty. If none are left,
  the existing `required` error is raised. A named zero-byte file is validated
  normally and fails (CHK009).

### Routes: `scaffold/apps/ssp/routes.py`
- `upload_architecture_overview`: validate; on any error, flash every message
  and save nothing. Otherwise create one row per file in
  `request.files.getlist` order, flush, write one
  `ssp_architecture_overview_uploaded` event per row (details: `ssp_id`,
  `original_filename`), then commit once. An exception before the commit
  persists nothing, because the session is rolled back at teardown (CHK008).
  Flash a success message with only the count (CHK006).
- `delete_architecture_overview`: unchanged apart from the audit details
  (drop `version_number`).
- `architecture_overview_image`: unchanged.
- `restore_architecture_overview` and `_next_architecture_overview_version`:
  **removed**.

### Template: `scaffold/apps/ssp/templates/ssp/view.html` (lines ~172–240)
- Loop over `ssp.architecture_overview_versions`. Each file starts with a
  header row (`flex items-center gap-3`): the filename block (`min-w-0
  truncate`), then size, uploader and date, then a `shrink-0` delete form
  whose confirm prompt names the filename (CHK021). Below it is either the
  inline `<img loading="lazy" decoding="async">` (CHK018) or the existing PDF
  download card.
- Keep the empty state and the upload form. The input gets `multiple`, and
  the form gets `data-max-total-bytes="100000000"` and
  `data-max-total-message`.
- Remove the history `<details>` block and the restore and delete-current
  buttons.

## Data Model

`ssp_architecture_overview_versions` (table name kept):
`id, ssp_id (FK, CASCADE), image_data (blob), mime_type, original_filename,
file_size_bytes, uploaded_by_id (FK, SET NULL), uploaded_at`. All rows for an
SSP are shown.

## API/Interface

| Method | Path | Change |
|---|---|---|
| POST | `/ssp/<id>/architecture-overview` | accepts 1..n files in field `files`; all or nothing |
| GET | `/ssp/<id>/architecture-overview/<file_id>/image` | unchanged |
| POST | `/ssp/<id>/architecture-overview/<file_id>/delete` | unchanged (audit details lose `version_number`) |
| POST | `/ssp/<id>/architecture-overview/<file_id>/restore` | **removed** |

## Edge Cases

- **One invalid file in a batch**: nothing is saved. Every error is flashed
  with its filename, and the user re-submits.
- **Same filename uploaded twice**: allowed. Both rows are shown, and the
  uploaded date tells them apart.
- **Empty multipart part** (browser sends `filename=""` when nothing is picked):
  filtered out before validation, and an empty result gives the `required`
  error.
- **Large batch**: over 100 MB in total, the browser check blocks it first,
  and the gateway would answer 413 anyway. There's no count limit, and
  Werkzeug's `max_form_parts` is accepted (CHK007). Up to about 100 MB is
  held in memory before the commit, which is accepted (CHK019).
- **Double submit**: the browser check disables the button after a valid
  submit. Duplicate filenames stay allowed (CHK020).
- **Partial restore of an older backup**: restoring this table from a
  backup made before the upgrade fails for that table, because the backup
  still has the `version_number` column. Other tables still restore. This is
  documented and `backup_utils` is not changed (CHK022).
- **Other consumers**: there are no exports, reports or API that read
  `version_number` or the relationship (grep of `scaffold/`, CHK022).
- **Permissions**: any logged-in user can still upload and delete, as today
  (CHK023).
- **Stream position**: the MIME check reads the header bytes, so seek back to
  0 per file before `read()`. The existing code relies on this.

## i18n

`en.json` / `nl.json`:
- Remove `ssp.architecture_overview.history.*` (heading, entry, restore),
  `delete.current`, `delete.history` and `current_alt`.
- Add or change (CHK005), all under `ssp.architecture_overview.`:

| Key | EN | NL |
|---|---|---|
| `upload.field.label` | Architecture overview files | Bestanden architectuuroverzicht |
| `upload.help` | PNG, JPEG or PDF, max 10 MB per file, images max 8000×8000 px. You can select several files (max 100 MB in total). Export Visio/draw.io/SVG diagrams as PNG or PDF first. | PNG, JPEG of PDF, max. 10 MB per bestand, afbeeldingen max. 8000×8000 px. Je kunt meerdere bestanden selecteren (max. 100 MB samen). Exporteer Visio-/draw.io-/SVG-diagrammen eerst als PNG of PDF. |
| `upload.flash` | {count} file(s) uploaded. | {count} bestand(en) geüpload. |
| `upload.errors.file_prefix` | {filename}: {error} | {filename}: {error} |
| `upload.errors.total_too_large` | The selected files are larger than 100 MB in total. Upload them in smaller batches. | De geselecteerde bestanden zijn samen groter dan 100 MB. Upload ze in kleinere delen. |
| `delete.button` | Delete | Verwijderen |
| `delete.confirm` | Delete "{filename}"? This cannot be undone. | "{filename}" verwijderen? Dit kan niet ongedaan worden gemaakt. |
| `image_alt` | Architecture overview: {filename} | Architectuuroverzicht: {filename} |

- Move the hard-coded `"Architecture overview uploaded."` flash to `_()`.

## Constitution Compliance

- **Module ownership:** all changes stay in the `ssp` blueprint and its
  migration.
- **Security, roles and audit:** no permission changes. Upload and delete keep
  writing audit events, one per file. PDFs are still served as attachments
  with `nosniff`, and the CSP is unchanged. The filename is still sanitised
  with `_safe_upload_filename`.
- **Test and migration discipline:** update
  `tests/test_ssp_architecture_overview.py`. Remove the restore and versioning
  tests and add: multi-file upload, all-or-nothing rejection, per-file
  delete, display order, and a migration test (history pruned, current kept).
- **Localization:** all new copy uses `_()` in `en.json` and `nl.json`.
- **UI language:** the existing Tailwind/theme markup is reused per file.
- **Operational impact:** the migration **permanently deletes historical
  versions**. The release notes must say so and tell operators to back up
  first (CHK002). The gateway `client_max_body_size` goes from 12m to 100m,
  which must be noted in `docs/deployment.md` (including an upstream load
  balancer needing ≥100 MB) and in the release notes, as constitution §V
  requires. Update `docs/ssp.md` and `docs/models.md`. The audit `details`
  lose `version_number` (CHK013).
- **Simpler option rejected:** a batch upload that keeps "one current version"
  was rejected because it doesn't let several diagrams be shown together.

## Out of Scope

- Captions or titles per file (the filename is the label)
- Manual reordering
- Replacing a file in place
- Version history, restore or archived rows
- File-count limits (the only size limits are the per-file 10 MB and the 100 MB batch limit)
- Changing admin partial restore for pre-upgrade backups of this table
- Thumbnails, a grid or inline PDF preview

## Open Questions

None. The naming question was closed by decision 20261120-0900 (CHK010):
keep the legacy names.
