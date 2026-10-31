"""食堂 / 商家 / 菜品的只读查询。

约定：
- 商家综合评分**不落库**，这里按"上架菜品按评价数加权"实时聚合。
- 需要跨表字段时用显式 join 选列，配合 noload 关掉关系预加载，避免多余的 selectin 查询。
"""

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.exceptions import NotFound
from app.models.catalog import Canteen, Dish, Merchant
from app.models.rating import Rating
from app.models.user import User
from app.schemas.catalog import CanteenOut, DishOut, MerchantOut, RatingOut

# 加权综合评分：SUM(avg_rating * rating_count) / SUM(rating_count)，只算上架菜品
_OVERALL = func.coalesce(
    func.round(func.sum(Dish.avg_rating * Dish.rating_count) / func.nullif(func.sum(Dish.rating_count), 0), 2),
    0,
).label("overall_rating")
_DISH_COUNT = func.count(Dish.id).label("dish_count")


async def list_canteens(db: AsyncSession) -> list[CanteenOut]:
    counter = (
        select(Merchant.canteen_id.label("canteen_id"), func.count(Merchant.id).label("cnt"))
        .group_by(Merchant.canteen_id)
        .subquery()
    )
    stmt = (
        select(Canteen, func.coalesce(counter.c.cnt, 0))
        .outerjoin(counter, counter.c.canteen_id == Canteen.id)
        .order_by(Canteen.id)
    )
    rows = (await db.execute(stmt)).all()
    return [CanteenOut(id=c.id, name=c.name, merchant_count=int(cnt)) for c, cnt in rows]


async def search_dishes(
    db: AsyncSession, keyword: str, offset: int, limit: int
) -> tuple[list[DishOut], int]:
    """按菜名或商家名模糊搜索，只返回上架菜品。

    搜"兰州"能同时搜到「牛肉拉面」这类只带商家名的结果，比只匹配菜名好用。
    """
    keyword = keyword.strip()
    stmt = (
        select(Dish, Merchant.name, Canteen.name)
        .join(Merchant, Dish.merchant_id == Merchant.id)
        .join(Canteen, Merchant.canteen_id == Canteen.id)
        .where(Dish.is_available.is_(True))
        .options(noload(Dish.merchant))
    )
    count_stmt = select(func.count()).select_from(Dish).join(Merchant, Dish.merchant_id == Merchant.id)

    if keyword:
        pattern = f"%{keyword}%"
        condition = or_(Dish.name.like(pattern), Merchant.name.like(pattern))
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    total = int(await db.scalar(count_stmt) or 0)
    rows = (await db.execute(stmt.order_by(Dish.rating_count.desc(), Dish.id).offset(offset).limit(limit))).all()
    return [_to_dish_out(d, m_name, c_name) for d, m_name, c_name in rows], total


async def get_canteen(db: AsyncSession, canteen_id: int) -> CanteenOut:
    canteen = await db.get(Canteen, canteen_id)
    if canteen is None:
        raise NotFound("食堂不存在")
    count = await db.scalar(select(func.count()).select_from(Merchant).where(Merchant.canteen_id == canteen_id))
    return CanteenOut(id=canteen.id, name=canteen.name, merchant_count=int(count or 0))


async def list_merchants(db: AsyncSession, canteen_id: int | None = None) -> list[MerchantOut]:
    stmt = (
        select(Merchant, Canteen.name, _OVERALL, _DISH_COUNT)
        .join(Canteen, Merchant.canteen_id == Canteen.id)
        .outerjoin(Dish, and_(Dish.merchant_id == Merchant.id, Dish.is_available.is_(True)))
        .group_by(Merchant.id, Canteen.name)
        .order_by(Merchant.id)
        .options(noload(Merchant.canteen))
    )
    if canteen_id is not None:
        stmt = stmt.where(Merchant.canteen_id == canteen_id)
    rows = (await db.execute(stmt)).all()
    return [
        MerchantOut(
            id=m.id,
            name=m.name,
            canteen_id=m.canteen_id,
            canteen_name=canteen_name,
            overall_rating=float(overall or 0),
            dish_count=int(dish_count or 0),
        )
        for m, canteen_name, overall, dish_count in rows
    ]


