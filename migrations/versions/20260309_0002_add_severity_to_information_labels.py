"""Add severity column to bia_information_labels

Revision ID: 20260309_0002
Revises: 20260309_0001
Create Date: 2026-03-09 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260309_0002'
down_revision = '20260309_0001'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('bia_information_labels', schema=None) as batch_op:
        batch_op.add_column(sa.Column('severity', sa.Integer(), nullable=False, server_default='0'))

    # Set severity for the default seeded labels
    op.execute("""
        UPDATE bia_information_labels SET severity = 1 WHERE slug = 'public';
        UPDATE bia_information_labels SET severity = 2 WHERE slug = 'internal';
        UPDATE bia_information_labels SET severity = 3 WHERE slug = 'confidential';
        UPDATE bia_information_labels SET severity = 4 WHERE slug = 'restricted';
    """)


def downgrade():
    with op.batch_alter_table('bia_information_labels', schema=None) as batch_op:
        batch_op.drop_column('severity')
