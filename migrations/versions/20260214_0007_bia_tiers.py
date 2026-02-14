"""Add BIA tiers

Revision ID: 20260214_0007
Revises: 20260214_0006
Create Date: 2026-02-14 13:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision = '20260214_0007'
down_revision = '20260214_0006'
branch_labels = None
depends_on = None


def upgrade():
    # Create bia_tiers table
    op.create_table(
        'bia_tiers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('name_en', sa.String(length=255), nullable=False),
        sa.Column('name_nl', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('level', name='uq_bia_tiers_level')
    )

    # Add tier_id to bia_context_scope
    op.add_column('bia_context_scope', sa.Column('tier_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_bia_context_scope_tier_id',
        'bia_context_scope',
        'bia_tiers',
        ['tier_id'],
        ['id']
    )

    # Data progression
    bia_tiers_table = table(
        'bia_tiers',
        column('id', sa.Integer),
        column('level', sa.Integer),
        column('name_en', sa.String),
        column('name_nl', sa.String)
    )

    op.bulk_insert(
        bia_tiers_table,
        [
            {'id': 1, 'level': 0, 'name_en': 'Critical Infrastructure', 'name_nl': 'Kritieke Infrastructuur'},
            {'id': 2, 'level': 1, 'name_en': 'Mission Critical', 'name_nl': 'Bedrijfskritisch'},
            {'id': 3, 'level': 2, 'name_en': 'Business Critical', 'name_nl': 'Zakelijk Kritisch'},
            {'id': 4, 'level': 3, 'name_en': 'Important', 'name_nl': 'Belangrijk'},
            {'id': 5, 'level': 4, 'name_en': 'Deferrable', 'name_nl': 'Uitstelbaar'},
        ]
    )


def downgrade():
    op.drop_constraint('fk_bia_context_scope_tier_id', 'bia_context_scope', type_='foreignkey')
    op.drop_column('bia_context_scope', 'tier_id')
    op.drop_table('bia_tiers')
