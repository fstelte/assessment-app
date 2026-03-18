"""Add threat modeling module tables

Revision ID: 20260317_0001
Revises: 20260309_0003
Create Date: 2026-03-17 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260317_0001"
down_revision = "20260309_0003"
branch_labels = None
depends_on = None

ASSET_TYPE_VALUES = ("component", "data_flow", "trust_boundary", "external_entity", "data_store")
STRIDE_CATEGORY_VALUES = (
    "spoofing",
    "tampering",
    "repudiation",
    "information_disclosure",
    "denial_of_service",
    "elevation_of_privilege",
    "lateral_movement",
)
TREATMENT_OPTION_VALUES = ("accept", "mitigate", "transfer", "avoid")
SCENARIO_STATUS_VALUES = ("identified", "analysed", "mitigated", "accepted", "closed")
RISK_LEVEL_VALUES = ("low", "medium", "high", "critical")


def upgrade() -> None:
    op.create_table(
        "threat_models",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "threat_model_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "threat_model_id",
            sa.Integer(),
            sa.ForeignKey("threat_models.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "asset_type",
            sa.Enum(*ASSET_TYPE_VALUES, name="asset_type_enum", native_enum=False),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "threat_scenarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "threat_model_id",
            sa.Integer(),
            sa.ForeignKey("threat_models.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asset_id",
            sa.Integer(),
            sa.ForeignKey("threat_model_assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "stride_category",
            sa.Enum(*STRIDE_CATEGORY_VALUES, name="stride_category_enum", native_enum=False),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("threat_actor", sa.String(length=255), nullable=True),
        sa.Column("attack_vector", sa.Text(), nullable=True),
        sa.Column("preconditions", sa.Text(), nullable=True),
        sa.Column("impact_description", sa.Text(), nullable=True),
        sa.Column("affected_cia", sa.String(length=3), nullable=True),
        sa.Column("likelihood", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("impact_score", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "risk_level",
            sa.Enum(*RISK_LEVEL_VALUES, name="risk_level_enum", native_enum=False),
            nullable=False,
            server_default="low",
        ),
        sa.Column(
            "treatment",
            sa.Enum(*TREATMENT_OPTION_VALUES, name="treatment_option_enum", native_enum=False),
            nullable=True,
        ),
        sa.Column("mitigation", sa.Text(), nullable=True),
        sa.Column("residual_risk", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(*SCENARIO_STATUS_VALUES, name="scenario_status_enum", native_enum=False),
            nullable=False,
            server_default="identified",
        ),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "threat_scenario_controls",
        sa.Column(
            "scenario_id",
            sa.Integer(),
            sa.ForeignKey("threat_scenarios.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "control_id",
            sa.Integer(),
            sa.ForeignKey("csa_controls.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.UniqueConstraint("scenario_id", "control_id", name="uq_threat_scenario_control"),
    )


def downgrade() -> None:
    op.drop_table("threat_scenario_controls")
    op.drop_table("threat_scenarios")
    op.drop_table("threat_model_assets")
    op.drop_table("threat_models")
