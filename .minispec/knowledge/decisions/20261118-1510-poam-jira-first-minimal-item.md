---
type: decision
id: 20261118-1510-poam-jira-first-minimal-item
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/ssp/models.py
  - scaffold/apps/ssp/forms.py
  - scaffold/apps/ssp/routes.py
  - scaffold/apps/ssp/templates/ssp/poam.html
  - scaffold/apps/ssp/templates/ssp/poam_item_form.html
  - scaffold/apps/ssp/templates/ssp/view.html
  - scaffold/apps/ssp/templates/ssp/print.html
  - migrations/versions/*
tags: [ssp, poam, jira, ux]
participants: [Ferry Stelte, Claude]
---

# POA&M items are Jira-first: weakness, status and a Jira link; everything else optional

## Context

The POA&M exists to steer and monitor improvements to the system described in
the SSP. Teams already track the actual work in Jira, so building out tasks
(resources, cost, contact, milestones) in the app duplicates that effort. The
user wants a Jira link in place of full task authoring.

## Options Considered

### Option 1: Jira link replaces milestones; steering fields stay prominent
- ✅ Keeps owner, date and status visible in the SSP
- ❌ Still asks for more than many teams want to fill in

### Option 2: Jira-first, minimal item
- ✅ Lightest; the SSP links to where the work happens
- ❌ Less steering detail in the SSP itself unless users open the optional details

### Option 3: Purely additive Jira link
- ✅ No behaviour change
- ❌ Does not remove the duplicated task authoring

## Decision

We chose **Option 2**.

- New column `POAMItem.jira_url` (String 500, nullable). The form validates it
  as an absolute `http(s)://` URL. It stays optional because POA&M items
  auto-created from threat mitigations (`source_threat_mitigation_id`) start
  without one.
- Item form, primary block: weakness description (required), status, Jira link.
- Item form, collapsed "Details (optional)" block: point of contact, scheduled
  completion, resources required, estimated cost, and the milestones panel.
  Nothing is removed and existing data stays visible. The block opens
  automatically when any of these fields has a value or milestones exist
  (20261118-1530, CHK011).
- The Jira link appears as an external link (`target="_blank"
  rel="noopener noreferrer"`) on the POA&M list, in the SSP view's POA&M table
  and in the print/PDF export (as the URL text).
- POA&M list, SSP view section and item form get an intro text: the POA&M is for
  steering and monitoring improvements to the system described in this plan,
  and detailed work is tracked in Jira.

## Consequences

### Positive
- ✅ No duplicate task authoring; the SSP points to the real work
- ✅ Purely additive schema change; no data loss

### Negative
- ❌ The SSP cannot see Jira status (no integration; plain link only)
