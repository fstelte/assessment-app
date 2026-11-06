---
feature: 20261106-081424-description-manual-backup
status: planned
created: 2026-11-06
decisions:
  - 20261106-0830-restore-normalize-and-validate-backup-key
  - 20261106-0831-restore-no-plaintext-fallback-for-enc
---

# Restoring Encrypted Manual Backups: Design

## Overview

An admin made a manual backup with a key from the "Generate key" button:
`pg_dump-manual-20261106T070556Z.sql.gz.enc`. Restoring it failed:

- **Partial restore** showed "This backup format does not support partial
  restore. Use full restore instead."
- **Full restore** returned HTTP 500.

**Root cause.** `Fernet(key)` raises `ValueError` when a key isn't valid
32-byte url-safe base64, for example when the trailing `=` was lost while
copying the key. Neither restore flow handles that exception:

- **Partial restore.** The `ValueError` escapes `build_inspection`
  (`backup_utils.py`). The route's `except ValueError` (`routes.py`,
  `partial_restore_inspect`) then reports it as "format not eligible".
- **Full restore.** `restore_backup` (`routes.py`) catches only
  `InvalidToken`, so the `ValueError` becomes a 500.

**A related bug.** `try_decrypt` treats a `None` key as "return the bytes
unchanged". When a key is valid but wrong, full restore queues the
still-encrypted file for the restore worker and reports success.

**The fix:**

- Normalize restore keys, which repairs missing padding.
- Report an invalid key with its own clear message.
- Remove the plaintext fallback for `.enc` files.

## User Stories

- As an admin, I want to restore an encrypted backup with the key I saved,
  even if I lost its trailing `=` while copying, so that a copy-paste slip
  doesn't block a restore.
- As an admin, I want a clear message when my key is invalid or wrong,
  instead of a 500 or a misleading message about the file format, so that I
  know what to fix.
- As an admin, I want a restore that can't decrypt the file to fail straight
  away, so that an unreadable file is never queued for restore.

### Acceptance scenarios

1. **Given** a `.sql.gz.enc` backup made with key K, **when** the admin uploads
   it for partial restore with K without its trailing `=`, **then** the
   inspection page lists the tables.
2. **Given** the same setup, **when** the admin uses full restore, **then** the
   decrypted `….sql.gz` is written to `RESTORE_WATCH_DIR` and the "queued"
   message is shown.
3. **Given** a key that isn't valid Fernet even after normalizing, such as
   `my-passphrase`, **when** the admin uses partial or full restore, **then**
   the response is not a 500. The flow's "invalid key" message is shown, and
   nothing is written or cached.
4. **Given** a valid key that didn't encrypt the file, **when** the admin uses
   partial or full restore, **then** the flow's `decrypt_failed` message is
   shown, and nothing is written to `RESTORE_WATCH_DIR`.
5. **Given** a `.enc` file uploaded with no key and no configured key,
   **when** the admin uses full restore, **then** `decrypt_failed` is shown,
   and nothing is written.
6. **Given** an unencrypted `.sql.gz` or `.db.gz` backup, **when** it is
   restored either way, **then** the behaviour is unchanged.
7. **Given** a key with surrounding spaces or quotes, **then** it is accepted
   the same as the bare key.
8. **Given** a full restore **or a partial restore** where the typed key is
   invalid but the configured key decrypts the file, **then** the restore
   succeeds. Invalid keys are skipped, not fatal, and both flows try keys in
   the same order: the typed key first, then the configured key.
9. **Given** a `.enc` file uploaded for partial restore with no key and no
   configured key, **then** `decrypt_failed` is shown, and nothing is cached.
10. **Given** any failed decryption, **then** neither the key nor any part of
    it appears in a flash message, an exception message, the application log
    or audit details.
11. **Given** a key pasted with line breaks or spaces inside it, **then** it is
    accepted the same as the bare key.
12. **Given** a key that was typed for an unencrypted backup (not `.enc`),
    **then** the key is ignored and the restore goes ahead as in scenario 6.

## Components

### `backup_crypto.py`

- **`normalize_key(key: str) -> str`** (new)
  - Removes all whitespace, including spaces and line breaks inside the key.
    A Fernet key never contains whitespace.
  - Removes one pair of matching surrounding `'` or `"`.
  - Pads with `=` to a multiple of 4.
  - Does **not** convert standard base64 (`+`, `/`) to url-safe base64. Keys
    made by the app are always url-safe, so a converted key is reported as
    invalid.
- **`class InvalidBackupKey(Exception)`** (new)
  - Raised when no key decrypts the data and at least one key was not valid
    Fernet.
  - Deliberately **not** a `ValueError` subclass.
- **`try_decrypt(data, keys)`** (changed)
  - `keys` holds only strings. `None` is no longer accepted, and empty
    strings are ignored.
  - Each key is normalized first. If `Fernet(...)` raises `ValueError`, the
    key is recorded as invalid and skipped.
  - When no key works, it raises `InvalidBackupKey` if any key was invalid,
    otherwise `InvalidToken`. An empty key list raises `InvalidToken`.
- `encrypt_bytes` and `decrypt_bytes` are unchanged. Backup creation keeps
  its current validation.

### `backup_utils.build_inspection`

- The `encryption_key: str | None` parameter is replaced by
  `encryption_keys: list[str]`. Callers are the route and one test in
  `test_admin_partial_restore.py`.
- When the file name ends in `.enc`, it calls
  `try_decrypt(file_bytes, encryption_keys)`, without the `None` fallback.
