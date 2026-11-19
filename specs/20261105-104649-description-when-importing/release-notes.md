# Release notes: PostgreSQL partial restore reads COPY data (2026.11.2)

## What's new

- **Partial restore of PostgreSQL backups restores data again.** Before this
  fix, every selected table reported "No INSERT statements found for this
  table." and the restore ended as **partial** with nothing restored. Both the
  manual backup and the scheduled backup (`docker/backup-db.sh`) write table
  data as `COPY … FROM stdin` blocks. The restore step only understood
  `INSERT` statements.
- The restore now reads the `COPY` blocks and loads each table through a
  temporary table with psycopg 3's copy API.
- **One failing table no longer stops the others.** Each table is restored in
  its own savepoint.
- **Sequences are moved forward** after a table restores rows, so new records
  don't collide with restored ids.
- The old `INSERT` parser is removed. This also fixes a bug where a `;` inside
  a quoted value cut a statement short.

## Who can do what

Nothing changes. Partial restore is still for administrators.

## Behaviour changes to be aware of

- Hand-made dumps that contain only `INSERT` statements are no longer
  restored by partial restore. Backups made by the app are not affected.

## Upgrade

No database migration, settings or environment variables.

## Known limitations and follow-ups

- Per-table result messages are not translated.
- The SQLite partial restore is unchanged.
