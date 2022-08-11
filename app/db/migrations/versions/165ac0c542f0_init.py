"""init

Revision ID: 165ac0c542f0
Revises: 
Create Date: 2022-08-11 21:14:39.219289

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '165ac0c542f0'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('catalog_template',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('title')
    )
    op.create_table('settings',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('vcd_api_jwt', sa.String(length=1023), nullable=True),
    sa.Column('default_vdc', sa.String(length=255), nullable=True),
    sa.Column('default_vapp', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('default_vapp'),
    sa.UniqueConstraint('default_vdc'),
    sa.UniqueConstraint('vcd_api_jwt')
    )
    op.create_table('vapp_template',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('title')
    )
    op.create_table('vm',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('vm_id', sa.String(length=255), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('vm_id')
    )
    op.create_table('vm_template',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('title')
    )
    op.create_table('template_catalog',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('catalog_template_id', sa.Integer(), nullable=False),
    sa.Column('vapp_template_id', sa.Integer(), nullable=False),
    sa.Column('vm_template_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['catalog_template_id'], ['catalog_template.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['vapp_template_id'], ['vapp_template.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['vm_template_id'], ['vm_template.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('vm_template_id')
    )
    op.create_table('vm_statistics',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('vm_id', sa.Integer(), nullable=True),
    sa.Column('statistics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['vm_id'], ['vm.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('vm_statistics')
    op.drop_table('template_catalog')
    op.drop_table('vm_template')
    op.drop_table('vm')
    op.drop_table('vapp_template')
    op.drop_table('settings')
    op.drop_table('catalog_template')
    # ### end Alembic commands ###