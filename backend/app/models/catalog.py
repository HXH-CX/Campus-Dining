from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    pass


class Canteen(Base, TimestampMixin):
    """食堂。删除前必须保证其下没有商家，由 service 层校验。"""

    __tablename__ = "canteens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Canteen id={self.id} name={self.name!r}>"


class Merchant(Base, TimestampMixin):
    """商家。

    注意：综合评分**不落库**，按上架菜品的评分加权在查询时聚合，见 service 层。
    """

    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    canteen_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("canteens.id", name="fk_merchant_canteen"), nullable=False, index=True
    )

    canteen: Mapped[Canteen] = relationship(lazy="selectin")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Merchant id={self.id} name={self.name!r}>"


class Dish(Base, TimestampMixin):
    """菜品。

    avg_rating / rating_count 是冗余聚合字段，每次打分后由 service 在同一事务内重算
    （数据量小，重算比维护增量更不容易错）。
    is_available 为 False 时：不出现在默认菜品列表、不可被新帖关联，但历史帖子与评分完整保留。
    """

    __tablename__ = "dishes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(255), default=None)
    merchant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("merchants.id", name="fk_dish_merchant"), nullable=False, index=True
    )
    avg_rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00"), comment="平均分"
    )
    rating_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0"), comment="评价总数"
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1"), comment="1上架 0下架"
    )

    merchant: Mapped[Merchant] = relationship(lazy="selectin")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Dish id={self.id} name={self.name!r} avg={self.avg_rating}>"
