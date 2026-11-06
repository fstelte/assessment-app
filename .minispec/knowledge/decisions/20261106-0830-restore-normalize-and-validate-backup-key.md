---
type: decision
id: 20261106-0830-restore-normalize-and-validate-backup-key
date: 2026-11-06
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/admin/backup_crypto.py
  - scaffold/apps/admin/backup_utils.py
  - scaffold/apps/admin/routes.py
  - scaffold/translations/en.json
  - scaffold/translations/nl.json
tags: [admin, backup, restore, encryption, bugfix]
participants: [Ferry Stelte, Claude]
---

# Normalize restore keys and report invalid keys clearly

## Context

An admin made a manual backup with a key generated in the browser
(`pg_dump-manual-20261106T070556Z.sql.gz.enc`). Restoring it failed in both
flows:

- **Partial restore** said "This backup format does not support partial
  restore", even though the file name is a supported format.
- **Full restore** returned HTTP 500.

There's one cause. `Fernet(key)` raises `ValueError`, not `InvalidToken`,
when the key isn't valid 32-byte url-safe base64. A typical trigger is a
copy-paste that drops the trailing `=`. The "Generate key" button always
produces a key that ends in `=`, and a double-click selection stops at that
character.

- In partial restore, the `ValueError` escapes `build_inspection`. The route's
  `except ValueError` treats it as "format not eligible".
- In full restore, the route catches only `InvalidToken`, so the request
  fails with a 500.

## Decision

1. Before each restore key is used, `backup_crypto` normalizes it:
   - remove all whitespace (including inside the key) and one matching pair
     of surrounding quotes
   - pad it with `=` to a multiple of 4
2. A key that still isn't valid Fernet after normalizing is skipped, not
   raised.
3. If no key decrypts the file and at least one key was invalid, `try_decrypt`
   raises a new `InvalidBackupKey` exception. This is not a `ValueError`
   subclass, so the route's "not eligible" branch can't catch it.
4. Both restore routes catch `InvalidBackupKey` and show a new message: "The
   encryption key is not a valid backup key". Each route has its own
   translation key, in `en` and `nl`.

## Alternatives considered

- **Clear error only, no padding repair.** This is simpler, but the admin has
  to work out on their own that a `=` is missing. That is exactly the slip
  that caused this incident. Rejected.

## Consequences

- A key that is missing its padding now works without any error.
- The 500 and the misleading "format" message are both gone.
- Normalizing affects restore only. Backup creation keeps rejecting invalid
  keys through its existing error message.
- Both restore flows try keys in the same order: the typed key, then the
  configured key. An invalid typed key doesn't block a configured key that
  works.
- No key, in any form, may appear in exception messages, flash messages,
  logs or audit details.
