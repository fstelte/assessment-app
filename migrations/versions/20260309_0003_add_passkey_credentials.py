"""Add passkey_credentials table for WebAuthn passkey support

Revision ID: 20260309_0003
Revises: 20260309_0002
Create Date: 2026-03-09 00:00:02.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260309_0003'
down_revision = '20260309_0002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'passkey_credentials',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('credential_id', sa.LargeBinary(length=1024), nullable=False),
        sa.Column('public_key', sa.LargeBinary(length=2048), nullable=False),
        sa.Column('sign_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('transports', sa.JSON(), nullable=True),
        sa.Column('aaguid', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False, server_default='Passkey'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('credential_id', name='uq_passkey_credentials_credential_id'),
    )


def downgrade():
    op.drop_table('passkey_credentials')
