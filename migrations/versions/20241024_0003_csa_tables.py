"""Create CSA domain tables

Revision ID: 20241024_0003
Revises: 20241024_0002
Create Date: 2025-10-24 15:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20241024_0003"
down_revision = "20241024_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    assessment_status = sa.Enum(
        "assigned",
        "in_progress",
        "submitted",
        "reviewed",
        name="csa_assessment_status",
    )
    assessment_status.create(op.get_bind(), checkfirst=True)

    assessment_result = sa.Enum(
        "green",
        "amber",
        "red",
        name="csa_assessment_result",
    )
    assessment_result.create(op.get_bind(), checkfirst=True)

    assessment_dimension = sa.Enum(
        "design",
        "operation",
        "monitoring_improvement",
        name="csa_assessment_dimension",
    )
    assessment_dimension.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "csa_controls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("section", sa.String(length=120), nullable=True),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("domain", name="uq_csa_control_domain"),
    )
    op.create_index("ix_csa_controls_domain", "csa_controls", ["domain"], unique=False)

    op.create_table(
        "csa_assessment_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("control_id", sa.Integer(), sa.ForeignKey("csa_controls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False, server_default="1.0"),
        sa.Column("question_set", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("control_id", "version", name="uq_csa_template_control_version"),
    )

    op.create_table(
        "csa_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("csa_assessment_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", assessment_status, nullable=False, server_default="assigned"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("design_rating", assessment_result, nullable=True),
    sa.Column("operation_rating", assessment_result, nullable=True),
    sa.Column("monitoring_rating", assessment_result, nullable=True),
        sa.Column("overall_comment", sa.Text(), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    op.create_table(
        "csa_assessment_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("csa_assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignee_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("assessment_id", "assignee_id", name="uq_csa_assignment_assessment_assignee"),
    )

    op.create_table(
        "csa_assessment_responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("csa_assessments.id", ondelete="CASCADE"), nullable=False),
    sa.Column("dimension", assessment_dimension, nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
    sa.Column("rating", assessment_result, nullable=True),
        sa.Column("evidence_uri", sa.String(length=255), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("responder_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index(
        "ix_csa_responses_assessment_dimension",
        "csa_assessment_responses",
        ["assessment_id", "dimension"],
        unique=False,
    )

    op.create_table(
        "csa_audit_trails",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_csa_audit_entity", "csa_audit_trails", ["entity_type", "entity_id"], unique=False)
    op.create_index("ix_csa_audit_user", "csa_audit_trails", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_csa_audit_user", table_name="csa_audit_trails")
    op.drop_index("ix_csa_audit_entity", table_name="csa_audit_trails")
    op.drop_table("csa_audit_trails")

    op.drop_index("ix_csa_responses_assessment_dimension", table_name="csa_assessment_responses")
    op.drop_table("csa_assessment_responses")

    op.drop_table("csa_assessment_assignments")
    op.drop_table("csa_assessments")
    op.drop_table("csa_assessment_templates")
    op.drop_index("ix_csa_controls_domain", table_name="csa_controls")
    op.drop_table("csa_controls")

    sa.Enum(name="csa_assessment_dimension").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="csa_assessment_result").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="csa_assessment_status").drop(op.get_bind(), checkfirst=True)
