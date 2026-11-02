"""菜品的口味/形态标签（dishes.tags）

Revision ID: 2f7c4a9d31b8
Revises: 8d4b2e6a91c7
Create Date: 2026-11-02

加一列 JSON 数组，不动任何现有关系：白名单在 app/core/tags.py 里，
改词表不需要迁移。默认值用 MySQL 8.0.13+ 的表达式默认值 '('[]')'，
已有行会直接拿到空数组，不用 UPDATE 补数据。
"""

import sqlalchemy as sa
from alembic import op

revision = "2f7c4a9d31b8"
down_revision = "8d4b2e6a91c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dishes",
        sa.Column(
            "tags",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("('[]')"),
            comment="标签数组",
        ),
    )


def downgrade() -> None:
    op.drop_column("dishes", "tags")
