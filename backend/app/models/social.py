from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin

if TYPE_CHECKING:
    from app.models.user import User


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
