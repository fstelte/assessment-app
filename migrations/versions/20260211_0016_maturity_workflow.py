"""Maturity workflow and control owner

Revision ID: 20260211_0016
Revises: ec5ce35d1bd0
Create Date: 2026-02-11 08:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260211_0016'
down_revision = 'ec5ce35d1bd0'
branch_labels = None
depends_on = None


def upgrade():
    # csa_controls owner
    with op.batch_alter_table('csa_controls', schema=None) as batch_op:
        batch_op.add_column(sa.Column('owner_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_csa_controls_owner_id', 'users', ['owner_id'], ['id'])

    # assessment status enum
    assessment_status = sa.Enum('UNASSESSED', 'BEING_ASSESSED', 'ASSESSED', name='assessmentstatus')
    assessment_status.create(op.get_bind(), checkfirst=True)

    # maturity_assessments changes
    with op.batch_alter_table('maturity_assessments', schema=None) as batch_op:
        # Add new columns
        batch_op.add_column(sa.Column('status', assessment_status, server_default='UNASSESSED', nullable=False))
        batch_op.add_column(sa.Column('last_updated_by_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('submitted_by_id', sa.Integer(), nullable=True))
        
        # Add foreign keys
        batch_op.create_foreign_key('fk_maturity_assessments_last_updated_by_user', 'users', ['last_updated_by_id'], ['id'])
        batch_op.create_foreign_key('fk_maturity_assessments_submitted_by_user', 'users', ['submitted_by_id'], ['id'])
        
        # Drop old column and constraints
        # Try to drop by standard naming convention. 
        # Note: If this fails due to name mismatch on the server, the constraint name might need to be retrieved or handled dynamically.
        batch_op.drop_constraint('maturity_assessments_assessor_id_fkey', type_='foreignkey')
        batch_op.drop_index('ix_maturity_assessments_assessor_id')
        batch_op.drop_column('assessor_id')


def downgrade():
    with op.batch_alter_table('maturity_assessments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('assessor_id', sa.Integer(), nullable=True)) # Nullable true to prevent downgrade failure
        batch_op.create_foreign_key('maturity_assessments_assessor_id_fkey', 'users', ['assessor_id'], ['id'])
        batch_op.create_index('ix_maturity_assessments_assessor_id', ['assessor_id'])
        
        batch_op.drop_constraint('fk_maturity_assessments_submitted_by_user', type_='foreignkey')
        batch_op.drop_constraint('fk_maturity_assessments_last_updated_by_user', type_='foreignkey')
        batch_op.drop_column('submitted_by_id')
        batch_op.drop_column('last_updated_by_id')
        batch_op.drop_column('status')

    sa.Enum(name='assessmentstatus').drop(op.get_bind(), checkfirst=True)

    with op.batch_alter_table('csa_controls', schema=None) as batch_op:
        batch_op.drop_constraint('fk_csa_controls_owner_id', type_='foreignkey')
        batch_op.drop_column('owner_id')
