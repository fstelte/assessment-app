"""Add structured scoring and tracking to maturity answers

Revision ID: 20260224_0001
Revises: 20260214_0007
Create Date: 2026-02-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260224_0001'
down_revision = '20260214_0007'
branch_labels = None
depends_on = None


def upgrade():
    # Create the MaturityScore enum type (if using Postgres/supporting backend)
    # Define enum values
    maturity_score_enum = sa.Enum(
        'NOT_APPLICABLE', 
        'NOT_AVAILABLE', 
        'PARTIALLY_IMPLEMENTED', 
        'IMPLEMENTED_NEEDS_IMPROVEMENT', 
        'BEST_PRACTICE', 
        name='maturityscore'
    )
    
    # Explicitly create the enum type
    maturity_score_enum.create(op.get_bind(), checkfirst=True)

    # Add columns to maturity_answers
    with op.batch_alter_table('maturity_answers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('score', maturity_score_enum, nullable=True))
        batch_op.add_column(sa.Column('jira_ticket', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('evidence_url', sa.String(length=1024), nullable=True))


def downgrade():
    with op.batch_alter_table('maturity_answers', schema=None) as batch_op:
        batch_op.drop_column('evidence_url')
        batch_op.drop_column('description')
        batch_op.drop_column('jira_ticket')
        batch_op.drop_column('score')
    
    # Drop the enum type if using Postgres
    # op.execute("DROP TYPE maturityscore")
    maturity_score_enum = sa.Enum(
        'NOT_APPLICABLE', 
        'NOT_AVAILABLE', 
        'PARTIALLY_IMPLEMENTED', 
        'IMPLEMENTED_NEEDS_IMPROVEMENT', 
        'BEST_PRACTICE', 
        name='maturityscore'
    )
    maturity_score_enum.drop(op.get_bind(), checkfirst=True)
