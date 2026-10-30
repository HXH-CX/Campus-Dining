from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Integer, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.social import UserAchievement


class User(Base, TimestampMixin):
    """用户（学生 / 管理员）。

    称号只存等级 title_level，中文名由 app.core.titles 映射，不存冗余文案。
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="登录用户名")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="bcrypt 哈希")
    nickname: Mapped[str] = mapped_column(String(50), nullable=False, comment="展示昵称")
    avatar_url: Mapped[str | None] = mapped_column(String(255), default=None, comment="头像 URL")
    title_level: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, server_default=text("1"), comment="称号等级 1-5"
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0"), comment="管理员标记"
    )
    follower_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0"), comment="粉丝数"
    )
    following_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0"), comment="关注数"
    )

    achievements: Mapped[list[UserAchievement]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} username={self.username!r} lv={self.title_level}>"
