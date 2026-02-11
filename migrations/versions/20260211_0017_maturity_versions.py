"""Add maturity versions and update workflow status

Revision ID: 20260211_0017
Revises: 20260211_0016
Create Date: 2026-02-11 09:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260211_0017'
down_revision = '20260211_0016'
branch_labels = None
depends_on = None


def upgrade():
    # Update AssessmentStatus enum
    # Using autocommit block for ALTER TYPE
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE assessmentstatus ADD VALUE IF NOT EXISTS 'SUBMITTED'")
        op.execute("ALTER TYPE assessmentstatus ADD VALUE IF NOT EXISTS 'APPROVED'")

    # Create maturity_assessment_versions table
    op.create_table('maturity_assessment_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('control_id', sa.Integer(), nullable=False),
        sa.Column('approved_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('approved_by_id', sa.Integer(), nullable=True),
        sa.Column('maturity_level', postgresql.ENUM('INITIAL', 'MANAGED', 'DEFINED', 'QUANTITATIVELY_MANAGED', 'OPTIMIZING', name='maturitylevel', create_type=False), nullable=False),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['control_id'], ['csa_controls.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_maturity_assessment_versions_control_id'), 'maturity_assessment_versions', ['control_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_maturity_assessment_versions_control_id'), table_name='maturity_assessment_versions')
    op.drop_table('maturity_assessment_versions')
    
    # Cannot easily remove enum values in Postgres without recreation
