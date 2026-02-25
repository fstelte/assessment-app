"""Add archive support to BIA context scope

Revision ID: 20260225_0001
Revises: 20260224_0001
Create Date: 2026-02-25 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260225_0001'
down_revision = '20260224_0001'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('bia_context_scope', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_archived', sa.Boolean(), server_default='false', nullable=False))
        batch_op.add_column(sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    with op.batch_alter_table('bia_context_scope', schema=None) as batch_op:
        batch_op.drop_column('archived_at')
        batch_op.drop_column('is_archived')
