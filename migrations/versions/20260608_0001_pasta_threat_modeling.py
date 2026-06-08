"""Add PASTA threat modeling workflow tables and threat_models metadata

Revision ID: 20260608_0001
Revises: 20260520_0001
Create Date: 2026-06-08 00:00:00.000000

Changes:
- Add methodology column to threat_models (default 'STRIDE')
- Add bootstrap_source_model_id self-referential FK on threat_models
- Create pasta_stage_records table
- Create pasta_findings table
- Create pasta_finding_asset_links table
- Create pasta_finding_stride_links table
- Create pasta_finding_scenario_links table

Compatibility notes (T004):
  The existing per-scenario ThreatScenario.methodology and
  ThreatScenario.pasta_stage columns are RETAINED as-is and are not
  removed or repurposed.  They will continue to work for any data that
  was recorded with those fields.  New PASTA analysis uses the model-
  level PastaStageRecord / PastaFinding tables added in this migration.
  A future migration may deprecate and drop the scenario-level fields
  once all consumers have migrated.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260608_0001"
down_revision = "20260520_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Extend threat_models with PASTA metadata columns
    # ------------------------------------------------------------------
    op.add_column(
        "threat_models",
        sa.Column("methodology", sa.String(20), nullable=False, server_default="STRIDE"),
    )
    op.add_column(
        "threat_models",
        sa.Column(
            "bootstrap_source_model_id",
            sa.Integer,
            sa.ForeignKey("threat_models.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_threat_models_methodology",
        "threat_models",
        ["methodology"],
    )

    # ------------------------------------------------------------------
    # 2. pasta_stage_records
    # ------------------------------------------------------------------
    op.create_table(
        "pasta_stage_records",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "threat_model_id",
            sa.Integer,
            sa.ForeignKey("threat_models.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage_code", sa.String(60), nullable=False),
        sa.Column("display_order", sa.Integer, nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="locked"),
        sa.Column("summary", sa.Text),
        sa.Column("completion_notes", sa.Text),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "completed_by_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("last_revalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "threat_model_id",
            "stage_code",
            name="uq_pasta_stage_model_code",
        ),
    )
    op.create_index(
        "ix_pasta_stage_records_threat_model_id",
        "pasta_stage_records",
        ["threat_model_id"],
    )

    # ------------------------------------------------------------------
    # 3. pasta_findings
    # ------------------------------------------------------------------
    op.create_table(
        "pasta_findings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "stage_record_id",
            sa.Integer,
            sa.ForeignKey("pasta_stage_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("finding_type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("evidence", sa.Text),
        sa.Column("priority", sa.String(20), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="current"),
        sa.Column(
            "source_library_entry_id",
            sa.Integer,
            sa.ForeignKey("threat_library_entries.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_by_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_pasta_findings_stage_record_id",
        "pasta_findings",
        ["stage_record_id"],
    )

    # ------------------------------------------------------------------
    # 4. pasta_finding_asset_links
    # ------------------------------------------------------------------
    op.create_table(
        "pasta_finding_asset_links",
        sa.Column(
            "finding_id",
            sa.Integer,
            sa.ForeignKey("pasta_findings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "asset_id",
            sa.Integer,
            sa.ForeignKey("threat_model_assets.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.UniqueConstraint("finding_id", "asset_id", name="uq_pasta_finding_asset"),
    )

    # ------------------------------------------------------------------
    # 5. pasta_finding_stride_links
    # ------------------------------------------------------------------
    op.create_table(
        "pasta_finding_stride_links",
        sa.Column(
            "finding_id",
            sa.Integer,
            sa.ForeignKey("pasta_findings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("stride_category", sa.String(50), nullable=False, primary_key=True),
        sa.UniqueConstraint(
            "finding_id",
            "stride_category",
            name="uq_pasta_finding_stride",
        ),
    )

    # ------------------------------------------------------------------
    # 6. pasta_finding_scenario_links
    # ------------------------------------------------------------------
    op.create_table(
        "pasta_finding_scenario_links",
        sa.Column(
            "finding_id",
            sa.Integer,
            sa.ForeignKey("pasta_findings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "scenario_id",
            sa.Integer,
            sa.ForeignKey("threat_scenarios.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("link_type", sa.String(20), nullable=False, server_default="linked"),
        sa.UniqueConstraint(
            "finding_id",
            "scenario_id",
            name="uq_pasta_finding_scenario",
        ),
    )


def downgrade() -> None:
    op.drop_table("pasta_finding_scenario_links")
    op.drop_table("pasta_finding_stride_links")
    op.drop_table("pasta_finding_asset_links")
    op.drop_table("pasta_findings")
    op.drop_index("ix_pasta_stage_records_threat_model_id", "pasta_stage_records")
    op.drop_table("pasta_stage_records")
    op.drop_index("ix_threat_models_methodology", "threat_models")
    op.drop_column("threat_models", "bootstrap_source_model_id")
    op.drop_column("threat_models", "methodology")
