"""Expand DPIA workflow statuses

Revision ID: 20251122_0009
Revises: 20251121_0008
Create Date: 2025-11-16 18:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20251122_0009"
down_revision = "20251121_0008"
branch_labels = None
depends_on = None


OLD_VALUES = ("in_progress", "submitted", "archived")
NEW_VALUES = ("in_progress", "in_review", "finished", "abandoned")


def upgrade() -> None:
    op.execute("ALTER TABLE dpia_assessments ALTER COLUMN status DROP DEFAULT")

    new_enum = postgresql.ENUM(*NEW_VALUES, name="dpia_assessment_status_new")
    new_enum.create(op.get_bind(), checkfirst=True)

    op.execute(
        sa.text(
            """
            ALTER TABLE dpia_assessments
            ALTER COLUMN status TYPE dpia_assessment_status_new
            USING (
                CASE
                    WHEN status::text = 'submitted' THEN 'in_review'
                    WHEN status::text = 'archived' THEN 'abandoned'
                    ELSE status::text
                END
            )::dpia_assessment_status_new
            """
        )
    )

    old_enum = postgresql.ENUM(*OLD_VALUES, name="dpia_assessment_status")
    old_enum.drop(op.get_bind(), checkfirst=True)

    op.execute(sa.text("ALTER TYPE dpia_assessment_status_new RENAME TO dpia_assessment_status"))
    op.execute("ALTER TABLE dpia_assessments ALTER COLUMN status SET DEFAULT 'in_progress'")


def downgrade() -> None:
    op.execute("ALTER TABLE dpia_assessments ALTER COLUMN status DROP DEFAULT")

    old_enum = postgresql.ENUM(*OLD_VALUES, name="dpia_assessment_status_old")
    old_enum.create(op.get_bind(), checkfirst=True)

    op.execute(
        sa.text(
            """
            ALTER TABLE dpia_assessments
            ALTER COLUMN status TYPE dpia_assessment_status_old
            USING (
                CASE
                    WHEN status::text = 'finished' THEN 'submitted'
                    WHEN status::text = 'in_review' THEN 'submitted'
                    WHEN status::text = 'abandoned' THEN 'archived'
                    ELSE status::text
                END
            )::dpia_assessment_status_old
            """
        )
    )

    new_enum = postgresql.ENUM(*NEW_VALUES, name="dpia_assessment_status")
    new_enum.drop(op.get_bind(), checkfirst=True)

    op.execute(sa.text("ALTER TYPE dpia_assessment_status_old RENAME TO dpia_assessment_status"))
    op.execute("ALTER TABLE dpia_assessments ALTER COLUMN status SET DEFAULT 'in_progress'")
