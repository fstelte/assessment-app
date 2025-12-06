"""Introduce risk management tables

Revision ID: 20251205_0012
Revises: 20251124_0011
Create Date: 2025-12-05 09:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251205_0012"
down_revision = "20251124_0011"
branch_labels = None
depends_on = None


RISK_IMPACT_VALUES = ("insignificant", "minor", "moderate", "major", "catastrophic")
RISK_CHANCE_VALUES = ("rare", "unlikely", "possible", "likely", "almost_certain")
RISK_TREATMENT_VALUES = ("accept", "avoid", "mitigate", "transfer")
RISK_IMPACT_AREA_VALUES = (
    "operational",
    "financial",
    "regulatory",
    "human_safety",
    "privacy",
)
RISK_SEVERITY_VALUES = ("low", "moderate", "high", "critical")
DEFAULT_THRESHOLDS = (
    ("low", 1, 5),
    ("moderate", 6, 10),
    ("high", 11, 17),
    ("critical", 18, 25),
)


def upgrade() -> None:
    risk_items = op.create_table(
        "risk_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("discovered_on", sa.Date(), server_default=sa.func.current_date(), nullable=False),
        sa.Column(
            "impact",
            sa.Enum(*RISK_IMPACT_VALUES, name="risk_impact", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "chance",
            sa.Enum(*RISK_CHANCE_VALUES, name="risk_chance", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "treatment",
            sa.Enum(*RISK_TREATMENT_VALUES, name="risk_treatment", native_enum=False),
            nullable=False,
        ),
        sa.Column("treatment_plan", sa.Text(), nullable=True),
        sa.Column("treatment_due_date", sa.Date(), nullable=True),
        sa.Column("treatment_owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("csa_control_id", sa.Integer(), sa.ForeignKey("csa_controls.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "treatment != 'mitigate' OR csa_control_id IS NOT NULL",
            name="ck_risk_control_required_for_mitigate",
        ),
    )

    op.create_table(
        "risk_component_links",
        sa.Column("risk_id", sa.Integer(), sa.ForeignKey("risk_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "component_id",
            sa.Integer(),
            sa.ForeignKey("bia_components.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("risk_id", "component_id", name="pk_risk_component_links"),
        sa.UniqueConstraint("risk_id", "component_id", name="uq_risk_component_link"),
    )

    op.create_table(
        "risk_impact_areas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("risk_id", sa.Integer(), sa.ForeignKey("risk_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "area",
            sa.Enum(*RISK_IMPACT_AREA_VALUES, name="risk_impact_area", native_enum=False),
            nullable=False,
        ),
        sa.UniqueConstraint("risk_id", "area", name="uq_risk_impact_area"),
    )

    op.create_table(
        "risk_severity_thresholds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "severity",
            sa.Enum(*RISK_SEVERITY_VALUES, name="risk_severity", native_enum=False),
            nullable=False,
        ),
        sa.Column("min_score", sa.Integer(), nullable=False),
        sa.Column("max_score", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("severity", name="uq_risk_threshold_severity"),
        sa.CheckConstraint("min_score >= 0", name="ck_risk_threshold_min_non_negative"),
        sa.CheckConstraint("max_score >= min_score", name="ck_risk_threshold_bounds"),
    )

    threshold_table = sa.table(
        "risk_severity_thresholds",
        sa.column("severity", sa.String(length=16)),
        sa.column("min_score", sa.Integer()),
        sa.column("max_score", sa.Integer()),
    )
    op.bulk_insert(
        threshold_table,
        [
            {"severity": severity, "min_score": min_score, "max_score": max_score}
            for severity, min_score, max_score in DEFAULT_THRESHOLDS
        ],
    )


def downgrade() -> None:
    op.drop_table("risk_component_links")
    op.drop_table("risk_impact_areas")
    op.drop_table("risk_severity_thresholds")
    op.drop_table("risk_items")
