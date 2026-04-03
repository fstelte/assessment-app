"""Re-add FIPS rating columns to ssp_plans

Revision ID: 20260403_0003
Revises: 20260403_0002
Create Date: 2026-04-03 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260403_0003"
down_revision = "20260403_0002"
branch_labels = None
depends_on = None

FIPS_RATING_VALUES = ("not_set", "low", "moderate", "high")


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    if not _column_exists("ssp_plans", "fips_confidentiality"):
        op.add_column(
            "ssp_plans",
            sa.Column(
                "fips_confidentiality",
                sa.Enum(*FIPS_RATING_VALUES, name="ssp_fips_conf", native_enum=False),
                nullable=False,
                server_default="not_set",
            ),
        )
    if not _column_exists("ssp_plans", "fips_integrity"):
        op.add_column(
            "ssp_plans",
            sa.Column(
                "fips_integrity",
                sa.Enum(*FIPS_RATING_VALUES, name="ssp_fips_integ", native_enum=False),
                nullable=False,
                server_default="not_set",
            ),
        )
    if not _column_exists("ssp_plans", "fips_availability"):
        op.add_column(
            "ssp_plans",
            sa.Column(
                "fips_availability",
                sa.Enum(*FIPS_RATING_VALUES, name="ssp_fips_avail", native_enum=False),
                nullable=False,
                server_default="not_set",
            ),
        )


def downgrade() -> None:
    op.drop_column("ssp_plans", "fips_availability")
    op.drop_column("ssp_plans", "fips_integrity")
    op.drop_column("ssp_plans", "fips_confidentiality")
