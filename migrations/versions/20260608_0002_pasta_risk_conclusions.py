"""Add pasta_risk_conclusions table with legacy backfill

Revision ID: 20260608_0002
Revises: 20260608_0001
Create Date: 2026-06-08 00:00:00.000000

Changes:
- Create pasta_risk_conclusions table (structured stage-seven scoring, FR-006/FR-007)
- Backfill existing stage-seven risk_conclusion findings into the new table
  as draft / not_published records, preserving their narrative text intact (T004)
- Legacy risk_conclusion PastaFinding rows are kept; the new table extends them 1:1
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260608_0002"
down_revision = "20260608_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create pasta_risk_conclusions table
    op.create_table(
        "pasta_risk_conclusions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "finding_id",
            sa.Integer,
            sa.ForeignKey("pasta_findings.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("likelihood_score", sa.Integer, nullable=True),
        sa.Column("impact_score", sa.Integer, nullable=True),
        sa.Column("overall_score", sa.Integer, nullable=True),
        sa.Column("treatment", sa.String(20), nullable=True, server_default="mitigate"),
        sa.Column(
            "publication_state",
            sa.String(30),
            nullable=False,
            server_default="not_published",
        ),
        sa.Column(
            "published_risk_id",
            sa.Integer,
            sa.ForeignKey("risk_items.id", ondelete="SET NULL"),
            nullable=True,
            unique=True,
        ),
        sa.Column("last_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_published_by_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("publication_notes", sa.Text, nullable=True),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_pasta_risk_conclusions_finding_id",
        "pasta_risk_conclusions",
        ["finding_id"],
    )
    op.create_index(
        "ix_pasta_risk_conclusions_published_risk_id",
        "pasta_risk_conclusions",
        ["published_risk_id"],
    )

    # 2. Backfill: create a draft not_published PastaRiskConclusion row for every
    #    existing stage-seven risk_conclusion finding so legacy records are preserved
    #    with no data loss.  Scores remain NULL and publication_state = not_published.
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT pf.id
            FROM pasta_findings pf
            JOIN pasta_stage_records psr ON pf.stage_record_id = psr.id
            WHERE psr.stage_code = 'risk_impact_analysis'
              AND pf.finding_type = 'risk_conclusion'
              AND NOT EXISTS (
                  SELECT 1
                  FROM pasta_risk_conclusions prc
                  WHERE prc.finding_id = pf.id
              )
            """
        )
    )
    rows = result.fetchall()
    if rows:
        bind.execute(
            sa.text(
                """
                INSERT INTO pasta_risk_conclusions
                    (finding_id, publication_state, treatment, created_at, updated_at)
                VALUES
                    (:fid, 'not_published', 'mitigate', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            [{"fid": row[0]} for row in rows],
        )


def downgrade() -> None:
    op.drop_index("ix_pasta_risk_conclusions_published_risk_id", "pasta_risk_conclusions")
    op.drop_index("ix_pasta_risk_conclusions_finding_id", "pasta_risk_conclusions")
    op.drop_table("pasta_risk_conclusions")
