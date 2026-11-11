---
feature: 20261111-082222-description-create-link
status: planned
created: 2026-11-11
decisions:
  - 20261111-0827-principles-admin-navigation
  - 20261111-0828-principle-description-no-length-cap
---

# Principles in the Admin Menu, Editable Without a Length Cap

## Overview

Architecture principles (`/admin/principles`) are what ADRs are anchored to,
but no menu links to them. This feature adds a "Principles" link to the admin
button row on the Users page and to the top navigation for admins. It also
removes the 5000-character description cap from the principle form, so
principles imported with longer descriptions can be edited and saved. The only
remaining limit is Flask's `MAX_FORM_MEMORY_SIZE` of 500,000 bytes per form
field. The importer gets that same limit, so every principle that exists can
also be saved through the form.

## User Stories

- **P1:** As an admin, I want a "Principles" link in the admin menu, so that I
  can manage ADR principles without knowing the URL.
- **P1:** As an admin or control owner, I want to save any existing principle,
  including imported ones with long descriptions, so that every principle is
  editable. Form and import both apply the same limit of 500 KB per
  description, so no principle can exist that the form can't save.
- **P2:** As an admin, I want a "Principles" button in the top navigation, so
  that I can reach the page from anywhere in one click.

## Components

### Admin button row (`scaffold/apps/admin/templates/admin/users.html`)
Add an `<a>` with the same classes as the neighbouring links, pointing to
`url_for('admin.principles')` and labelled with `admin.users.link_principles`.
Put it after the sensitivity labels link, before the audit trail.

### Top navigation (`scaffold/templates/partials/navigation.html`)
Inside the existing `{% if current_user.has_role('admin') %}` block, add a
button before the "Admin" button, in the neutral "Profile" style, pointing to
`url_for('admin.principles')` and labelled with `app.navigation.principles`.
Admins only. It is **not** a `NavEntry` (those have no role filtering).

### Principle form (`scaffold/apps/admin/forms.py`)
`PrincipleCreateForm.description`: change
`validators=[DataRequired(), Length(max=5000)]` to `[DataRequired()]`.
`PrincipleUpdateForm` inherits this. The name keeps `Length(max=255)`.

### Principle importer (`scaffold/apps/ssp/principle_importer.py`)
In `import_principles_from_mapping`, skip rows whose description is over
500,000 bytes in UTF-8 and add a per-row error to `stats.errors`, as is already
done for empty fields. The limit is read from
`current_app.config["MAX_FORM_MEMORY_SIZE"]` (Flask default 500,000), so form
and import stay the same if the setting is ever changed. If the value is `None`
(no limit), the importer checks nothing either.

### Documentation (`docs/architecture.md`)
Update the principles paragraph (line 60): the page is in the admin menu and in
the top navigation for admins, and descriptions have no application-level cap
beyond the 500 KB form field limit, which the importer also applies.

### Translations (`scaffold/translations/en.json`, `nl.json`)
- `admin.users.link_principles`: en "Principles" / nl "Principes"
- `app.navigation.principles`: en "Principles" / nl "Principes"

## Data Model

No changes. `architecture_principles.description` is already `Text`.

## API/Interface

No new routes. The existing ones are used:
- `GET /admin/principles` (`admin.principles`): the link target.
- `GET /admin/principles/<id>/edit`, `POST /admin/principles/<id>/update`: now
  accept descriptions up to the 500 KB form field limit.
- `POST /admin/principles` (import): rejects rows whose description is over
  that same limit, with a per-row error.

## Testing

In `tests/test_admin_principles.py`:
- An admin sees a link to `/admin/principles` on `/admin/users` and the nav
  "Principles" button.
- A logged-in control owner does **not** see the nav button. The assertion
  looks for the nav button's label/markup, not just the URL, because the ADR
  empty state also links to `/admin/principles`.
- Updating a principle with a 6000-character description succeeds and stores
  it (regression test for the removed cap).
- Creating a principle with a 6000-character description succeeds.
- Importing a row with a description over `MAX_FORM_MEMORY_SIZE` skips that row
  with an error, and other rows in the same file are still imported.

## Constitution Check

- **Module ownership (I):** everything stays in the existing `admin` and `ssp`
  modules and the shared navigation partial. No new modules or shared code.
- **Security and audit impact (II):** no change to who can view or edit. The
  page keeps `_require_control_admin` and `require_fresh_login`, and the new
  links only reuse existing role checks (`has_role('admin')`, `_require_admin`
  on the Users page). Create, update and import already write an `AuditLog`
  row. The removed cap allows larger descriptions (up to 500 KB) from admins and
  control owners only, an accepted risk.
- **Validation scope (III):** new pytest cases in
  `tests/test_admin_principles.py`, and the existing principle and ADR tests
  (`tests/test_ssp_adr.py`) must still pass.
- **Localization impact (IV):** two new keys in `en.json` and `nl.json`. The
  buttons use the existing Tailwind classes of their neighbours.
- **Migration and operational impact (V):** no schema change, no migration, no
  new environment variables. `docs/architecture.md` is updated.

## Out of Scope

- A nav link for non-admin control owners (see decision B1; revisit on request).
- Showing validation errors inline on the edit page instead of redirecting with
  a flash message.
- Any other importer validation change beyond the description size limit.
- An active/highlighted state for the nav button ("Admin" has none either).

## Open Questions

- None.
