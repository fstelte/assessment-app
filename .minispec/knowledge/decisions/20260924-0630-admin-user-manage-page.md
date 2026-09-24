---
title: Per-user Manage page for account actions
date: 2026-09-24
status: accepted
---

## Context

The delete route `POST /admin/users/<id>/delete` already exists but has no button. Set password and reset MFA are new. The users table row already holds Manage MFA and a status button.

## Decisions

A new page `GET /admin/users/<id>/manage` holds the set-password form, the Reset MFA button and the Delete button in a danger zone. The users table gains a Manage link. Service accounts may still be deleted.

If the database rejects a delete because the user owns records, the route rolls back and tells the admin to deactivate the user instead.

## Alternatives considered

- Row buttons only: the row becomes crowded and the password form does not fit.
- Splitting across the existing MFA page: puts the password form under an MFA URL.

## Consequences

- One new template and three routes, two of them new.
