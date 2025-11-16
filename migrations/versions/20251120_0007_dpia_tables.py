"""Add DPIA tables

Revision ID: 20251120_0007
Revises: 20251115_0006
Create Date: 2025-11-16 10:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20251120_0007"
down_revision = "20251115_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'dpia_assessment_status'
                ) THEN
                    CREATE TYPE dpia_assessment_status AS ENUM (
                        'in_progress',
                        'submitted',
                        'archived'
                    );
                END IF;
            END $$;
            """
        )
    )
    status_enum = postgresql.ENUM(
        "in_progress",
        "submitted",
        "archived",
        name="dpia_assessment_status",
        create_type=False,
    )

    op.create_table(
        "dpia_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("project_lead", sa.String(length=255), nullable=True),
        sa.Column("responsible_name", sa.String(length=255), nullable=True),
        sa.Column("status", status_enum, nullable=False, server_default="in_progress"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("component_id", sa.Integer(), sa.ForeignKey("bia_components.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dpia_assessments_component_id", "dpia_assessments", ["component_id"])
    op.create_index("ix_dpia_assessments_created_by_id", "dpia_assessments", ["created_by_id"])

    op.create_table(
        "dpia_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("help_text", sa.Text(), nullable=True),
        sa.Column("question_type", sa.String(length=50), nullable=False, server_default="text"),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "dpia_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("dpia_assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("dpia_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dpia_answers_assessment_id", "dpia_answers", ["assessment_id"])
    op.create_index("ix_dpia_answers_question_id", "dpia_answers", ["question_id"])

    op.create_table(
        "dpia_risks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("risk_type", sa.String(length=50), nullable=False),
        sa.Column("likelihood", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("impact", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("dpia_assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dpia_risks_assessment_id", "dpia_risks", ["assessment_id"])

    op.create_table(
        "dpia_measures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("effect_likelihood", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("effect_impact", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("dpia_assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("risk_id", sa.Integer(), sa.ForeignKey("dpia_risks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dpia_measures_assessment_id", "dpia_measures", ["assessment_id"])
    op.create_index("ix_dpia_measures_risk_id", "dpia_measures", ["risk_id"])


def downgrade() -> None:
    op.drop_index("ix_dpia_measures_risk_id", table_name="dpia_measures")
    op.drop_index("ix_dpia_measures_assessment_id", table_name="dpia_measures")
    op.drop_table("dpia_measures")

    op.drop_index("ix_dpia_risks_assessment_id", table_name="dpia_risks")
    op.drop_table("dpia_risks")

    op.drop_index("ix_dpia_answers_question_id", table_name="dpia_answers")
    op.drop_index("ix_dpia_answers_assessment_id", table_name="dpia_answers")
    op.drop_table("dpia_answers")

    op.drop_table("dpia_questions")

    op.drop_index("ix_dpia_assessments_created_by_id", table_name="dpia_assessments")
    op.drop_index("ix_dpia_assessments_component_id", table_name="dpia_assessments")
    op.drop_table("dpia_assessments")

    status_enum = postgresql.ENUM(
        "in_progress",
        "submitted",
        "archived",
        name="dpia_assessment_status",
    )
    status_enum.drop(op.get_bind(), checkfirst=True)