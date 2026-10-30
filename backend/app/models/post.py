from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, JSON, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.catalog import Dish
    from app.models.user import User


class Post(Base, TimestampMixin):
    """帖子。

    帖子与评分是两件事：帖子记录"这次就餐的图文体验"，可对同一道菜发多条；
    score 不存在这里，评分统一落在 ratings 表（一人一菜一条）。
    """

    __tablename__ = "posts"
    __table_args__ = (
        Index("idx_posts_created", "created_at"),
        Index("idx_posts_dish", "dish_id"),
        Index("idx_posts_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", name="fk_post_user"), nullable=False)
    dish_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dishes.id", name="fk_post_dish"), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, default=None, comment="文案，≤500字")
    images: Mapped[list[str] | None] = mapped_column(
        JSON, default=None, comment='图片 URL 数组，如 ["/uploads/2026/10/a.jpg"]'
    )
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))

    author: Mapped[User] = relationship(lazy="selectin")
    dish: Mapped[Dish] = relationship(lazy="selectin")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Post id={self.id} user={self.user_id} dish={self.dish_id}>"


class Comment(Base, CreatedAtMixin):
    __tablename__ = "comments"
    __table_args__ = (Index("idx_comments_post", "post_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("posts.id", name="fk_comment_post", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", name="fk_comment_user"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    author: Mapped[User] = relationship(lazy="selectin")


class Like(Base, CreatedAtMixin):
    """点赞。复合主键即天然唯一约束，重复点赞由 service 做"切换"语义。"""

    __tablename__ = "likes"
    __table_args__ = (Index("idx_likes_post", "post_id"),)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", name="fk_like_user"), primary_key=True)
    post_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("posts.id", name="fk_like_post", ondelete="CASCADE"), primary_key=True
    )
