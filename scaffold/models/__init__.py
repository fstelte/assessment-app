"""Unified model registry for the scaffold application.

This module centralises the SQLAlchemy metadata by re-exporting identity,
BIA, and CSA domain models. It reconciles the overlapping entities found in
the legacy ``bia_app`` and ``csa_app`` projects:

* ``User`` now captures the superset of fields and lifecycle hooks from both
    applications (status, MFA, role assignments, dark-mode preference).
* Legacy BIA tables are prefixed with ``bia_`` to coexist with CSA schemas
    under the same database. Foreign-keys now reference ``users.id`` instead of
    the former ``user`` table.
* CSA audit and assessment artefacts retain their structure but bind to the
    shared ``User`` model via creator/assignee relationships.

See ``MIGRATION_REQUIREMENTS`` and ``BACKWARD_COMPATIBILITY_CONCERNS`` below
for concrete steps when upgrading an existing deployment.
"""

from __future__ import annotations

# Import identity models first so user relationships are available.
from ..apps.identity.models import MFASetting, Role, TimestampMixin, User, UserStatus

# Domain-specific models.
from ..apps.bia.models import (
    AIIdentificatie,
    AvailabilityRequirements,
    Component,
    Consequences,
    ContextScope,
    Summary,
)
from ..apps.csa.models import (
    Assessment,
    AssessmentAssignment,
    AssessmentDimension,
    AssessmentResponse,
    AssessmentResult,
    AssessmentStatus,
    AssessmentTemplate,
    AuditTrail,
    Control,
)
from ..apps.risk.models import (
    Risk,
    RiskChance,
    RiskImpact,
    RiskImpactArea,
    RiskImpactAreaLink,
    RiskSeverity,
    RiskSeverityThreshold,
    RiskTreatmentOption,
)
from ..apps.maturity.models import MaturityAnswer, MaturityAssessment, MaturityLevel, MaturityScore
from .audit import AuditLog

__all__ = [
    "TimestampMixin",
    "User",
    "UserStatus",
    "Role",
    "MFASetting",
    "ContextScope",
    "Component",
    "Consequences",
    "AvailabilityRequirements",
    "AIIdentificatie",
    "Summary",
    "Assessment",
    "AssessmentAssignment",
    "AssessmentDimension",
    "AssessmentResponse",
    "AssessmentResult",
    "AssessmentStatus",
    "AssessmentTemplate",
    "Control",
    "AuditTrail",
    "AuditLog",
    "Risk",
    "RiskChance",
    "RiskImpact",
    "RiskImpactArea",
    "RiskImpactAreaLink",
    "RiskSeverity",
    "RiskSeverityThreshold",
    "RiskTreatmentOption",
    "MaturityLevel",
    "MaturityScore",
    "MaturityAssessment",
    "MaturityAnswer",
]

MIGRATION_REQUIREMENTS: list[str] = [
    "Rename legacy BIA tables (`context_scope`, `component`, `consequences`, etc.) to the new `bia_`-prefixed names or configure views to maintain legacy naming.",
    "Introduce the shared `users` table with status enum (`user_status`) and migrate credentials/MFA secrets from legacy BIA/CSA user tables.",
    "Backfill `ContextScope.author_id` from the previous `user_id` column and drop the legacy field once verified.",
    "Ensure Alembic revisions recreate the enum types used by CSA (assessment status/result/dimension).",
]

BACKWARD_COMPATIBILITY_CONCERNS: dict[str, str] = {
    "password_hash": "BIA stored PBKDF2 hashes compatible with Werkzeug. CSA used the same scheme; no re-hash needed as long as `werkzeug.security` stays in use.",
    "role_management": "Legacy BIA used a plain string `role` column. During migration assign matching `Role` rows and populate the association table to preserve permissions.",
    "mfa": "`MFASetting` consolidates BIA `mfa_secret` and CSA `mfa_settings` records. Populate the unified table and mark `enabled` appropriately to avoid forcing re-enrolment.",
    "table_prefix": "Existing SQL integrations referencing raw table names must be updated to the new `bia_`/`csa_` prefixed naming convention or provided with compatibility views.",
}
