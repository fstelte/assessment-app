---
feature: 20261119-182410-ssp-architecture-overview-multiple-files
status: implemented
created: 2026-11-19
chunk_size: adaptive
total_tasks: 6
estimated_lines: 420
---

# SSP Architecture Overview: Multiple Files Tasks

## Overview

This turns the SSP architecture overview from one versioned slot into a flat
list of files that are all shown together, with multi-select upload
(all or nothing, up to 100 MB per batch) and per-file delete. Restore,
history and `version_number` are removed. The upgrade migration keeps only
the current version per SSP. Decisions: 20261119-1825, 1826, 1827 and 1828,
and 20261120-0900 (checklist gap resolutions).

The tasks are ordered so the test suite stays green after each one. Versioning
is removed first. The column is dropped while "current = newest" still holds.
The display then switches to a list, and only after that does upload accept
several files.

## Task List

### Foundation

#### Task 1: Remove restore and history
- **Estimate:** ~150 lines touched (about −130 / +20, mostly deletions)
- **Files:** `scaffold/apps/ssp/routes.py`,
  `scaffold/apps/ssp/templates/ssp/view.html`,
  `scaffold/translations/en.json`, `scaffold/translations/nl.json`,
  `tests/test_ssp_architecture_overview.py`
- **Description:**
  - Delete the `restore_architecture_overview` route and its
    `ssp_architecture_overview_restored` audit event.
  - Remove the history `<details>` block (restore and delete buttons per entry)
    from `view.html`.
  - Remove the translation keys `ssp.architecture_overview.history.*` and
    `delete.history` in both languages.
  - Tests: delete `test_restore_creates_new_version_without_mutating_old`.
    Rename `test_second_upload_keeps_first_in_history` and make it assert that
    two rows exist. Drop the restore half of
    `test_upload_and_restore_write_audit_log_rows`.
- **Depends on:** None
- **Acceptance:** No route, template or test references restore or history.
  The current file still shows and can be deleted.
- **Evidence:** `pytest tests/test_ssp_architecture_overview.py` passes.
  `grep -rn "restore_architecture_overview\|architecture_overview.history" scaffold tests`
  finds nothing.

#### Task 2: Migration: prune history, drop `version_number`
- **Estimate:** ~130 lines
- **Files:** `migrations/versions/20261119_0001_architecture_overview_flat_list.py` (new),
  `scaffold/apps/ssp/models.py`, `scaffold/apps/ssp/routes.py`,
  `scaffold/apps/ssp/templates/ssp/view.html`,
  `scaffold/translations/en.json`, `scaffold/translations/nl.json`,
  `tests/test_ssp_architecture_overview.py`,
  `tests/test_ssp_architecture_overview_migration.py` (new)
- **Description:**
  - Migration (`down_revision = "20261118_0003"`, the only head as of 2026-11-20; re-check if `main` moves):
    - Upgrade deletes every row below the per-SSP max `version_number` and
      logs `pruned N historical architecture overview versions across M SSPs`
      through `logging.getLogger("alembic.runtime.migration")`. It then drops
      `uq_ssp_architecture_overview_version` and `version_number` inside
      `batch_alter_table`.
    - Downgrade re-adds the column as nullable and numbers **every** row 1..n
      per `ssp_id` by `uploaded_at, id`, in Python so it works on SQLite and
      Postgres. It then sets the column to NOT NULL and re-creates the
      constraint.
  - Model:
    - Drop the column and the constraint, and update the docstring.
    - Order the relationship by `uploaded_at.desc(), id.desc()` **for now**
      (interim, design §Model).
  - Routes:
    - Remove `_next_architecture_overview_version`. Upload no longer sets
      `version_number`.
    - Audit details are `{ssp_id, original_filename}` for both upload and
      delete.
  - Template and i18n: the delete confirm uses `filename` (new
    `delete.confirm` wording from design §i18n).
  - Tests:
    - Remove the `version_number` assertions from the existing tests.
    - Write the new migration test in the style of
      `test_ssp_usability_migration.py` (`_PRE_SCHEMA`, `_run`), with fixture
      **SSP A versions 1, 2, 3; SSP B version 1; SSP C none**. It covers:
      - after upgrade, only A:3 and B:1 remain, with no rows for C;
      - the column and the constraint are gone;
      - the log line says `pruned 2 … across 1 SSPs`;
      - after downgrade, A's row and B's row are both `version_number = 1`;
      - with two rows added post-upgrade for B, downgrade numbers them 1 and 2
        by `uploaded_at`.
