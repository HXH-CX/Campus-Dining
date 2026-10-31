"""add wants

Revision ID: 3c1f9a2b7d54
Revises: 78100d949cc7
Create Date: 2026-10-31 09:25:12.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '3c1f9a2b7d54'
down_revision: str | None = '78100d949cc7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'wants',
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('dish_id', sa.BigInteger(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('now()'),
            nullable=False,
            comment='创建时间',
        ),
        sa.ForeignKeyConstraint(['dish_id'], ['dishes.id'], name='fk_want_dish'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_want_user'),
        sa.PrimaryKeyConstraint('user_id', 'dish_id'),
    )
    op.create_index('idx_wants_dish', 'wants', ['dish_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_wants_dish', table_name='wants')
    op.drop_table('wants')
