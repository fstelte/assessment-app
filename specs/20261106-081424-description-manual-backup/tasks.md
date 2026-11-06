---
feature: 20261106-081424-description-manual-backup
status: planned
created: 2026-11-06
chunk_size: adaptive
total_tasks: 3
estimated_lines: 260
---

# Restoring Encrypted Manual Backups: Tasks

## Overview

Fixes the restore of encrypted backups, as set out in `design.md`:

- Keys are normalized, which repairs a missing `=`.
- A key that is still invalid raises `InvalidBackupKey`, which shows a clear
  message instead of a 500 (full restore) or the wrong "format not eligible"
  message (partial restore).
- The plaintext `None` fallback for `.enc` files is removed.

Decisions:

- `20261106-0830-restore-normalize-and-validate-backup-key`
- `20261106-0831-restore-no-plaintext-fallback-for-enc`

## Task List

### Foundation

#### Task 1: Normalize keys and classify failures in `backup_crypto`
- **Estimate:** ~90 lines (about 35 of code, 55 of tests)
- **Files:** `scaffold/apps/admin/backup_crypto.py`, `tests/test_admin_backup_crypto.py` (new)
- **Description:**
  - Add `normalize_key(key)`. It removes all whitespace (including inside the
    key), removes one matching pair of surrounding quotes (`'` or `"`), and
    pads with `=` to a multiple of 4. It does not convert `+` or `/`.
  - Add `class InvalidBackupKey(Exception)`. It must not subclass
    `ValueError`.
  - Rewrite `try_decrypt(data, keys)`:
    - Skip falsy keys (`None`, `""`). Keys are no longer passed through as
      plaintext.
    - Normalize each key, then try it.
    - If `Fernet(...)` raises `ValueError`, mark the key as invalid and go on
      to the next one.
    - When no key works, raise `InvalidBackupKey` if any key was invalid,
      otherwise `InvalidToken`.
  - The current callers still pass `None`. With `None` ignored, they keep
    working until Tasks 2 and 3 clean them up.
- **Depends on:** None
- **Acceptance:** Pure unit tests cover:
  - `normalize_key`: missing padding, whitespace, quotes, and a valid key
    left unchanged
  - `try_decrypt`:
    - the right key works
    - the right key works without its `=` (scenario 1)
    - the right key works with spaces or quotes around it (scenario 7)
    - the right key works with a line break inside it (scenario 11)
    - neither exception's message contains the key (scenario 10)
    - an invalid key alone raises `InvalidBackupKey`
    - a valid but wrong key raises `InvalidToken`
    - an invalid key followed by the right key works (scenario 8)
    - `[]` and `[None]` raise `InvalidToken`
  - An assertion that `InvalidBackupKey` is not a `ValueError`
- **Evidence:** `pytest tests/test_admin_backup_crypto.py` passes.

### Core Implementation

#### Task 2: Full restore handles invalid and wrong keys [P]
- **Estimate:** ~70 lines
- **Parallel:** Can run with Task 3
- **Files:** `scaffold/apps/admin/routes.py` (`restore_backup`), `scaffold/translations/en.json`, `scaffold/translations/nl.json`, `tests/test_admin_backup_crypto.py` (route tests)
- **Description:**
  - Set `keys_to_try = [k for k in (provided_key, configured_key) if k]`, and
    drop the `+ [None]` and `[None]` defaults.
  - Catch `InvalidBackupKey` and flash `admin.backup.restore.invalid_key`.
  - Keep catching `InvalidToken` and flashing `decrypt_failed`.
  - Neither error writes a file.
  - Add the `admin.backup.restore.invalid_key` text in `en` and `nl`, using
    the wording in `design.md`.
- **Depends on:** Task 1
- **Acceptance:** Route tests use the admin client and set
  `RESTORE_WATCH_DIR` to `tmp_path`. Upload a `.sql.gz.enc` encrypted with
  key K and check each case:

  | Scenario | Key used | Expected result |
  |---|---|---|
  | 2 | K without its `=` | The decrypted `.sql.gz` is written, and "queued" is shown |
  | 3 | `my-passphrase` | Status 200 (not 500), the `invalid_key` message, no file |
  | 4 | A different valid key | `decrypt_failed`, no file |
  | 5 | No key, and none configured | `decrypt_failed`, no file |
  | 6 | Plain `.sql.gz` upload | Unchanged |
  | 12 | Plain `.sql.gz` upload with a key typed | Unchanged, key ignored |

  In scenarios 3 and 4, also assert that the key string isn't in the
  response body or in `caplog.text` (scenario 10).
