"""add notifications

Revision ID: 8d4b2e6a91c7
Revises: 3c1f9a2b7d54
Create Date: 2026-10-31 10:12:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '8d4b2e6a91c7'
down_revision: str | None = '3c1f9a2b7d54'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'notifications',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='接收者'),
        sa.Column('actor_id', sa.BigInteger(), nullable=False, comment='触发者'),
        sa.Column('type', sa.String(length=20), nullable=False, comment='like / comment / follow'),
        sa.Column('post_id', sa.BigInteger(), nullable=True),
        sa.Column('comment_id', sa.BigInteger(), nullable=True),
        sa.Column('is_read', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('now()'),
            nullable=False,
            comment='创建时间',
        ),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], name='fk_notify_actor', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['comment_id'], ['comments.id'], name='fk_notify_comment', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], name='fk_notify_post', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_notify_user', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'idx_notifications_user', 'notifications', ['user_id', 'is_read', 'created_at'], unique=False
    )
    op.create_index('idx_notifications_actor', 'notifications', ['actor_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_notifications_actor', table_name='notifications')
    op.drop_index('idx_notifications_user', table_name='notifications')
    op.drop_table('notifications')
