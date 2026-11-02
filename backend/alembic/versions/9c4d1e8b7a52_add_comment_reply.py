"""评论支持回复某条评论（comments.reply_to_id）

Revision ID: 9c4d1e8b7a52
Revises: 5b8e2c7a4d19
Create Date: 2026-11-02

自引用外键，只做一层：被回复评论被删时置 NULL（SET NULL），
而不是连回复一起级联删除——"楼下说了什么"不该因为楼上删了而消失。
评论列表本来就是按帖平铺，所以只加列不加树结构。
"""

import sqlalchemy as sa
from alembic import op

revision = "9c4d1e8b7a52"
down_revision = "5b8e2c7a4d19"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "comments",
        sa.Column("reply_to_id", sa.BigInteger(), nullable=True, comment="回复的评论 id；顶层评论为 NULL"),
    )
    op.create_index("idx_comments_reply", "comments", ["reply_to_id"])
    op.create_foreign_key(
        "fk_comment_reply_to",
        "comments",
        "comments",
        ["reply_to_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_comment_reply_to", "comments", type_="foreignkey")
    op.drop_index("idx_comments_reply", table_name="comments")
    op.drop_column("comments", "reply_to_id")
