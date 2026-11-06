---
type: decision
id: 20261106-0831-restore-no-plaintext-fallback-for-enc
date: 2026-11-06
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/admin/backup_crypto.py
  - scaffold/apps/admin/backup_utils.py
  - scaffold/apps/admin/routes.py
tags: [admin, backup, restore, encryption, bugfix]
participants: [Ferry Stelte, Claude]
---

# Remove the "return as-is" fallback when decrypting .enc backups

## Context

`try_decrypt(data, keys)` treats a `None` entry in `keys` as "return the data
unchanged". Both restore paths add `None` at the end of their key list:

- `build_inspection` uses `[key, None]`.
- The full-restore route uses `[provided, configured, None]`, or `[None]`
  when there are no keys.

When a `.enc` file is restored with a valid but wrong key, the result is:

- **Full restore** writes the still-encrypted bytes to `RESTORE_WATCH_DIR` as
  `….sql.gz` and reports "queued". The restore worker fails on that file
  later, and the UI never shows it.
- **Partial restore** fails while decompressing and shows the generic
  "inspect failed" message instead of "decryption failed".

## Decision

- `try_decrypt` no longer accepts `None` as a key. When no key works, it
  raises `InvalidToken`, or `InvalidBackupKey` (see
  [[20261106-0830-restore-normalize-and-validate-backup-key]]).
- Callers pass only real keys. `try_decrypt` is called only for `.enc`
  files, and unencrypted files never go through it.
- A `.enc` upload with no key available fails with the existing
  `decrypt_failed` message.

## Alternatives considered

- **Keep the fallback and fix only the invalid-key crash.** Rejected: a wrong
  key would still queue a file the restore worker can't use, and the admin
  wouldn't be told.

## Consequences

- An encrypted file is never passed on as if it were plaintext.
- A wrong key gets the "Decryption failed, verify the key" message at upload
  time, in both flows.
- The same rule covers the cache step in `partial_restore_inspect`. Its
  `except (InvalidToken, Exception): bytes_to_cache = file_bytes` fallback is
  removed, and a failure there caches nothing.