- `InvalidToken` still becomes `RuntimeError("Decryption failed…")`.
- `InvalidBackupKey` passes through unchanged.
- For a file that isn't `.enc`, the keys are ignored (scenario 12).

### `routes.restore_backup` (full restore)

- `keys_to_try = [provided_key, configured_key]`, filtered to the ones that
  are set. No `None` entries.
- It catches `InvalidBackupKey` and flashes
  `admin.backup.restore.invalid_key`.
- It catches `InvalidToken` and flashes `decrypt_failed`, as now.
- After either error it re-renders the form and writes nothing.

### `routes.partial_restore_inspect`

- It uses the same key order as full restore:
  `keys = [k for k in (provided_key, configured_key) if k]`. It passes
  `keys` to `build_inspection`, replacing `provided_key or configured_key`,
  which used only one of the two (scenario 8).
- It catches `InvalidBackupKey` **before** the existing `except ValueError`,
  and flashes `admin.backup.partial_restore.entry.invalid_key`.
- **The cache step after inspection** (the second decrypt before
  `_store_backup_bytes`):
  - It decrypts with the same `keys`.
  - The `except (InvalidToken, Exception): bytes_to_cache = file_bytes`
    fallback is removed. On any failure, the route flashes `decrypt_failed`,
    redirects to the entry page and caches nothing.
  - This brings the step in line with
    [[20261106-0831-restore-no-plaintext-fallback-for-enc]]. In practice it
    can't fail, because the inspection has already decrypted the file with
    the same keys.
  - The `if inspection.encrypted and encryption_key` guard becomes
    `if inspection.encrypted`.

### Key material must never be shown or logged (applies to all components)

- `InvalidBackupKey` and `InvalidToken` messages are fixed strings that never
  contain a key.
- Flash messages are fixed translation strings with no placeholders.
- No code added or changed here logs `provided_key`, `configured_key` or the
  normalized keys, or puts them in `log_event` details.

### Translations (`en.json`, `nl.json`)

| Key | English | Dutch |
|---|---|---|
| `admin.backup.restore.invalid_key` | "The encryption key is not a valid backup key. Check that you copied it completely. If you left the key field empty, the server's configured backup key is invalid; ask your administrator to check `BACKUP_ENCRYPTION_KEY`." | "De versleutelingssleutel is geen geldige back-upsleutel. Controleer of je de sleutel volledig hebt gekopieerd. Heb je het sleutelveld leeg gelaten, dan is de back-upsleutel van de server ongeldig; vraag je beheerder `BACKUP_ENCRYPTION_KEY` te controleren." |
| `admin.backup.partial_restore.entry.invalid_key` | Same text. | Same text. |

## Data Model

No changes.

## API / Interface

- `try_decrypt` no longer accepts `None` in `keys`. This is an internal
  helper, and both callers are updated.
- `normalize_key` and `InvalidBackupKey` are new.
- Routes, forms and templates are unchanged, apart from the new flash
  messages.

## Tests

- **New `tests/test_admin_backup_crypto.py`** (pure functions, no app):
  - `normalize_key` restores padding, strips whitespace and quotes, and
    leaves a valid key unchanged.
  - `try_decrypt`: the right key works, and so does the right key without
    its `=`.
  - `try_decrypt` with an invalid key alone raises `InvalidBackupKey`.
  - `try_decrypt` with a valid but wrong key raises `InvalidToken`.
  - `try_decrypt` with an invalid key followed by the right key works
    (scenario 8).
  - `try_decrypt` with an empty list raises `InvalidToken`.
- **Route tests**, alongside the existing admin backup tests or in the new
  file using the app client. These cover scenarios 2–5 for full restore,
  with `RESTORE_WATCH_DIR` set to `tmp_path`. They assert:
  - the response status is 200, not 500
  - the flash message is correct
  - whether a file was written
- **Partial-restore tests**, in `tests/test_admin_partial_restore.py`, for
  both `.sql.gz.enc` and `.db.gz.enc`:
  - scenario 1: a key without its padding works
  - scenario 3: an invalid key gives `invalid_key`, not `not_eligible`
  - scenario 8: an invalid typed key with a correct configured key works
  - scenario 9: no key gives `decrypt_failed`
- **Key-leak assertion (scenario 10).** In the invalid-key and wrong-key
  route tests, assert that the key string doesn't appear in the response
  body or in `caplog.text`.

## Operational documentation

Constitution principle V: checked on 2026-11-06. `docs/deployment.md` and
`docker/README.md` don't describe restore keys, and
`docs/backup_encryption_plan.md` is a historical plan. **No docs change is
needed.**

## Out of scope

- Detecting the backup format from file content instead of the file name.
  The file name is fine here.
- Changing how keys are generated or shown on the backup page.
- Streaming large uploads, and the restore worker (`docker/restore`).
- Having `build_inspection` return decrypted bytes so the route doesn't have
  to decrypt a second time.
- Audit logging of failed restore attempts (invalid or wrong key). This is a
  follow-up, and it must follow the key-material rule above.
- Detecting an invalid configured `BACKUP_ENCRYPTION_KEY` outside restore,
  for example on the backup page.
- Encrypted files uploaded without the `.enc` suffix, for example after a
  rename. These are still treated as unencrypted and fail later in inspection
  or in the restore worker.
- Converting standard base64 keys (`+`, `/`) to url-safe base64.

## Open Questions

- None blocking. Optionally, the backup page could show the generated key in
  a read-only field with a copy button, to stop the padding slip at the
  source. That would be a follow-up UX change.
