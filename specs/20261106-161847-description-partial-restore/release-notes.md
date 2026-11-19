# Release notes: partial restore handles missing foreign-key parents (2026.11.3)

## What's new

- **Partial restore no longer fails on missing users.** The default selection
  leaves out the identity tables (`users`, `roles`, …), but many tables point
  to a user (author, owner, creator). One backup row that pointed to a user
  missing from the live database made the whole table fail with
  `ForeignKeyViolation`, and every table depending on it failed too. About 25
  tables were affected.
- Each table's data is now cleaned before it is inserted:
  - A **nullable** reference to a table that is not part of this restore, with
    no matching live row, is set to empty. This follows the `SET NULL` rule
    the models already use.
  - Any **other** row whose parent is missing is skipped.
- **Counts per table.** The results page and the audit event show how many
  references were cleared and how many rows were skipped for a missing parent.

## Who can do what

Nothing changes. Partial restore is still for administrators.

## Behaviour changes to be aware of

- Restored records can have an empty author or owner when that user doesn't
  exist in the live database. Check the "cleared" counts on the results page.
- The "Partial Restore" section of `docs/deployment.md` describes the new
  behaviour.

## Upgrade

No database migration, settings or environment variables.

## Known limitations and follow-ups

- If two selected tables point to each other (a cycle), the table restored
  first can't see its parent yet, so those rows are skipped. The current
  models have no cycles.
- Composite foreign keys with one empty column are not checked.
