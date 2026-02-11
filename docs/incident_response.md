# Incident Response Plan Module

The Incident Response module allows organizations to define "If This Then That" style response plans for their components. It integrates with the Business Impact Analysis (BIA) module to pull in recovery targets.

## Data Model

### IncidentScenario (The "If")
Represents a specific event that triggers a response plan.
- **Linked to:** `Component` (1:N)
- **Fields:** Name, Description.

### IncidentStep (The "Then")
Contains the actionable steps for a scenario.
- **Linked to:** `IncidentScenario` (1:1)
- **Fields:**
  - `actions_first_hour`: Immediate actions.
  - `alternatives`: Fallback procedures.
  - `rto`: Recovery Time Objective (Snapshot from BIA).
  - `rpo`: Recovery Point Objective (Snapshot from BIA).
  - `contact_list`: Who to notify.
  - `manual_procedures`: Offline operation steps.

## Integration

The module is registered as a blueprint in `scaffold/apps/incident`.
It adds a navigation entry to the main sidebar.

### Configuration
Ensure the module is enabled in your environment if feature flags are used (currently enabled by default if the code is present).
