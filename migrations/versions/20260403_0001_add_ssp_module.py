"""Add SSP module tables and ContextScope SSP fields

Revision ID: 20260403_0001
Revises: 20260322_0001
Create Date: 2026-04-03 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260403_0001"
down_revision = "20260322_0001"
branch_labels = None
depends_on = None

FIPS_RATING_VALUES = ("not_set", "low", "moderate", "high")
AGREEMENT_TYPE_VALUES = ("mou", "isa", "contract", "informal", "none")
DATA_DIRECTION_VALUES = ("incoming", "outgoing", "bidirectional")
IMPL_STATUS_VALUES = ("planned", "partially_implemented", "implemented", "not_applicable")
CONTROL_SOURCE_VALUES = ("threat", "risk", "manual")
OPERATIONAL_STATUS_VALUES = ("operational", "under_development", "major_modification")
SYSTEM_TYPE_VALUES = ("major_application", "general_support_system")


def upgrade() -> None:
    # ── New columns on bia_context_scope ──────────────────────────────────────
    op.add_column(
        "bia_context_scope",
        sa.Column("abbreviation", sa.String(50), nullable=True),
    )
    op.add_column(
        "bia_context_scope",
        sa.Column(
            "operational_status",
            sa.Enum(
                *OPERATIONAL_STATUS_VALUES,
                name="context_scope_operational_status",
                native_enum=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "bia_context_scope",
        sa.Column(
            "system_type",
            sa.Enum(
                *SYSTEM_TYPE_VALUES,
                name="context_scope_system_type",
                native_enum=False,
            ),
            nullable=True,
        ),
    )

    # ── ssp_plans ─────────────────────────────────────────────────────────────
    op.create_table(
        "ssp_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "context_scope_id",
            sa.Integer(),
            sa.ForeignKey("bia_context_scope.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("laws_regulations", sa.Text(), nullable=True),
        sa.Column("authorization_boundary", sa.Text(), nullable=True),
        sa.Column(
            "fips_confidentiality",
            sa.Enum(*FIPS_RATING_VALUES, name="ssp_fips_conf", native_enum=False),
            nullable=False,
            server_default="not_set",
        ),
        sa.Column(
            "fips_integrity",
            sa.Enum(*FIPS_RATING_VALUES, name="ssp_fips_integ", native_enum=False),
            nullable=False,
            server_default="not_set",
        ),
        sa.Column(
            "fips_availability",
            sa.Enum(*FIPS_RATING_VALUES, name="ssp_fips_avail", native_enum=False),
            nullable=False,
            server_default="not_set",
        ),
        sa.Column("plan_completion_date", sa.Date(), nullable=True),
        sa.Column("plan_approval_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ── ssp_interconnections ──────────────────────────────────────────────────
    op.create_table(
        "ssp_interconnections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ssp_id",
            sa.Integer(),
            sa.ForeignKey("ssp_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("system_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("owning_organization", sa.String(255), nullable=True),
        sa.Column(
            "agreement_type",
            sa.Enum(*AGREEMENT_TYPE_VALUES, name="ssp_agreement_type", native_enum=False),
            nullable=False,
            server_default="none",
        ),
        sa.Column(
            "data_direction",
            sa.Enum(*DATA_DIRECTION_VALUES, name="ssp_data_direction", native_enum=False),
            nullable=False,
            server_default="bidirectional",
        ),
        sa.Column("security_contact", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    # ── ssp_control_entries ───────────────────────────────────────────────────
    op.create_table(
        "ssp_control_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ssp_id",
            sa.Integer(),
            sa.ForeignKey("ssp_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "control_id",
            sa.Integer(),
            sa.ForeignKey("csa_controls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "implementation_status",
            sa.Enum(*IMPL_STATUS_VALUES, name="ssp_impl_status", native_enum=False),
            nullable=False,
            server_default="planned",
        ),
        sa.Column("responsible_entity", sa.String(255), nullable=True),
        sa.Column("implementation_statement", sa.Text(), nullable=True),
        sa.Column(
            "source",
            sa.Enum(*CONTROL_SOURCE_VALUES, name="ssp_control_source", native_enum=False),
            nullable=False,
            server_default="manual",
        ),
        sa.UniqueConstraint("ssp_id", "control_id", name="uq_ssp_control_entry"),
    )


def downgrade() -> None:
    op.drop_table("ssp_control_entries")
    op.drop_table("ssp_interconnections")
    op.drop_table("ssp_plans")

    op.drop_column("bia_context_scope", "system_type")
    op.drop_column("bia_context_scope", "operational_status")
    op.drop_column("bia_context_scope", "abbreviation")