- **Depends on:** Task 1
- **Acceptance:** The model and DB have no `version_number`. Upgrading keeps
  exactly one row per SSP, the newest.
- **Evidence:** both test files pass. `alembic upgrade head` followed by
  `alembic downgrade -1` runs cleanly on a dev DB.

### Core Implementation

#### Task 3: Stacked file list display
- **Estimate:** ~90 lines
- **Files:** `scaffold/apps/ssp/models.py`,
  `scaffold/apps/ssp/templates/ssp/view.html`,
  `scaffold/translations/en.json`, `scaffold/translations/nl.json`,
  `tests/test_ssp_architecture_overview.py`
- **Description:**
  - Switch the relationship order to `uploaded_at.asc(), id.asc()`.
  - Replace the `current_overview` block with a loop over all files. Each file
    gets a header row (`flex items-center gap-3`): the filename (`min-w-0
    truncate`), then size, uploader and date, then a `shrink-0` delete form
    whose confirm names the file. Below it: either
    `<img loading="lazy" decoding="async" alt="image_alt(filename)">` or the
    existing PDF download card.
  - Keep the empty state and the upload form.
  - Replace the keys `current_alt` and `delete.current` with `image_alt` and
    `delete.button`.
- **Depends on:** Task 2
- **Acceptance:** with 2 uploaded files, both are on the page, oldest first,
  each with its own delete button. Deleting one leaves the other.
- **Evidence:**
  - New tests pass: `test_all_files_are_shown_oldest_first`,
    `test_delete_one_file_keeps_the_others` (replacing
    `test_delete_current_version_makes_previous_current`) and
    `test_overview_images_are_lazy_loaded`.
  - The full SSP test module passes.
  - Manual browser check of these scenarios: one image; one PDF; mixed image
    and PDF; a 40-character filename at 375 px width; light and dark theme.

#### Task 4: Multi-file upload, all or nothing
- **Estimate:** ~120 lines
- **Files:** `scaffold/apps/ssp/forms.py`, `scaffold/apps/ssp/routes.py`,
  `scaffold/apps/ssp/templates/ssp/view.html`,
  `scaffold/translations/en.json`, `scaffold/translations/nl.json`,
  `tests/test_ssp_architecture_overview.py`
- **Description:**
  - Form:
    - Rename `image` to `files`, a `MultipleFileField`.
    - Skip only parts where `filename == ""`. If none are left, raise the
      `required` error.
    - Refactor the per-file checks (extension, the `FileSize` equivalent,
      `_validate_architecture_overview_file`) into a helper that takes one
      `FileStorage`.
    - Collect errors as `upload.errors.file_prefix` using the **raw** browser
      filename, shortened to 100 characters.
  - Route:
    - On any error, flash all of them and save nothing.
    - Otherwise, in `getlist` order and per file: `seek(0)`, detect the MIME
      type, read the bytes and add a row. Flush, write one
      `ssp_architecture_overview_uploaded` event per row, and commit once.
    - Flash `upload.flash(count)` via `_()`. This replaces the hard-coded
      English string.
  - Every place that uses the field name, `form.image` → `form.files`:
    the template input and `hidden_tag` block, the `aria-describedby` /
    help `<p>`, the error loop `architecture_overview_form.image.errors`, the
    route's `form.image.data`, and the test helper `_upload`
    (`data={"image": ...}`).
  - Template: add `multiple` to the input and use the plural label.
  - i18n: update the `upload.help` text (design §i18n).
  - Tests: change `_upload` to accept a list of `(filename, bytes)`. Add:
    - 3 valid files → 3 rows in submission order and 3 audit events;
    - 2 valid files + 1 `.svg` → 0 rows, with the error naming `"….svg: "`;
    - PNG + PDF together → both stored with the detected MIME type;
    - empty submit → `required`;
    - a named zero-byte `.png` → `invalid_image`.

    Update the existing error-message tests for the filename prefix.
- **Depends on:** Task 3
- **Acceptance:** several files can be uploaded in one submit, and any
  invalid file blocks the whole batch with a named error.
- **Evidence:** the SSP test module passes, including the 5 new tests.
  Manual check: pick 3 files in the browser and see 3 files on the page, in
  the order selected.

#### Task 5: Request size: gateway 100m and browser check
- **Estimate:** ~60 lines
- **Files:** `docker/nginx/nginx.conf`,
  `docker/nginx/nginx.conf.example.public.md`,
  `docker/nginx/nginx.conf.example.behind-proxy.md`,
  `scaffold/static/js/ui.js`, `scaffold/apps/ssp/templates/ssp/view.html`,
  `scaffold/translations/en.json`, `scaffold/translations/nl.json`,
  `docs/deployment.md`, `tests/test_ssp_architecture_overview.py`
