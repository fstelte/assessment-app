# Release notes: multiple files in the SSP architecture overview

## What's new

- **Several architecture diagrams per SSP.** The architecture overview on the
  SSP page is now a list of files, shown oldest first. Each file shows its
  name, type, size, uploader and date. Images are shown on the page, and PDFs
  are shown with **Download PDF**.
- **Upload several files at once.** Select several PNG, JPEG or PDF files in
  one upload: up to 10 MB per file and 100 MB in total. A selection over
  100 MB is blocked in the browser with a message.
- **All or nothing.** If any selected file is refused, nothing is uploaded.
  Each message names the file and the reason, for example
  `network.svg: Only PNG, JPEG or PDF files can be uploaded…`.
- **Delete one file.** Every file has its own **Delete** button, and the
  other files stay.

## Removed

- **Version history and Restore are gone.** Files are no longer versions of
  one overview. To replace a diagram, delete it and upload the new one.

## Who can do what

Nothing changes. Any signed-in user can upload and delete architecture
overview files, as before.

## Upgrade

- **The migration permanently deletes architecture overview history.**
  Migration `20261119_0001` keeps only the current (newest) version of each
  SSP's architecture overview and deletes all older versions. This cannot be
  undone: a downgrade does not bring them back. **If you need that history,
  take a backup before upgrading** (**Admin → Backup & Restore**).
- **Gateway limit raised to 100 MB.** The bundled gateway now sets
  `client_max_body_size 100m;` (was `12m`). Redeploy it with
  `docker compose up -d gateway`. If you run your own gateway, or a load
  balancer or reverse proxy in front of it, raise its body-size limit to at
  least 100 MB. Otherwise larger batches fail with that proxy's bare `413`.
  See `docs/deployment.md`, "Upload size limit".
- **Audit events no longer carry `version_number`.** Both
  `ssp_architecture_overview_uploaded` and `ssp_architecture_overview_deleted`
  now log `{ssp_id, original_filename}`, one event per file. The
  `ssp_architecture_overview_restored` event is no longer written.
- **Partial restore of a pre-upgrade backup is not supported for this table.**
  A backup made before this release still has the `version_number` column.
  Restoring `ssp_architecture_overview_versions` from it with the admin
  partial restore fails for that table, and other tables still restore.
- New and changed translation keys under `ssp.architecture_overview.*` (en,
  nl). The `history.*`, `current_alt`, `delete.current`, `delete.history` and
  `pdf.meta` keys are removed.

## Known limitations and follow-ups

- Files have no caption; the filename is the label. They can't be reordered
  or replaced in place.
- The migration's "pruned N historical versions" log line is not shown when
  running `flask db upgrade`. `migrations/env.py` looks for a
  `migrations/alembic.ini` that doesn't exist, so migration logging is never
  configured. This predates this release.
- The full migration chain does not run on SQLite (`20251115_0006` alters
  constraints without batch mode). This predates this release. The new
  migration was verified on PostgreSQL 16.
