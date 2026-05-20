"""Add plural threat-scenario assignments and risk ticket links

Revision ID: 20260520_0001
Revises: 20260417_0001
Create Date: 2026-05-20 00:00:00.000000

Changes:
- Create threat_scenario_assets association table
- Create threat_scenario_stride_categories association table
- Create risk_ticket_links child table
- Backfill existing single-value records from scalar columns
  (threat_scenarios.asset_id, threat_scenarios.stride_category,
   risk_items.ticket_url) into the new tables
- Scalar columns are retained for now; application code migrates to
  reading from the new relationships.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260520_0001"
down_revision = "20260417_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. threat_scenario_assets
    # ------------------------------------------------------------------
    op.create_table(
        "threat_scenario_assets",
        sa.Column("scenario_id", sa.Integer, sa.ForeignKey("threat_scenarios.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("threat_model_assets.id", ondelete="CASCADE"), primary_key=True),
        sa.UniqueConstraint("scenario_id", "asset_id", name="uq_threat_scenario_asset"),
    )
    op.create_index("ix_threat_scenario_assets_scenario_id", "threat_scenario_assets", ["scenario_id"])

    # ------------------------------------------------------------------
    # 2. threat_scenario_stride_categories
    # ------------------------------------------------------------------
    op.create_table(
        "threat_scenario_stride_categories",
        sa.Column("scenario_id", sa.Integer, sa.ForeignKey("threat_scenarios.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("stride_category", sa.String(50), nullable=False, primary_key=True),
        sa.UniqueConstraint("scenario_id", "stride_category", name="uq_threat_scenario_stride"),
    )
    op.create_index(
        "ix_threat_scenario_stride_categories_scenario_id",
        "threat_scenario_stride_categories",
        ["scenario_id"],
    )

    # ------------------------------------------------------------------
    # 3. risk_ticket_links
    # ------------------------------------------------------------------
    op.create_table(
        "risk_ticket_links",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("risk_id", sa.Integer, sa.ForeignKey("risk_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, default=0),
        sa.UniqueConstraint("risk_id", "label", "url", name="uq_risk_ticket_link"),
    )
    op.create_index("ix_risk_ticket_links_risk_id", "risk_ticket_links", ["risk_id"])

    # ------------------------------------------------------------------
    # 4. Backfill existing data
    # ------------------------------------------------------------------
    bind = op.get_bind()

    # Backfill threat_scenario_assets from threat_scenarios.asset_id
    bind.execute(sa.text("""
        INSERT INTO threat_scenario_assets (scenario_id, asset_id)
        SELECT id, asset_id
        FROM threat_scenarios
        WHERE asset_id IS NOT NULL
        ON CONFLICT DO NOTHING
    """))

    # Backfill threat_scenario_stride_categories from threat_scenarios.stride_category
    bind.execute(sa.text("""
        INSERT INTO threat_scenario_stride_categories (scenario_id, stride_category)
        SELECT id, stride_category
        FROM threat_scenarios
        WHERE stride_category IS NOT NULL
        ON CONFLICT DO NOTHING
    """))

    # Backfill risk_ticket_links from risk_items.ticket_url
    bind.execute(sa.text("""
        INSERT INTO risk_ticket_links (risk_id, label, url, sort_order)
        SELECT id, 'Ticket', ticket_url, 0
        FROM risk_items
        WHERE ticket_url IS NOT NULL AND ticket_url != ''
        ON CONFLICT DO NOTHING
    """))


def downgrade() -> None:
    op.drop_index("ix_risk_ticket_links_risk_id", table_name="risk_ticket_links")
    op.drop_table("risk_ticket_links")

    op.drop_index(
        "ix_threat_scenario_stride_categories_scenario_id",
        table_name="threat_scenario_stride_categories",
    )
    op.drop_table("threat_scenario_stride_categories")

    op.drop_index("ix_threat_scenario_assets_scenario_id", table_name="threat_scenario_assets")
    op.drop_table("threat_scenario_assets")