- **Description:**
  - nginx: change `client_max_body_size` from `12m` to `100m` in all three
    files.
  - `ui.js`: on `submit` of `form[data-max-total-bytes]`, add up
    `input[type=file].files[*].size`. If the total is over the limit,
    `preventDefault()` and put the `data-max-total-message` text
    (`textContent`) into the form's error slot. Otherwise disable the submit
    buttons.
  - Template: add `data-max-total-bytes="100000000"` and
    `data-max-total-message="{{ _('…upload.errors.total_too_large') }}"` on
    the upload form, plus an empty error slot.
  - `docs/deployment.md`: update the "Upload size limit" paragraph (12m →
    100m, the reason, upstream load balancer ≥100 MB, redeploy `gateway`) and
    the troubleshooting line at about line 129.
  - Test: the view renders the form with `data-max-total-bytes="100000000"`.
- **Depends on:** Task 4
- **Acceptance:** a selection over 100 MB in total is blocked in the browser
  with the translated message, and a valid submit disables the button.
- **Evidence:**
  - The SSP test module passes.
  - `grep -rn "client_max_body_size" docker` shows only `100m`.
  - Manual browser check: a selection over 100 MB shows the message and is
    not sent. A normal selection submits once, even with a double-click.

### Integration & Polish

#### Task 6: Docs and release notes [P]
- **Estimate:** ~50 lines
- **Parallel:** can run alongside Tasks 3–5 (docs only)
- **Files:** `docs/ssp.md`, `docs/models.md`, `docs/history.md`
- **Description:**
  - `docs/ssp.md`: describe the overview as a list of files (types, limits,
    multi-select, 100 MB per batch, all-or-nothing, per-file delete, no
    history). Update the gateway note at about line 76.
  - `docs/models.md`: the model has no `version_number`.
  - Release-notes entry in `docs/history.md`, which must include:
    - an **upgrade warning** that the migration permanently deletes historical
      architecture-overview versions, keeping only the current one per SSP,
      so **take a backup first** if the history matters;
    - the gateway limit raised to 100m, so custom gateways and upstream load
      balancers need the same;
    - the audit `details` no longer carry `version_number`;
    - partial restore of this table from a pre-upgrade backup is not
      supported.
- **Depends on:** Task 2
- **Acceptance:** no doc mentions versions, history or restore for the
  architecture overview, and the release notes cover all four points.
- **Evidence:**
  - `grep -n -i "restore\|version" docs/ssp.md` shows no architecture-overview
    hits.
  - The `docs/history.md` entry contains the four points.

## Notes

- **Sequencing:** the temporary `desc` order in Task 2 is intentional. It keeps
  the single-image template correct until Task 3 replaces it.
- **Stream handling:** `detect_architecture_overview_mime` reads the header
  bytes. Always `seek(0)` per file before `read()`.
- **Naming:** keep `architecture_overview_versions` and
  `ssp_architecture_overview_versions` (20261120-0900, CHK010).
- **Accepted risks:** `MAX_CONTENT_LENGTH` stays unset. Werkzeug
  `max_form_parts = 1000` is accepted. Up to about 100 MB per batch is held
  in memory.
- **Migration logging (found in Task 2, accepted):** under `flask db upgrade`,
  `migrations/env.py` looks for `migrations/alembic.ini`, which doesn't exist,
  so no logging is configured and the `pruned …` line (CHK001) is not shown.
  This predates the feature. The release notes in Task 6 carry the data-loss
  warning instead.
- **The migration chain doesn't run on SQLite (found in Task 2, predates
  this feature):** `20251115_0006` alters constraints without batch mode.
  Task 2 was verified on Postgres 16.
- **Deferred:** captions, reordering, in-place replace, thumbnails, count
  limits, and partial-restore compatibility for pre-upgrade backups.

## Progress
- [x] Task 1: Remove restore and history
- [x] Task 2: Migration: prune history, drop `version_number`
- [x] Task 3: Stacked file list display (manual browser check: approved by engineer at commit)
- [x] Task 4: Multi-file upload, all or nothing (manual browser check: approved by engineer at commit)
- [x] Task 5: Request size: gateway 100m and browser check (manual browser check: approved by engineer at commit)
- [x] Task 6: Docs and release notes
