"""Split bia process dependencies

Revision ID: 20260214_0006
Revises: 20260211_0018
Create Date: 2026-02-14 12:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260214_0006'
down_revision = '20260211_0018'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns as Text
    op.add_column('bia_components', sa.Column('dependencies_it_systems_applications', sa.Text(), nullable=True))
    op.add_column('bia_components', sa.Column('dependencies_equipment', sa.Text(), nullable=True))
    op.add_column('bia_components', sa.Column('dependencies_suppliers', sa.Text(), nullable=True))
    op.add_column('bia_components', sa.Column('dependencies_people', sa.Text(), nullable=True))
    op.add_column('bia_components', sa.Column('dependencies_facilities', sa.Text(), nullable=True))
    op.add_column('bia_components', sa.Column('dependencies_others', sa.Text(), nullable=True))

    # Data migration: Copy existing process_dependencies to dependencies_others
    op.execute("UPDATE bia_components SET dependencies_others = process_dependencies")

    # Drop old column
    op.drop_column('bia_components', 'process_dependencies')


def downgrade():
    # Recreate process_dependencies column
    op.add_column('bia_components', sa.Column('process_dependencies', sa.Text(), nullable=True))

    # Copy data back from dependencies_others (this is lossy if other new columns were used, but best effort)
    op.execute("UPDATE bia_components SET process_dependencies = dependencies_others")

    # Drop new columns
    op.drop_column('bia_components', 'dependencies_it_systems_applications')
    op.drop_column('bia_components', 'dependencies_equipment')
    op.drop_column('bia_components', 'dependencies_suppliers')
    op.drop_column('bia_components', 'dependencies_people')
    op.drop_column('bia_components', 'dependencies_facilities')
    op.drop_column('bia_components', 'dependencies_others')
