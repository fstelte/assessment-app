"""Create component environment mapping table

Revision ID: 20251124_0011
Revises: 20251123_0010
Create Date: 2025-11-21 10:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251124_0011"
down_revision = "20251123_0010"
branch_labels = None
depends_on = None


_ENVIRONMENT_TYPE_ENUM = "bia_environment_type"
_ENVIRONMENT_VALUES = ("development", "test", "acceptance", "production")

environment_type_enum = sa.Enum(*_ENVIRONMENT_VALUES, name=_ENVIRONMENT_TYPE_ENUM)


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text(f"DROP TYPE IF EXISTS {_ENVIRONMENT_TYPE_ENUM} CASCADE"))

    op.create_table(
        "bia_component_environments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("component_id", sa.Integer(), sa.ForeignKey("bia_components.id", ondelete="CASCADE"), nullable=False),
        sa.Column("environment_type", environment_type_enum, nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("authentication_method_id", sa.Integer(), sa.ForeignKey("bia_authentication_methods.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("component_id", "environment_type", name="uq_component_environment"),
    )
    op.create_index(
        "ix_bia_component_environments_component",
        "bia_component_environments",
        ["component_id"],
    )
    op.create_index(
        "ix_bia_component_environments_environment",
        "bia_component_environments",
        ["environment_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_bia_component_environments_environment", table_name="bia_component_environments")
    op.drop_index("ix_bia_component_environments_component", table_name="bia_component_environments")
    op.drop_table("bia_component_environments")

    op.execute(sa.text(f"DROP TYPE IF EXISTS {_ENVIRONMENT_TYPE_ENUM} CASCADE"))
