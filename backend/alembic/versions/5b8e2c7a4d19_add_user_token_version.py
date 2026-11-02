"""用户的令牌版本号（users.token_version）

Revision ID: 5b8e2c7a4d19
Revises: 2f7c4a9d31b8
Create Date: 2026-11-02

JWT 是自证的，签出去就收不回来。要支持"登出后旧 token 立刻失效"，
最省事的办法是给用户加一个版本号：签名时写进 payload，校验时比对，
不一致就判无效。登出 / 改密把版本 +1，所有旧 token 一起作废。

不引入 token 黑名单表：那需要存 jti 并定期清理过期项，为 MVP 没必要。
默认 0，历史行不用回填；早期没有 ver 的 token 在解码时按 0 处理，
所以升级那一刻已登录的会话不会被踢掉。
"""

import sqlalchemy as sa
from alembic import op

revision = "5b8e2c7a4d19"
down_revision = "2f7c4a9d31b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="令牌版本：登出/改密时 +1，旧 token 随之失效",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
