from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin

if TYPE_CHECKING:
    from app.models.post import Comment, Post
    from app.models.user import User

# 通知类型：点赞、评论、关注。不要扩成枚举表，三种够用且前端要按类型给文案。
NOTIFY_LIKE = "like"
NOTIFY_COMMENT = "comment"
NOTIFY_FOLLOW = "follow"


class Follow(Base, CreatedAtMixin):
    """单向关注。互关不单独建模，查询时用 EXISTS 推导 is_mutual 返回前端。"""

    __tablename__ = "follows"
    __table_args__ = (Index("idx_follows_following", "following_id"),)

    follower_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", name="fk_follow_follower"), primary_key=True
    )
    following_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", name="fk_follow_following"), primary_key=True
    )


class Want(Base, CreatedAtMixin):
    """想吃清单：一人一菜一条，纯标记。

    不影响评分，也不代表"吃过"——它的用途是给"今天吃什么"提供一份
    由本人挑过的候选池，抽中了再决定去不去。
    """

    __tablename__ = "wants"
    __table_args__ = (Index("idx_wants_dish", "dish_id"),)

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", name="fk_want_user"), primary_key=True
    )
    dish_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dishes.id", name="fk_want_dish"), primary_key=True
    )


class UserAchievement(Base):
    """隐藏成就，与等级称号并存展示（如"食堂扫地僧 + 纯爱战神"）。一次性解锁，永久保留。"""

    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "code", name="uk_user_code"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_achievement_user", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False, comment="如 pure_love_warrior")
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="achievements")


class Notification(Base, CreatedAtMixin):
    """站内通知：谁对你做了什么。

    设计上是"事件即通知"，只在被操作发生时写一行，不做已读同步之外的任何状态。
    同一个人对同一篇帖子重复点赞（取消再点）不重复堆积：写之前先删同键旧行，
    相当于把时间刷新到最近一次——用户看到的是"他赞了你"，不是"他赞了你 5 次"。

    帖子 / 评论被删时靠外键 CASCADE 连带清掉通知，避免点开是空的。
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notifications_user", "user_id", "is_read", "created_at"),
        Index("idx_notifications_actor", "actor_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", name="fk_notify_user", ondelete="CASCADE"), nullable=False,
        comment="接收者",
    )
    actor_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", name="fk_notify_actor", ondelete="CASCADE"), nullable=False,
        comment="触发者",
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False, comment="like / comment / follow")
    post_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("posts.id", name="fk_notify_post", ondelete="CASCADE"), default=None
    )
    comment_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("comments.id", name="fk_notify_comment", ondelete="CASCADE"), default=None
    )
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("0"))

    actor: Mapped[User] = relationship(lazy="selectin", foreign_keys=[actor_id])
    post: Mapped[Post | None] = relationship("Post", lazy="selectin")
    comment: Mapped[Comment | None] = relationship("Comment", lazy="selectin")
