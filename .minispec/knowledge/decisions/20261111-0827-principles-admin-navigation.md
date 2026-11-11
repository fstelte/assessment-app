---
type: decision
id: 20261111-0827-principles-admin-navigation
date: 2026-11-11
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/admin/templates/admin/users.html
  - scaffold/templates/partials/navigation.html
  - scaffold/translations/en.json
  - scaffold/translations/nl.json
tags: [admin, navigation, ssp, adr, principles]
participants: [Ferry Stelte, Claude]
---

# Principles get a link in the admin button row and an admin-only nav button

## Context

`/admin/principles` (`admin.principles`) manages the architecture principles
that ADRs are anchored to. It has no entry in any menu. The only way in is the
empty-state link on the ADR list (`ssp/adrs.html`), which disappears once at
least one principle exists.

The "admin menu" is the button row at the top of `admin/users.html`
(authentication methods, risk management, tiers, labels, audit trail, backup,
and so on). The top navigation has section entries (`NavEntry`, with no role
filtering) and a right-hand group with role checks in the template (the
"Admin" button is `has_role('admin')`).

The page itself admits admins **and** control owners (`_require_control_admin`).

## Options Considered

- A: only the Users page button row.
- **B: the button row plus a button in the top-right nav group (chosen).**
- C: the button row plus a permanent "Manage principles" link on the ADR list.

For the audience of the nav button:

- B1: admins and control owners (matching the page's access check).
- **B2: admins only (chosen).**

## Decision

- Add a "Principles" button to the `admin/users.html` button row, in the same
  style as the other links, pointing to `url_for('admin.principles')`.
- Add a "Principles" button to the right-hand group in
  `partials/navigation.html`, inside the existing
  `{% if current_user.has_role('admin') %}` block, next to "Admin".
- It is not a `NavEntry`: those have no role filter and would show the link to
  everyone.
- Control owners who aren't admins get no new link. Their access to the page
  doesn't change.

## Consequences

### Positive
- ✅ Admins can reach principles from anywhere in one click.
- ✅ No new role logic: the link reuses the existing admin check.

### Negative
- ⚠️ Admins have two links to the same page (the button row and the nav).
- ⚠️ Non-admin control owners can use the page but have no menu link to it.
  Revisit if they ask for one (option B1).

## Related Decisions

- [[20261111-0828-principle-description-no-length-cap]]
