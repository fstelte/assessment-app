"""initial schema

Revision ID: 20251018_0001
Revises: None
Create Date: 2025-10-18 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251018_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    user_status_enum = sa.Enum("pending", "active", "disabled", name="user_status")
    assessment_status_enum = sa.Enum(
        "assigned",
        "in_progress",
        "submitted",
        "reviewed",
        name="assessment_status",
    )
    assessment_result_enum = sa.Enum("green", "amber", "red", name="assessment_result")
    assessment_dimension_enum = sa.Enum(
        "design",
        "operation",
        "monitoring_improvement",
        name="assessment_dimension",
    )

    user_status_enum.create(bind, checkfirst=True)
    assessment_status_enum.create(bind, checkfirst=True)
    assessment_result_enum.create(bind, checkfirst=True)
    assessment_dimension_enum.create(bind, checkfirst=True)

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=120), nullable=True),
        sa.Column("last_name", sa.String(length=120), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("status", user_status_enum, nullable=False),
        sa.Column("is_service_account", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("theme_preference", sa.String(length=20), nullable=False, server_default="dark"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    op.create_table(
        "controls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("identifier", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("section", sa.String(length=120), nullable=True),
        sa.Column("domain", sa.String(length=120), nullable=True),
        sa.Column("category", sa.String(length=120), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identifier"),
    )
    op.create_index("ix_controls_identifier", "controls", ["identifier"], unique=False)

    op.create_table(
        "audit_trails",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_entity", "audit_trails", ["entity_type", "entity_id"], unique=False)
    op.create_index("ix_audit_user", "audit_trails", ["user_id"], unique=False)

    op.create_table(
        "assessment_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("control_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("question_set", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["control_id"], ["controls.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("control_id", "version", name="uq_template_control_version"),
    )

    op.create_table(
        "mfa_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("secret", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("backup_codes", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )

    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
    sa.Column("status", assessment_status_enum, nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    sa.Column("design_rating", assessment_result_enum, nullable=True),
    sa.Column("operation_rating", assessment_result_enum.copy(), nullable=True),
    sa.Column("monitoring_rating", assessment_result_enum.copy(), nullable=True),
        sa.Column("overall_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["template_id"], ["assessment_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assessments_status", "assessments", ["status"], unique=False)

    op.create_table(
        "assessment_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("assignee_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by_id", sa.Integer(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["assigned_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_id", "assignee_id", name="uq_assignment_assessment_assignee"),
    )

    op.create_table(
        "assessment_responses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
    sa.Column("dimension", assessment_dimension_enum, nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
    sa.Column("rating", assessment_result_enum.copy(), nullable=True),
        sa.Column("evidence_uri", sa.String(length=255), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("responder_id", sa.Integer(), nullable=True),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["responder_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_responses_assessment_dimension",
        "assessment_responses",
        ["assessment_id", "dimension"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_responses_assessment_dimension", table_name="assessment_responses")
    op.drop_table("assessment_responses")
    op.drop_table("assessment_assignments")
    op.drop_index("ix_assessments_status", table_name="assessments")
    op.drop_table("assessments")
    op.drop_table("user_roles")
    op.drop_table("mfa_settings")
    op.drop_table("assessment_templates")
    op.drop_index("ix_audit_user", table_name="audit_trails")
    op.drop_index("ix_audit_entity", table_name="audit_trails")
    op.drop_table("audit_trails")
    op.drop_index("ix_controls_identifier", table_name="controls")
    op.drop_table("controls")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("roles")

    assessment_dimension_enum = sa.Enum(
        "design",
        "operation",
        "monitoring_improvement",
        name="assessment_dimension",
    )
    assessment_result_enum = sa.Enum("green", "amber", "red", name="assessment_result")
    assessment_status_enum = sa.Enum(
        "assigned",
        "in_progress",
        "submitted",
        "reviewed",
        name="assessment_status",
    )
    user_status_enum = sa.Enum("pending", "active", "disabled", name="user_status")

    assessment_dimension_enum.drop(bind, checkfirst=True)
    assessment_result_enum.drop(bind, checkfirst=True)
    assessment_status_enum.drop(bind, checkfirst=True)
    user_status_enum.drop(bind, checkfirst=True)
