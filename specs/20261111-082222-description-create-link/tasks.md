---
feature: 20261111-082222-description-create-link
status: planned
created: 2026-11-11
chunk_size: adaptive
total_tasks: 1
estimated_lines: 85
---

# Principles in the Admin Menu, Editable Without a Length Cap — Tasks

## Overview

Implements [design.md](design.md): a "Principles" link in the Users page button
row and an admin-only "Principles" button in the top navigation, and the
5000-character description cap removed from the principle form. Per the
engineer's choice, this is one task.

## Task List

### Core Implementation

#### Task 1: Principles nav links and no description length cap
- **Estimate:** ~85 lines (about 30 implementation and docs, 55 tests)
- **Files:**
  - `scaffold/apps/admin/forms.py`: `PrincipleCreateForm.description`
    validators become `[DataRequired()]` (check whether the `Length` import is
    still used elsewhere in the file; it is, by `name` and other forms)
  - `scaffold/apps/admin/templates/admin/users.html`: add a button to
    `url_for('admin.principles')` after the sensitivity labels link, same
    classes as its neighbours, label `admin.users.link_principles`
  - `scaffold/templates/partials/navigation.html`: inside
    `{% if current_user.has_role('admin') %}`, add a button before "Admin" in
    the "Profile" button style, label `app.navigation.principles`
  - `scaffold/translations/en.json`, `scaffold/translations/nl.json`: add
    `admin.users.link_principles` and `app.navigation.principles`
    ("Principles" / "Principes"), placed next to the sibling keys
  - `scaffold/apps/ssp/principle_importer.py`: in
    `import_principles_from_mapping`, skip a row when
    `len(description.encode("utf-8")) > current_app.config["MAX_FORM_MEMORY_SIZE"]`
    (no check when that is `None`), with an error in `stats.errors`
  - `docs/architecture.md`: update the principles paragraph (line 60): admin
    menu and nav link for admins; no description cap beyond the 500 KB form
    field limit, which the importer also applies
  - `tests/test_admin_principles.py`: new tests (below)
- **Description:** add both menu links, remove the form's length cap, and give
  the importer the same 500 KB limit as the form.
- **Depends on:** None
- **Acceptance:**
  - `/admin/users` (as admin) contains a link to `/admin/principles`
  - Any page (as admin) shows the nav "Principles" button
  - A logged-in non-admin control owner does **not** see the nav button. The
    assertion looks for the nav button's label/markup, not just the
    `/admin/principles` URL, because the ADR empty state also links there.
  - Updating an existing principle with a 6000-character description
    redirects with the success flash and stores the full text
  - Creating a principle with a 6000-character description succeeds
  - Importing a file with one row over `MAX_FORM_MEMORY_SIZE` and one valid
    row: the valid row is created, the oversized row is not and shows up as an
    error (the test can set a small `MAX_FORM_MEMORY_SIZE` in the app config)
  - Both language files have both keys
  - `docs/architecture.md` describes the menu links and the limit
- **Evidence:**
  - `pytest tests/test_admin_principles.py` passes (new and existing tests)
  - `pytest tests/test_ssp_adr.py` still passes (the ADR page links to principles)
  - Template check: both new keys are present in `en.json` and `nl.json`
    (no missing-key fallback text on the page)
  - `graphify update .` run after the code changes

## Notes

- The nav button is deliberately **not** a `NavEntry`: those have no role filter
  ([[20261111-0827-principles-admin-navigation]]).
- The update form inherits the validator from `PrincipleCreateForm`, so one edit
  covers create and update ([[20261111-0828-principle-description-no-length-cap]]).
- The existing test helpers `_make_admin` and `_login` can be reused. A control
  owner user needs a `Role` with name `control_owner`.
- The importer uses `current_app`, so import it from `flask` in
  `principle_importer.py`. `import_principles_from_mapping` already runs inside
  a request.
- Deferred: a nav link for non-admin control owners; inline errors on the edit
  page; an active state for the nav button; other importer validation.

## Progress
- [x] Task 1: Principles nav links and no description length cap
  - Evidence (2026-11-11): `pytest tests/test_admin_principles.py tests/test_ssp_adr.py` → 17 passed.
    The `_login` helpers in both files were switched to direct session sign-in (password
    login now forces MFA; the old helper made 7 existing tests fail). 5 audit-trail tests
    in `test_admin_routes.py` fail with and without this change (audit retention worker
    + in-memory SQLite on Python 3.13); out of scope. `graphify update .` run.
