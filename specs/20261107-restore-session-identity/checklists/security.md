---
type: checklist
domain: security
feature: 20261107-restore-session-identity
created: 2026-11-07
status: completed
---

# Security Requirements Quality Checklist

**Purpose:** Check that the security requirements for restore-safe session
identity are complete, clear and consistent.
**Feature:** 20261107-restore-session-identity

## Completeness

- [x] CHK001 - Does the design cover the session keys **before login** that hold a numeric user id (`mfa_pending_user_id` and `mfa_enroll_user_id` in `auth/flow.py`, `passkey_reg_user_id` in `auth/routes.py`)? After a full restore they can point to a different user, and rotating tokens doesn't invalidate them with cookie sessions. With `mfa_enroll_user_id`, someone could enroll their own TOTP on someone else's account. [Gap, critical]
- [x] CHK002 - Does the design say whether `session_token` is stored in the database **as is** or as a hash, and why that's acceptable (forging a cookie still needs `SECRET_KEY`)? [Gap, Decision 0848]
- [x] CHK003 - Is it specified which source of randomness generates tokens in each path: Python `secrets` (app and migration), PostgreSQL in `restore_db.py` (`random()` isn't a cryptographic random generator; `gen_random_uuid()` is), and SQLite (`randomblob` versus `secrets` in Python)? [Gap, Design §Full restore]
- [x] CHK004 - Is it defined whether deactivating or deleting a user (admin or SCIM deprovisioning) rotates the token or relies on `is_active`? [Gap]
- [x] CHK005 - Are remember-me cookie settings (`REMEMBER_COOKIE_DURATION`, `_SECURE`, `_HTTPONLY`, `_SAMESITE`) included or explicitly marked out of scope? [Completeness]
- [x] CHK006 - Is the expected identity after a **failed** rotation during a full restore described? Tokens from the same database stay tied to the same person, but a backup from another environment doesn't. [Gap, Decision 0855]

## Clarity

- [x] CHK007 - Is "every user except the admin who ran it" defined by `user_id` from the run, and is it clear what happens if that admin isn't in the database (anymore)? [Clarity, Design §Partial restore]
- [x] CHK008 - Is the token format the same in all three paths: 43 characters `token_urlsafe` versus 64 hex characters from `md5||md5` or `randomblob`, all fitting `String(64)`? [Clarity, Data Model]
- [x] CHK009 - Is it clear that `invalidate_user_sessions` keeps an admin's **own** session out when the admin is the target, as decision 20260924-0620 and the call sites do? [Clarity, Decision 0905]

## Consistency

- [x] CHK010 - Is the "restore always counts as successful when rotation fails" rule consistent between `restore_db.py` (state file), the partial restore (`run.warnings`) and constitution II (no silent skipping)? [Consistency]
- [x] CHK011 - Do the design (`String(64)`, `token_urlsafe(32)`) and decision 0855 (SQL `md5||md5`) describe the same column contract? [Consistency]
- [x] CHK012 - Is the timing of the `sha256` fingerprint ("only together with the token") reflected in the tasks, as the same deploy as Task 1 and not separately? [Consistency, tasks.md Task 2]

## Measurability

- [x] CHK013 - Is SC-001 reproducible with an exact scenario: which ids swap, and which request should be anonymous? [Measurability]
- [x] CHK014 - Is the remember-me side of SC-001 testable without a real browser, with a test approach described? [Measurability, tasks.md Task 1(d)]
- [x] CHK015 - Can SC-004 ("survives a restart") be verified objectively, with a test across two processes because `hash()` randomness is per process? [Measurability]

## Coverage

- [x] CHK016 - Are **concurrent requests** during a partial restore covered: a request that loads a session between the restore and the rotation? [Coverage, Edge Case]
- [x] CHK017 - Are the audit requirements for the security-relevant event "all sessions ended after restore" specified, or explicitly rejected (constitution II, audit visibility)? [Coverage]
- [x] CHK018 - Is the impact of the one-time logout at deployment on SSO users (Azure) and service accounts described? [Coverage]
- [x] CHK019 - Is the threat "an old backup leaks, including tokens" analysed, along with what it means when `SECRET_KEY` has leaked too? [Coverage, Threat model]
- [x] CHK020 - Is the downgrade of the migration safe from a security point of view: does `get_id()` fall back to the numeric id after a downgrade, and is that intended? [Coverage, Design §Migration]

## Resolution (2026-11-07, warnings W1–W4)

Settled in design.md §Security Notes, §Components, §Out of Scope, and in decisions 0848/0855/0905:
- CHK002/019: storing the token as is is argued (forging needs `SECRET_KEY`), and the backup-leak threat is described.
- CHK004: admin deactivation is covered (call site around line 1516); SCIM deprovisioning is a follow-up under Out of Scope.
- CHK005: remember-me cookie hardening is out of scope (Flask-Login defaults noted).
- CHK006/010: identity after a failed rotation and the failure rules are described consistently.
- CHK007/009: "admin who ran it" = `user_id` of the run; the admin's own session is handled at the call sites.
- CHK008/011: one token format, 64 hex characters (`secrets.token_hex(32)` in the app, migration and SQLite step).
- CHK012: `sha256` only together with Task 1 (same PR or release).
- CHK013–015: SC-001, remember-me and SC-004 test scenarios written out.
- CHK016/018: concurrent requests and the one-time logout at deployment are described.
- CHK020: downgrade only together with rolling back the code (migration docstring).

**CHK001 (C1) settled in Task 1:** the MFA/passkey steps before login store the session token. **CHK003 (C2) and CHK017 (C3) settled in Tasks 3 and 4.** All 20 items are settled.

## Summary

- **Total items:** 20
- **Focus areas:** session identity before login, token randomness and storage, failure paths, auditability
- **Main gaps found:**
  - **CHK001 (critical):** MFA and passkey steps before login use the numeric `user.id` in the session, and a restore can't invalidate it with cookie sessions.
  - CHK003: PostgreSQL `random()` isn't a cryptographically secure generator for tokens.
  - CHK002 / CHK019: storing tokens as is, and the backup-leak threat, aren't argued.
  - CHK017: no audit event for "all sessions ended".