async def get_merchant(db: AsyncSession, merchant_id: int) -> MerchantOut:
    stmt = (
        select(Merchant, Canteen.name, _OVERALL, _DISH_COUNT)
        .join(Canteen, Merchant.canteen_id == Canteen.id)
        .outerjoin(Dish, and_(Dish.merchant_id == Merchant.id, Dish.is_available.is_(True)))
        .where(Merchant.id == merchant_id)
        .group_by(Merchant.id, Canteen.name)
        .options(noload(Merchant.canteen))
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        raise NotFound("商家不存在")
    merchant, canteen_name, overall, dish_count = row
    return MerchantOut(
        id=merchant.id,
        name=merchant.name,
        canteen_id=merchant.canteen_id,
        canteen_name=canteen_name,
        overall_rating=float(overall or 0),
        dish_count=int(dish_count or 0),
    )


async def list_dishes(db: AsyncSession, merchant_id: int, include_unavailable: bool = False) -> list[DishOut]:
    # 先确认商家存在，否则"0 个菜品"和"商家不存在"分不清
    await get_merchant(db, merchant_id)

    stmt = (
        select(Dish, Merchant.name, Canteen.name)
        .join(Merchant, Dish.merchant_id == Merchant.id)
        .join(Canteen, Merchant.canteen_id == Canteen.id)
        .where(Dish.merchant_id == merchant_id)
        .order_by(Dish.id)
        .options(noload(Dish.merchant))
    )
    if not include_unavailable:
        stmt = stmt.where(Dish.is_available.is_(True))
    rows = (await db.execute(stmt)).all()
    return [_to_dish_out(d, m_name, c_name) for d, m_name, c_name in rows]


async def top_dishes(
    db: AsyncSession, min_rating: float = 4.0, min_count: int = 2, limit: int = 6
) -> list[DishOut]:
    """高分榜：够分且够人评才上榜。

    为什么要有 min_count：只要一个人打 5 星就能让一道菜登顶，榜单会退化成"谁先打分谁赢"。
    两个门槛一起用，才代表"多数人觉得好吃"。
    """
    stmt = (
        select(Dish, Merchant.name, Canteen.name)
        .join(Merchant, Dish.merchant_id == Merchant.id)
        .join(Canteen, Merchant.canteen_id == Canteen.id)
        .where(
            Dish.is_available.is_(True),
            Dish.rating_count >= min_count,
            Dish.avg_rating >= min_rating,
        )
        # 同分时评价多的靠前：4.67 分 3 人评 比 2 人评更可信
        .order_by(Dish.avg_rating.desc(), Dish.rating_count.desc(), Dish.id)
        .limit(limit)
        .options(noload(Dish.merchant))
    )
    rows = (await db.execute(stmt)).all()
    return [_to_dish_out(dish, merchant_name, canteen_name) for dish, merchant_name, canteen_name in rows]


async def get_dish(db: AsyncSession, dish_id: int) -> DishOut:
    stmt = (
        select(Dish, Merchant.name, Canteen.name)
        .join(Merchant, Dish.merchant_id == Merchant.id)
        .join(Canteen, Merchant.canteen_id == Canteen.id)
        .where(Dish.id == dish_id)
        .options(noload(Dish.merchant))
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        raise NotFound("菜品不存在")
    dish, merchant_name, canteen_name = row
    return _to_dish_out(dish, merchant_name, canteen_name)


async def list_dish_ratings(
    db: AsyncSession, dish_id: int, offset: int, limit: int
) -> tuple[list[RatingOut], int]:
    await get_dish(db, dish_id)  # 不存在直接 404，而不是返回空列表

    total = await db.scalar(select(func.count()).select_from(Rating).where(Rating.dish_id == dish_id))
    stmt = (
        select(Rating, User.nickname, User.avatar_url)
        .join(User, Rating.user_id == User.id)
        .where(Rating.dish_id == dish_id)
        .order_by(Rating.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    items = [
        RatingOut(user_id=r.user_id, nickname=nickname, avatar_url=avatar, score=r.score, updated_at=r.updated_at)
        for r, nickname, avatar in rows
    ]
    return items, int(total or 0)


def _to_dish_out(dish: Dish, merchant_name: str, canteen_name: str) -> DishOut:
    return DishOut(
        id=dish.id,
        name=dish.name,
        image_url=dish.image_url,
        merchant_id=dish.merchant_id,
        merchant_name=merchant_name,
        canteen_name=canteen_name,
        avg_rating=float(dish.avg_rating),
        rating_count=dish.rating_count,
        is_available=dish.is_available,
    )
