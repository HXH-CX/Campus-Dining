from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin


class Rating(Base, CreatedAtMixin):
    """菜品评分：一人一菜一条（uk_user_dish），重复打分覆盖 score 与 updated_at。

    语义是"我当前的看法"，所以不做历史流水；多次就餐的差异用多条帖子表达。
    """

    __tablename__ = "ratings"
    __table_args__ = (
        Index("uk_user_dish", "user_id", "dish_id", unique=True),
        Index("idx_ratings_user_recent", "user_id", "updated_at"),
        Index("idx_ratings_dish", "dish_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", name="fk_rating_user"), nullable=False)
    dish_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dishes.id", name="fk_rating_dish"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False, comment="1-5 星，只取整星")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="重复打分时刷新；称号统计按此字段取时间窗口",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Rating user={self.user_id} dish={self.dish_id} score={self.score}>"
