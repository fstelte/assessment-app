# UAT Plan

This plan defines the user acceptance testing (UAT) scenarios and feedback handling process for the Control Self-Assessment platform.

## Objective

Validate that end-to-end flows meet business requirements before production release, covering onboarding, MFA security, assessment data entry, and reporting.

## Test Scenarios

### Scenario 1: User Registration with Admin Activation
- **Preconditions:** Admin account exists; outbound email optional (simulation allowed).
- **Steps:**
  1. Prospective user completes the registration form at `/auth/register`.
  2. Admin logs into `/admin/` and reviews pending registrations.
  3. Admin activates the new user.
  4. User receives confirmation (email or manual notification) and logs in.
- **Acceptance Criteria:** Pending user is invisible to login until activated; audit timestamps updated; admin sees success flash message.

### Scenario 2: MFA Enrollment and Verification
- **Preconditions:** Scenario 1 user is active and logged in.
- **Steps:**
  1. User navigates to `/auth/mfa/setup`.
  2. User scans the QR code with an authenticator app.
  3. User enters the generated code and submits the form.
  4. User signs out and logs back in, completing the MFA challenge.
- **Acceptance Criteria:** `enrolled_at` and `last_verified_at` timestamps persist; login fails without correct MFA code; UI shows success messages.

### Scenario 3: Completing an Assessment
- **Preconditions:** Assessment template and assignments seeded (via importer or fixtures); user has access rights.
- **Steps:**
  1. User opens assigned assessment.
  2. User selects a control, enters responses, and attaches evidence notes.
  3. User saves changes and confirms they persist on refresh.
- **Acceptance Criteria:** Responses stored in database; status indicators update; timestamps reflect save time.

### Scenario 4: Generating Results Report
- **Preconditions:** Completed assessment with populated responses.
- **Steps:**
  1. User triggers the reporting action (HTML/PDF export placeholder or CSV export command).
  2. System compiles results summary (coverage, risk rating placeholders).
  3. User downloads or views the report.
- **Acceptance Criteria:** Report includes all responses; metadata (assessment name, date, owner) correct; export action logged.

## Feedback Collection & Processing

1. **Capture:** Testers record findings in the shared UAT spreadsheet or issue tracker using the template (severity, steps to reproduce, expected vs. actual outcome, screenshots).
2. **Triage:** Product owner and tech lead review daily, tagging each item as `defect`, `enhancement`, or `question`.
3. **Resolution:**
   - Critical defects addressed immediately and retested within 24 hours.
   - Enhancements assessed post-UAT and scheduled into the roadmap backlog.
4. **Sign-off:** Once all blockers are resolved or accepted, stakeholders sign the UAT completion form and authorize deployment.

## Exit Criteria

- All four scenarios executed successfully by at least two testers.
- No open critical or high-severity defects.
- Documentation updated for any deviations discovered during testing.
