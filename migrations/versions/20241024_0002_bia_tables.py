"""Create BIA domain tables

Revision ID: 20241024_0002
Revises: 20241024_0001
Create Date: 2025-10-24 14:58:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20241024_0002"
down_revision = "20241024_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    enum_values = "'No AI','Unacceptable risk','High risk','Limited risk','Minimal risk'"
    false_default = sa.text("false") if bind.dialect.name == "postgresql" else sa.text("0")
    if bind.dialect.name == "postgresql":
        op.execute(
            "DO $$\n"
            "BEGIN\n"
            "    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'bia_ai_category') THEN\n"
            f"        CREATE TYPE bia_ai_category AS ENUM ({enum_values});\n"
            "    END IF;\n"
            "END\n"
            "$$;"
        )
        bia_ai_enum = postgresql.ENUM(
            "No AI",
            "Unacceptable risk",
            "High risk",
            "Limited risk",
            "Minimal risk",
            name="bia_ai_category",
            create_type=False,
        )
    else:
        bia_ai_enum = sa.Enum(
            "No AI",
            "Unacceptable risk",
            "High risk",
            "Limited risk",
            "Minimal risk",
            name="bia_ai_category",
        )
        bia_ai_enum.create(bind, checkfirst=True)
        bia_ai_enum = sa.Enum(
            "No AI",
            "Unacceptable risk",
            "High risk",
            "Limited risk",
            "Minimal risk",
            name="bia_ai_category",
            create_type=False,
        )

    op.create_table(
        "bia_context_scope",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("responsible", sa.Text(), nullable=True),
        sa.Column("coordinator", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("last_update", sa.Date(), nullable=True),
        sa.Column("service_description", sa.Text(), nullable=True),
        sa.Column("knowledge", sa.Text(), nullable=True),
        sa.Column("interfaces", sa.Text(), nullable=True),
        sa.Column("mission_critical", sa.Text(), nullable=True),
        sa.Column("support_contracts", sa.Text(), nullable=True),
        sa.Column("security_supplier", sa.Text(), nullable=True),
        sa.Column("user_amount", sa.Integer(), nullable=True),
        sa.Column("scope_description", sa.Text(), nullable=True),
    sa.Column("risk_assessment_human", sa.Boolean(), nullable=False, server_default=false_default),
    sa.Column("risk_assessment_process", sa.Boolean(), nullable=False, server_default=false_default),
    sa.Column("risk_assessment_technological", sa.Boolean(), nullable=False, server_default=false_default),
    sa.Column("ai_model", sa.Boolean(), nullable=False, server_default=false_default),
        sa.Column("project_leader", sa.Text(), nullable=True),
        sa.Column("risk_owner", sa.Text(), nullable=True),
        sa.Column("product_owner", sa.Text(), nullable=True),
        sa.Column("technical_administrator", sa.Text(), nullable=True),
        sa.Column("security_manager", sa.Text(), nullable=True),
        sa.Column("incident_contact", sa.Text(), nullable=True),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )

    op.create_table(
        "bia_components",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("info_type", sa.Text(), nullable=True),
        sa.Column("info_owner", sa.Text(), nullable=True),
        sa.Column("user_type", sa.Text(), nullable=True),
        sa.Column("process_dependencies", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("context_scope_id", sa.Integer(), sa.ForeignKey("bia_context_scope.id", ondelete="CASCADE"), nullable=False),
    )

    op.create_table(
        "bia_availability_requirements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("component_id", sa.Integer(), sa.ForeignKey("bia_components.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mtd", sa.Text(), nullable=True),
        sa.Column("rto", sa.Text(), nullable=True),
        sa.Column("rpo", sa.Text(), nullable=True),
        sa.Column("masl", sa.Text(), nullable=True),
    )

    op.create_table(
        "bia_consequences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("component_id", sa.Integer(), sa.ForeignKey("bia_components.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consequence_category", sa.Text(), nullable=True),
        sa.Column("security_property", sa.Text(), nullable=True),
        sa.Column("consequence_worstcase", sa.Text(), nullable=True),
        sa.Column("justification_worstcase", sa.Text(), nullable=True),
        sa.Column("consequence_realisticcase", sa.Text(), nullable=True),
        sa.Column("justification_realisticcase", sa.Text(), nullable=True),
    )

    op.create_table(
        "bia_ai_identificatie",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("component_id", sa.Integer(), sa.ForeignKey("bia_components.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", bia_ai_enum, nullable=False, server_default="No AI"),
        sa.Column("motivatie", sa.Text(), nullable=True),
    )

    op.create_table(
        "bia_summary",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("context_scope_id", sa.Integer(), sa.ForeignKey("bia_context_scope.id", ondelete="CASCADE"), nullable=True, unique=True),
    )


def downgrade() -> None:
    op.drop_table("bia_summary")
    op.drop_table("bia_ai_identificatie")
    op.drop_table("bia_consequences")
    op.drop_table("bia_availability_requirements")
    op.drop_table("bia_components")
    op.drop_table("bia_context_scope")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS bia_ai_category")
    else:
        sa.Enum(name="bia_ai_category").drop(bind, checkfirst=True)
