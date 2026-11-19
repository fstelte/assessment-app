# Release notes: principles in the admin menu, no length cap (2026.11.4)

## What's new

- **Principles are easy to find.** Architecture principles
  (`/admin/principles`), which ADRs are anchored to, are now linked from the
  admin button row on the Users page and from the top navigation for admins.
- **Long principle descriptions can be saved.** The principle form no longer
  caps the description at 5000 characters. Principles imported with longer
  descriptions can now be edited and saved.
- The only remaining limit is Flask's `MAX_FORM_MEMORY_SIZE` of 500,000 bytes
  per form field. The importer uses the same limit, so every principle that
  can be imported can also be saved through the form.

## Who can do what

Nothing changes. Managing principles is still for administrators.

## Behaviour changes to be aware of

- The principle importer refuses descriptions over 500,000 bytes.

## Upgrade

No database migration, settings or environment variables.

## Known limitations and follow-ups

None.
