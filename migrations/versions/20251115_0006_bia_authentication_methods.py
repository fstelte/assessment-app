"""Add authentication method lookup for BIA components

Revision ID: 20251115_0006
Revises: 20251106_0005
Create Date: 2025-11-15 10:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251115_0006"
down_revision = "20251106_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bia_authentication_methods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("label_en", sa.String(length=255), nullable=False),
        sa.Column("label_nl", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("slug", name="uq_bia_authentication_methods_slug"),
    )

    op.add_column(
        "bia_components",
        sa.Column("authentication_method_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_bia_components_authentication_method_id",
        "bia_components",
        ["authentication_method_id"],
    )
    op.create_foreign_key(
        "fk_bia_components_authentication_method_id",
        "bia_components",
        "bia_authentication_methods",
        ["authentication_method_id"],
        ["id"],
        ondelete="SET NULL",
    )

    authentication_methods = sa.table(
        "bia_authentication_methods",
        sa.column("slug", sa.String(length=64)),
        sa.column("label_en", sa.String(length=255)),
        sa.column("label_nl", sa.String(length=255)),
        sa.column("is_active", sa.Boolean()),
    )

    op.bulk_insert(
        authentication_methods,
        [
            {
                "slug": "application-integrated",
                "label_en": "Application integrated",
                "label_nl": "Applicatie-geïntegreerd",
                "is_active": True,
            },
            {
                "slug": "centrally-managed",
                "label_en": "Centrally managed (IdP)",
                "label_nl": "Centraal beheerd (IdP)",
                "is_active": True,
            },
        ],
    )

    op.alter_column(
        "bia_authentication_methods",
        "is_active",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_constraint("fk_bia_components_authentication_method_id", "bia_components", type_="foreignkey")
    op.drop_index("ix_bia_components_authentication_method_id", table_name="bia_components")
    op.drop_column("bia_components", "authentication_method_id")

    op.drop_table("bia_authentication_methods")
