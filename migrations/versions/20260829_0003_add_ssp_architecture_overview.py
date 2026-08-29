"""Add ssp_architecture_overview_versions table

Revision ID: 20260829_0003
Revises: 20260829_0002
Create Date: 2026-08-29 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260829_0003"
down_revision = "20260829_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ssp_architecture_overview_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ssp_id",
            sa.Integer(),
            sa.ForeignKey("ssp_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("image_data", sa.LargeBinary(), nullable=False),
        sa.Column("mime_type", sa.String(20), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "uploaded_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("ssp_id", "version_number", name="uq_ssp_architecture_overview_version"),
    )


def downgrade() -> None:
    op.drop_table("ssp_architecture_overview_versions")
