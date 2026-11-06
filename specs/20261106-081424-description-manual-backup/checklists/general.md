---
type: checklist
domain: general
feature: 20261106-081424-description-manual-backup
created: 2026-11-06
status: completed
---

# General Requirements Quality Checklist (security emphasis)

**Purpose:** Check that the requirements for restoring encrypted backups are
complete, clear and consistent before implementation starts.
**Feature:** 20261106-081424-description-manual-backup

Checked items are already satisfied by `design.md` and `tasks.md`.
Unchecked items are gaps to resolve, with a short note.

## Completeness

- [x] CHK001 - Is the root cause tied to a specific exception type and code location for each flow? [Completeness, Design §Overview]
- [x] CHK002 - Are the normalization rules listed as specific transformations (whitespace, one matching pair of quotes, `=` padding to a multiple of 4)? [Completeness, Design §backup_crypto]
- [x] CHK003 - Does the design say whether normalization also handles internal whitespace or line breaks, or standard base64 (`+`, `/`) instead of url-safe base64 (`-`, `_`)? [Gap]
  *Unspecified. A key pasted across two lines, or converted to standard base64, would still be rejected as invalid. Decide whether to accept it or reject it explicitly.*
- [x] CHK004 - Are requirements defined for the partial-restore flow when a `.enc` file is uploaded with no key and none configured? [Gap, Coverage]
  *Scenario 5 covers full restore only. Given the design, partial restore would show `decrypt_failed` through `RuntimeError`. Say so.*
- [x] CHK005 - Are audit-logging requirements defined for failed restore attempts (invalid key, wrong key)? [Gap, Security]
  *`partial_restore_inspect` logs `partial_restore_inspect` on success only. The design doesn't say whether failed decryptions should be logged with `log_event`. The constitution emphasises reviewable activity.*

## Clarity

- [x] CHK006 - Is the user-facing text for `invalid_key` specified word for word in both languages? [Clarity, Design §Translations]
- [x] CHK007 - Is it unambiguous which exception wins when several keys fail for different reasons (any invalid key gives `InvalidBackupKey`)? [Clarity, Design §try_decrypt]
- [x] CHK008 - Is it clear what the admin should do when `invalid_key` is caused by the server's `BACKUP_ENCRYPTION_KEY` rather than the key they typed? [Clarity, Gap]
  *With no key typed and an invalid configured key, the message "Check that you copied it completely" points at a key the admin never entered.*
- [x] CHK009 - Is the docs requirement ("if `docs/deployment.md` … describes the restore key") resolved to a definite yes or no? [Clarity, Design §Operational documentation]
  *It is conditional. Check the docs once and record the outcome in the task.*

## Consistency

- [x] CHK010 - Are key-precedence rules the same in both flows? [Consistency, Conflict]
  *Full restore tries the typed key and then the configured key. Partial restore uses `provided_key or configured_key`, so only one of them. Scenario 8 (an invalid typed key, rescued by the configured key) therefore holds only for full restore. Align the flows, or document the difference.*
- [x] CHK011 - Does the "never treat an encrypted file as plaintext" decision apply to the re-decrypt step in `partial_restore_inspect` too? [Consistency, Conflict, Decision 0831]
  *That step still has `except (InvalidToken, Exception): bytes_to_cache = file_bytes`, which caches ciphertext. The design calls it "inherits normalization, no other change". That contradicts decision 0831.*
- [x] CHK012 - Is `InvalidBackupKey` required not to be a `ValueError`, so it can't fall into the "not eligible" branch? [Consistency, Design §backup_crypto, Tasks Notes]
- [x] CHK013 - Do the translation keys follow the existing namespaces (`admin.backup.restore.*`, `admin.backup.partial_restore.entry.*`)? [Consistency]

## Security

- [x] CHK014 - Does the design forbid the key, or any part of it, appearing in flash messages, exception text, logs or audit details? [Gap, Security]
  *Not stated. `InvalidBackupKey` messages and any new `log_event` details should never include key material.*
- [x] CHK015 - Does the design keep normalization out of backup creation, so lenient parsing doesn't weaken key generation? [Security, Decision 0830 §Consequences]
- [x] CHK016 - Is it defined whether an invalid configured `BACKUP_ENCRYPTION_KEY` should be surfaced to admins (for example on the backup page) rather than only at restore time? [Gap, Security/Operational]
  *Today it is found only when a restore fails. That may be acceptable, but make the choice explicit.*
- [x] CHK017 - Does the design say nothing is written to `RESTORE_WATCH_DIR` or cached when decryption fails? [Security, Scenarios 3–5]

## Measurability

- [x] CHK018 - Does every scenario have an objective outcome (status code, specific flash key, file written or not)? [Measurability, Design §Acceptance scenarios]
- [x] CHK019 - Does every task have concrete evidence (a named pytest file passing, the 500 reproduced before the fix)? [Measurability, Tasks]

## Coverage

- [x] CHK020 - Are unencrypted backups (`.sql.gz`, `.db.gz`) covered as a regression scenario? [Coverage, Scenario 6]
- [x] CHK021 - Are both backends (`.sql.gz.enc` and `.db.gz.enc`) covered for partial restore? [Coverage, Task 3]
- [x] CHK022 - Is the case "key supplied for a non-`.enc` file" addressed? [Coverage, Edge Case]
  *Presumably the key is ignored, but no requirement says so.*
- [x] CHK023 - Does the design address an encrypted file uploaded without the `.enc` suffix, for example after a rename? [Coverage, Edge Case]
  *Out of scope is fine, but say so under Out of scope.*

## Summary

- **Total items:** 23. All are resolved as of 2026-11-06.
- **Resolved in this update:**
  - **CHK011:** the cache step's ciphertext fallback is removed (Task 3,
    decision 0831).
  - **CHK010:** both flows try the typed key, then the configured key
    (scenario 8).
  - **CHK014:** a rule that keys never appear in messages or logs
    (scenario 10, with test assertions).
  - **CHK008:** the `invalid_key` text now also covers an invalid configured
    key.
  - **CHK003:** whitespace inside a key is removed; `+` and `/` are not
    converted.
  - **CHK004:** scenario 9.
  - **CHK022:** scenario 12.
  - **CHK009:** no docs change needed.
- **Moved to Out of scope:**
  - **CHK005:** audit logging of failed restore attempts.
  - **CHK016:** checking the configured key outside restore.
  - **CHK023:** encrypted files without the `.enc` suffix.