- **Evidence:** The route tests pass, and the 500 is reproduced before the
  fix and gone after it.

#### Task 3: Partial restore reports invalid keys correctly [P]
- **Estimate:** ~90 lines
- **Parallel:** Can run with Task 2
- **Files:**
  - `scaffold/apps/admin/backup_utils.py` (`build_inspection`)
  - `scaffold/apps/admin/routes.py` (`partial_restore_inspect`)
  - `scaffold/translations/en.json`, `scaffold/translations/nl.json`
  - `tests/test_admin_partial_restore.py`
- **Description:**
  - **`build_inspection`:**
    - Replace `encryption_key: str | None` with `encryption_keys: list[str]`.
    - Call `try_decrypt(file_bytes, encryption_keys)` without the `None`
      fallback. `InvalidToken` still becomes
      `RuntimeError("Decryption failed…")`, and `InvalidBackupKey` passes
      through.
    - Update the existing call at `test_admin_partial_restore.py:797` to
      `encryption_keys=[]`.
  - **`partial_restore_inspect`, key order:** build
    `keys = [k for k in (provided_key, configured_key) if k]`, the same as
    full restore, and pass it to `build_inspection`.
  - **`partial_restore_inspect`, errors:** add `except InvalidBackupKey`
    **before** `except ValueError`. It flashes
    `admin.backup.partial_restore.entry.invalid_key` and redirects to the
    entry page.
  - **`partial_restore_inspect`, cache step:**
    - The guard becomes `if inspection.encrypted`.
    - Decrypt with `keys`.
    - Remove the `except (InvalidToken, Exception): bytes_to_cache =
      file_bytes` fallback. On failure, flash `decrypt_failed`, redirect and
      cache nothing (decision 0831).
  - Add the `admin.backup.partial_restore.entry.invalid_key` text in `en`
    and `nl`, using the wording in `design.md`.
- **Depends on:** Task 1
- **Acceptance:** Tests in `test_admin_partial_restore.py` cover both a
  `.sql.gz.enc` and a `.db.gz.enc` encrypted with K:
  - K without its `=`. The selection page lists the tables (scenario 1).
  - `my-passphrase`. The flash is `invalid_key`, not `not_eligible`, there
    is no 500, and the key isn't in the response or in `caplog.text`
    (scenarios 3 and 10).
  - A valid but wrong key. The flash is `decrypt_failed`, not
    `inspect_failed` (scenario 4).
  - `my-passphrase` typed, with K configured as `BACKUP_ENCRYPTION_KEY`. The
    tables are listed (scenario 8).
  - No key typed and none configured. The flash is `decrypt_failed`, and
    nothing is cached (scenario 9).
- **Evidence:** `pytest tests/test_admin_partial_restore.py` passes, and the
  full suite stays green.

## Notes

- **Why the exception is separate.** `InvalidBackupKey` is deliberately not a
  `ValueError`. Otherwise `partial_restore_inspect`'s `except ValueError`
  would catch it and show the misleading "format not eligible" message
  again.
- **Second decrypt.** After inspecting, `partial_restore_inspect` decrypts
  the file a second time to cache it. Task 3 removes its ciphertext fallback
  (checklist CHK011). It is left in place otherwise; removing it entirely is
  deferred.
- **Keys stay secret.** No new or changed code may put a key into a log
  line, a flash message, exception text or `log_event` details (design
  §Key material).
- **Docs.** None needed, checked on 2026-11-06 (design §Operational
  documentation).
- **No-encryption fixture.** The tests need to clear `BACKUP_ENCRYPTION_KEY`
  or set it explicitly, so a key configured in the environment doesn't
  change the results.
- **Graph.** Run `graphify update .` after the code tasks.
- **Deferred:**
  - a copy button for the generated key on the backup page
  - having `build_inspection` return the decrypted bytes so the route
    doesn't decrypt twice

## Progress
- [x] Task 1: Normalize keys and classify failures in `backup_crypto`
- [ ] Task 2: Full restore handles invalid and wrong keys
- [ ] Task 3: Partial restore reports invalid keys correctly
