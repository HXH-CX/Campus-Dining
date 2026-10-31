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
from app.models.social import Want
from app.models.user import User
from app.schemas.catalog import CanteenOut, DishOut, MerchantOut, RandomDishOut, RatingOut

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
    return [to_dish_out(d, m_name, c_name) for d, m_name, c_name in rows], total


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
    return [to_dish_out(d, m_name, c_name) for d, m_name, c_name in rows]


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
    return [to_dish_out(dish, merchant_name, canteen_name) for dish, merchant_name, canteen_name in rows]


async def random_dish(
    db: AsyncSession,
    *,
    min_rating: float = 4.0,
    min_count: int = 2,
    exclude_id: int | None = None,
    wanted_by: int | None = None,
) -> RandomDishOut:
    """「今天吃什么」：随机抽一道菜。

    默认先在高分池里抽（够分 + 够人评），池子空时退回全部在售菜品。
    为什么不只在高分池里抽：数据少的时候会直接抽不出来，
    对"选择困难"的人来说，抽不出来比抽到一道没人评过的菜更让人放弃。

    wanted_by 给「从想吃里抽」用：只在这份清单里挑，不做任何回退——
    用户自己挑的池子就该被尊重，抽不到时前端引导去加菜，而不是偷偷塞一道别的。

    exclude_id 用来支撑「换一个」：刚抽到的那道不再进候选，
    除非池子里只剩它（否则会 404，还不如把同一道菜再端上来）。
    """
    if wanted_by is not None:
        want_ids = select(Want.dish_id).where(Want.user_id == wanted_by)
        # 下架的菜不能出现在结果里：清单是历史，抽签要能真去吃
        body = [Dish.is_available.is_(True), Dish.id.in_(want_ids)]
        attempts: list[tuple[list, str]] = [(body + [Dish.id != exclude_id], "wants")] if exclude_id else []
        attempts.append((body, "wants"))
        empty_message = "想吃清单还是空的，先去挑几道"
    else:
        qualified = [
            Dish.is_available.is_(True),
            Dish.rating_count >= min_count,
            Dish.avg_rating >= min_rating,
        ]
        available = [Dish.is_available.is_(True)]
        attempts = []
        if exclude_id is not None:
            attempts.append((qualified + [Dish.id != exclude_id], "top"))
            attempts.append((available + [Dish.id != exclude_id], "all"))
        attempts.append((qualified, "top"))
        attempts.append((available, "all"))
        empty_message = "还没有可供选择的菜品"

    for conditions, source in attempts:
        stmt = (
            select(Dish, Merchant.name, Canteen.name)
            .join(Merchant, Dish.merchant_id == Merchant.id)
            .join(Canteen, Merchant.canteen_id == Canteen.id)
            .where(*conditions)
            .options(noload(Dish.merchant))
        )
        pool = int(await db.scalar(stmt.with_only_columns(func.count()).order_by(None)) or 0)
        if not pool:
            continue
        # 小表上 ORDER BY RAND() 足够快；真到几万行再改成"先 count 再随机 offset"
        row = (await db.execute(stmt.order_by(func.rand()).limit(1))).first()
        if row is None:
            continue
        dish, merchant_name, canteen_name = row
        return RandomDishOut(
            dish=to_dish_out(dish, merchant_name, canteen_name),
            pool_size=pool,
            source=source,
        )

    raise NotFound(empty_message)


async def get_dish(
    db: AsyncSession, dish_id: int, viewer_id: int | None = None, with_want: bool = False
) -> DishOut:
    """菜品详情。

    with_want 只在详情页开：想吃人数要单独 COUNT，后台列表一次查 20 个菜品时
    没必要逐个计数（那里也不展示这个字段）。
    """
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
    out = to_dish_out(dish, merchant_name, canteen_name)

    if with_want:
        from app.services import want_service  # 局部导入：want_service 反向依赖 to_dish_out

        want_count, is_wanted = await want_service.state_of(db, dish_id, viewer_id)
        out.want_count = want_count
        out.is_wanted = is_wanted
    return out


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


def to_dish_out(dish: Dish, merchant_name: str, canteen_name: str) -> DishOut:
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
