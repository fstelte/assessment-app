---
type: decision
id: 20261120-0900-architecture-overview-multi-file-checklist-gap-resolutions
date: 2026-11-20
status: accepted
supersedes: null
superseded_by: null
impacts:
  - migrations/versions/20261119_0001_architecture_overview_flat_list.py
  - scaffold/apps/ssp/forms.py
  - scaffold/apps/ssp/routes.py
  - scaffold/apps/ssp/templates/ssp/view.html
  - scaffold/static/js/ui.js
  - scaffold/translations/*
  - docker/nginx/nginx.conf
  - docker/nginx/nginx.conf.example.*.md
  - docs/deployment.md
  - docs/ssp.md
  - docs/history.md
tags: [ssp, architecture-overview, checklist, gap-resolution, nginx]
participants: [Ferry Stelte, Claude]
---

# Architecture overview multi-file: checklist gap resolutions

Resolves the items in
`specs/20261119-182410-ssp-architecture-overview-multiple-files/checklists/general.md`.
It amends decisions 20261119-1826, -1827 and -1828 where noted. The user made
the call marked **(user)**. The others follow the codebase's defaults and
conventions.

## Context

The general checklist found 23 gaps. While checking CHK007 we also found that
`docker/nginx/nginx.conf` sets `client_max_body_size 12m`, which was sized for
one 10 MB file (decision 20261118-1530, CHK008). Any multi-file batch over
about 12 MB in total would get a bare nginx 413 before the app sees it. That
makes "no count limit" (20261119-1827) a 12 MB per-batch cap in practice.

## Resolutions

- **CHK007 + nginx limit (user): raise the gateway limit to 100 MB and check in
  the browser.** Amends 20261119-1827.
  - Set `client_max_body_size 100m;` in `docker/nginx/nginx.conf` and in both
    `nginx.conf.example.*.md`.
  - Update `docs/deployment.md`: the 12 MB rationale becomes "10 MB per file,
    up to 100 MB per architecture-overview batch". An upstream load balancer
    needs at least 100 MB.
  - Add a small `ui.js` handler on forms with `data-max-total-bytes`. When the
    selected files add up to more than the limit, it blocks the submit and
    shows a translated message passed in through `data-max-total-message`.
  - The upload form sets the limit to 100 MB as 100000000 bytes (decimal).
    *Amended in Task 5:* not 104857600 (100 MiB), because nginx `100m`
    caps the whole body including multipart overhead. The decimal value
    leaves about 4.8 MB of headroom, so a selection at the limit never
    reaches nginx's bare 413.
  - Flask's `MAX_CONTENT_LENGTH` stays unset (backup restore must not be
    capped).
  - Werkzeug's default `max_form_parts = 1000` is accepted as a hard cap
    nobody will reach in practice. No custom 413 handler.
- **CHK001: migration audit.** The migration writes no audit rows, because
  writing to the audit table from a migration is fragile. It logs one line
  through Alembic's logger: `pruned N historical architecture overview
  versions across M SSPs`. The release notes state the data loss.
- **CHK002: backup before upgrade.** The `docs/history.md` entry and
  `docs/deployment.md` tell operators to take a backup (the existing admin
  backup) before upgrading if they need the history. There is no export tool.
- **CHK003: batch order.** Files are inserted in the order of
  `request.files.getlist("files")`, which is the browser's submission order.
  The display order is `uploaded_at asc, id asc`, so a batch keeps that order
  and older uploads come first.
- **CHK004: filename in errors.** Error messages show the **raw browser
  filename** (what the user recognises), shortened to 100 characters. It is
  safe because flash messages are autoescaped (`{{ message }}` in
  `base.html`). The stored name stays `_safe_upload_filename`.
- **CHK005: translation keys.** These are listed with their EN and NL wording
  in design.md §i18n.
- **CHK006: success flash.** It gives a count only: "{count} file(s)
  uploaded." / "{count} bestand(en) geüpload."
- **CHK008: server-side failure.** The route adds all rows, flushes, writes
  the audit events and commits once. Any exception before the commit means
  nothing is persisted (Flask-SQLAlchemy rolls the session back at teardown),
  and the user sees the standard error page.
- **CHK009: empty versus zero-byte.** Only a part with `filename == ""` counts
  as empty and is skipped. A named zero-byte file is validated normally and
  fails as `invalid_image` or `invalid_pdf` (or `invalid_type` because of its
  extension).
- **CHK010: naming.** Keep `architecture_overview_versions` and
  `ssp_architecture_overview_versions`. The open question is closed: renaming
  touches the relationship, the cascade, the migration and backup tables for
  no change in behaviour.
- **CHK011: downgrade.** Every row that exists at downgrade time survives.
  Rows are numbered 1..n per SSP by `uploaded_at, id`, so the newest becomes
  "current" again. Pruned history is not restored.
- **CHK012: interim order.** design.md now documents the temporary
  `desc` order between Task 2 and Task 3.
- **CHK013: audit shape.** Both upload and delete log
  `{ssp_id, original_filename}`. The removal of `version_number` from both
  events is noted in `docs/history.md`.
- **CHK014: field rename.** Task 4 lists every place that uses the field name
  (`form.image` → `form.files`): template input, `aria-describedby`, error
  loop, route, `_upload` test helper.
- **CHK015: carried-over rules.** design.md §Overview lists exactly what is
  kept from 20261118-1505 and -1530.
- **CHK016: migration fixture.** SSP A has versions 1, 2 and 3; SSP B has
  version 1; SSP C has none. After upgrade, A:3 and B:1 remain and C has none.
  After downgrade, A:3 → 1 and B:1 → 1.
- **CHK017: manual check.** Covered scenarios: one image, one PDF, mixed
  image and PDF, a 40-character filename at 375 px width, and light and dark
  theme. These are listed in Task 3.
- **CHK018: page weight.** Every overview `<img>` gets `loading="lazy"` and
  `decoding="async"`. Amends 20261119-1828.
- **CHK019: memory.** A batch is held in memory before the commit, at most
  about 100 MB because of the gateway limit. Accepted.
- **CHK020: double submit.** The same `ui.js` handler disables the submit
  button once a valid submit starts. Duplicate filenames stay allowed.
- **CHK021: mobile header row.** The header row uses `flex items-center gap-3`.
  The filename block is `min-w-0` with `truncate`, and the delete button is
  `shrink-0`. This follows the existing PDF card's markup. Amends
  20261119-1828.
- **CHK022: other consumers.** A grep of `scaffold/` finds no exports,
  reports or API that read `version_number` or the relationship, outside
  `ssp/models.py`, `routes.py` and `view.html`. Admin **partial restore**
  copies a backup table's columns as-is (`backup_utils.py`). Restoring this
  table from a backup made before the upgrade therefore fails for that table
  (it is reported as an error), and the other tables still restore. This is
  documented in `docs/deployment.md` and the release notes; `backup_utils` is
  not changed.
- **CHK023: permissions.** Any logged-in user can still upload and delete any
  file, as today. No role changes, so constitution §II needs no role or
  audit review beyond the existing per-file events.

## Consequences

### Positive
- ✅ Real multi-file batches up to 100 MB work through the bundled gateway
- ✅ Every checklist gap has a concrete, testable answer

### Negative
- ❌ Operators with their own gateway or load balancer must raise its limit to 100 MB
- ❌ Partial restore of this table from a pre-upgrade backup no longer works
