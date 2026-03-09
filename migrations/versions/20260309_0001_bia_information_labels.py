"""Add information labels table and info_label_id to bia_components

Revision ID: 20260309_0001
Revises: 20260225_0001
Create Date: 2026-03-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260309_0001'
down_revision = '20260225_0001'
branch_labels = None
depends_on = None


def upgrade():
    # Create bia_information_labels table
    op.create_table(
        'bia_information_labels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(64), nullable=False),
        sa.Column('label_en', sa.String(255), nullable=False),
        sa.Column('label_nl', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('severity', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', name='uq_bia_information_labels_slug'),
    )

    # Seed default labels
    information_labels = sa.table(
        'bia_information_labels',
        sa.column('slug', sa.String),
        sa.column('label_en', sa.String),
        sa.column('label_nl', sa.String),
        sa.column('is_active', sa.Boolean),
        sa.column('severity', sa.Integer),
    )
    op.bulk_insert(
        information_labels,
        [
            {'slug': 'public', 'label_en': 'Public', 'label_nl': 'Openbaar', 'is_active': True, 'severity': 1},
            {'slug': 'internal', 'label_en': 'Internal', 'label_nl': 'Intern', 'is_active': True, 'severity': 2},
            {'slug': 'confidential', 'label_en': 'Confidential', 'label_nl': 'Vertrouwelijk', 'is_active': True, 'severity': 3},
            {'slug': 'restricted', 'label_en': 'Restricted', 'label_nl': 'Strikt vertrouwelijk', 'is_active': True, 'severity': 4},
        ],
    )

    # Add info_label_id FK column to bia_components
    with op.batch_alter_table('bia_components', schema=None) as batch_op:
        batch_op.add_column(sa.Column('info_label_id', sa.Integer(), nullable=True))
        batch_op.create_index(
            'ix_bia_components_info_label_id',
            ['info_label_id'],
        )
        batch_op.create_foreign_key(
            'fk_bia_components_info_label_id',
            'bia_information_labels',
            ['info_label_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade():
    with op.batch_alter_table('bia_components', schema=None) as batch_op:
        batch_op.drop_constraint('fk_bia_components_info_label_id', type_='foreignkey')
        batch_op.drop_index('ix_bia_components_info_label_id')
        batch_op.drop_column('info_label_id')

    op.drop_table('bia_information_labels')
