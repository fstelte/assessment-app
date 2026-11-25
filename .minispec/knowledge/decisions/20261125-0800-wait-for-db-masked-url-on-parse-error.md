---
type: decision
id: 20261125-0800-wait-for-db-masked-url-on-parse-error
date: 2026-11-25
status: accepted
supersedes: null
superseded_by: null
impacts:
  - docker/wait_for_db.py
tags: [security, logging, postgres, startup]
participants: [Ferry Stelte, Claude]
---

# wait_for_db prints a masked URL, never the raw URL or SQLAlchemy's parse error

## Context

When `DATABASE_URL` can't be parsed (usually because a password contains `@`, `/`,
`#` or `?` without URL encoding), `docker/wait_for_db.py` prints
`invalid DATABASE_URL '<raw url>': <exc>`. SQLAlchemy's `ArgumentError` text
(`Could not parse SQLAlchemy URL from string '...'`) contains the raw URL again.
This was the password leak seen in the app container log. The entrypoint uses
`set -e`, so `flask db upgrade` and gunicorn never run after this failure; wait_for_db
is the only place where it shows.

## Options Considered

- A: print only a hint, no URL: simplest, nothing to mask.
- **B: print a masked URL plus a hint (chosen).** It still helps with host, port
  or database typos.

## Decision

- Masking works on the raw string, without parsing it: find `://`, then the **last**
  `@` after it. If there is one, the part between is the userinfo. Keep everything
  up to the first `:` in the userinfo (the user) and replace the rest with `***`.
  Using the last `@` covers passwords that contain `@`, because a host can't contain
  `@`. No `@`: nothing to mask, print as is.
- The message is `invalid DATABASE_URL '<masked>'; URL-encode special characters
  in the password (e.g. @ -> %40)`. The exception text is **not** printed, because
  it contains the raw URL.
- The final `database bootstrap failed: {exc}` also goes through the mask.
- The mask helper is inline in `wait_for_db.py`
  ([[20261125-0805-pg-credential-helpers-inline-per-script]]).

## Consequences

### Positive
- ✅ An admin can still see host/port/database in the error.
- ✅ The hint points to the most likely cause.

### Negative
- ⚠️ A string without `://` (complete garbage) is printed as is. In that case it
  isn't a URL with a password in the userinfo position, but it could still contain
  a secret. Accepted: better than an error message that doesn't help.

## Related Decisions

- [[20261125-0753-pg-password-via-pgpassword-env]]
