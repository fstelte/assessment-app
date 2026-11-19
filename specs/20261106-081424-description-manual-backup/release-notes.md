# Release notes: restoring encrypted manual backups (2026.11.2)

## What's new

- **Encrypted backups restore with a key that lost its padding.** A key from
  **Generate key** is often copied without its trailing `=`. Restore keys are
  now normalised, which repairs missing padding.
- **An invalid key gets a clear message.** Before this fix, partial restore
  said "This backup format does not support partial restore" and full restore
  returned an HTTP 500. Both now say that the key is invalid.
- **A wrong key no longer "succeeds".** Full restore used to send a
  still-encrypted `.enc` file to the restore worker and report success. A
  `.enc` file now always needs a key that decrypts it.

## Who can do what

Nothing changes. Restore is still for administrators.

## Behaviour changes to be aware of

- Restoring a `.enc` file without a working key now fails straight away with
  an error, instead of being queued.

## Upgrade

No database migration, settings or environment variables.

## Known limitations and follow-ups

- Failed restore attempts (invalid or wrong key) are not audit-logged yet.
- An invalid configured `BACKUP_ENCRYPTION_KEY` is only detected when you
  restore, not on the backup page.
- The encryption is detected from the `.enc` file name. A renamed encrypted
  file without `.enc` is treated as unencrypted and fails later.
