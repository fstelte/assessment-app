"""Add threat library, product, and mitigation models

Revision ID: 20260322_0001
Revises: 20260317_0002
Create Date: 2026-03-22 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260322_0001"
down_revision = "20260317_0002"
branch_labels = None
depends_on = None

MITIGATION_STATUS_VALUES = ("proposed", "in_progress", "implemented", "verified")


def upgrade() -> None:
    # ── New tables ────────────────────────────────────────────────────────────

    op.create_table(
        "threat_frameworks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        "threat_library_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "framework_id",
            sa.Integer(),
            sa.ForeignKey("threat_frameworks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("suggested_mitigation", sa.Text(), nullable=True),
        sa.Column("stride_hint", sa.String(50), nullable=True),
        sa.Column("is_custom", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
        "threat_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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

    # ── Add columns to existing tables ───────────────────────────────────────

    with op.batch_alter_table("threat_models") as batch_op:
        batch_op.add_column(
            sa.Column(
                "product_id",
                sa.Integer(),
                sa.ForeignKey("threat_products.id", ondelete="SET NULL"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("suggested_frameworks", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "dpia_id",
                sa.Integer(),
                sa.ForeignKey("dpia_assessments.id", ondelete="SET NULL"),
                nullable=True,
            )
        )

    with op.batch_alter_table("threat_scenarios") as batch_op:
        batch_op.add_column(
            sa.Column(
                "library_entry_id",
                sa.Integer(),
                sa.ForeignKey("threat_library_entries.id", ondelete="SET NULL"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "methodology",
                sa.String(50),
                nullable=False,
                server_default="STRIDE",
            )
        )
        batch_op.add_column(
            sa.Column("pasta_stage", sa.String(100), nullable=True)
        )

    # ── Mitigation actions table (depends on threat_scenarios and threat_library_entries) ──

    op.create_table(
        "threat_mitigation_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scenario_id",
            sa.Integer(),
            sa.ForeignKey("threat_scenarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "library_entry_id",
            sa.Integer(),
            sa.ForeignKey("threat_library_entries.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(*MITIGATION_STATUS_VALUES, name="mitigation_status_enum", native_enum=False),
            nullable=False,
            server_default="proposed",
        ),
        sa.Column(
            "assigned_to_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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


def downgrade() -> None:
    op.drop_table("threat_mitigation_actions")

    with op.batch_alter_table("threat_scenarios") as batch_op:
        batch_op.drop_column("pasta_stage")
        batch_op.drop_column("methodology")
        batch_op.drop_column("library_entry_id")

    with op.batch_alter_table("threat_models") as batch_op:
        batch_op.drop_column("dpia_id")
        batch_op.drop_column("suggested_frameworks")
        batch_op.drop_column("product_id")

    op.drop_table("threat_library_entries")
    op.drop_table("threat_frameworks")
    op.drop_table("threat_products")
