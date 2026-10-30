"""管理端 CRUD。

删除一律"先问有没有下级/引用"，有就 40901 让管理员先处理，
不靠数据库外键报 500 给前端看。菜品被引用后只允许下架，不物理删除。
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound
from app.models.catalog import Canteen, Dish, Merchant
from app.models.post import Post
from app.models.rating import Rating
from app.schemas.catalog import (
    CanteenCreate,
    CanteenOut,
    CanteenUpdate,
    DishCreate,
    DishOut,
    DishUpdate,
    MerchantCreate,
    MerchantOut,
    MerchantUpdate,
)
from app.services import catalog_service, post_service


async def _count(db: AsyncSession, model, *conditions) -> int:
    stmt = select(func.count()).select_from(model)
    for cond in conditions:
        stmt = stmt.where(cond)
    return int(await db.scalar(stmt) or 0)


async def _canteen_out(db: AsyncSession, canteen: Canteen) -> CanteenOut:
    count = await _count(db, Merchant, Merchant.canteen_id == canteen.id)
    return CanteenOut(id=canteen.id, name=canteen.name, merchant_count=count)


# ---------------------------------------------------------------- 食堂


async def list_canteens(db: AsyncSession, offset: int, limit: int) -> tuple[list[CanteenOut], int]:
    total = await _count(db, Canteen)
    rows = (
        await db.execute(select(Canteen).order_by(Canteen.id).offset(offset).limit(limit))
    ).scalars().all()
    items = [await _canteen_out(db, c) for c in rows]
    return items, total


async def create_canteen(db: AsyncSession, payload: CanteenCreate) -> CanteenOut:
    if await _count(db, Canteen, Canteen.name == payload.name):
        raise Conflict("同名食堂已存在")
    canteen = Canteen(name=payload.name)
    db.add(canteen)
    await db.commit()
    return await _canteen_out(db, canteen)


async def update_canteen(db: AsyncSession, canteen_id: int, payload: CanteenUpdate) -> CanteenOut:
    canteen = await db.get(Canteen, canteen_id)
    if canteen is None:
        raise NotFound("食堂不存在")
    if await _count(db, Canteen, Canteen.name == payload.name, Canteen.id != canteen_id):
        raise Conflict("同名食堂已存在")
    canteen.name = payload.name
    await db.commit()
    return await _canteen_out(db, canteen)


async def delete_canteen(db: AsyncSession, canteen_id: int) -> None:
    canteen = await db.get(Canteen, canteen_id)
    if canteen is None:
        raise NotFound("食堂不存在")
    merchant_count = await _count(db, Merchant, Merchant.canteen_id == canteen_id)
    if merchant_count:
        raise Conflict(f"该食堂下还有 {merchant_count} 个商家，请先删除或迁移商家")
    await db.delete(canteen)
    await db.commit()


# ---------------------------------------------------------------- 商家


async def list_merchants(
    db: AsyncSession, offset: int, limit: int, canteen_id: int | None = None
) -> tuple[list[MerchantOut], int]:
    total_stmt = select(func.count()).select_from(Merchant)
    if canteen_id is not None:
        total_stmt = total_stmt.where(Merchant.canteen_id == canteen_id)
    total = int(await db.scalar(total_stmt) or 0)

    ids_stmt = select(Merchant.id).order_by(Merchant.id).offset(offset).limit(limit)
    if canteen_id is not None:
        ids_stmt = ids_stmt.where(Merchant.canteen_id == canteen_id)
    ids = (await db.execute(ids_stmt)).scalars().all()

    items: list[MerchantOut] = []
    for merchant_id in ids:
        items.append(await catalog_service.get_merchant(db, merchant_id))
    return items, total


async def create_merchant(db: AsyncSession, payload: MerchantCreate) -> MerchantOut:
    if await db.get(Canteen, payload.canteen_id) is None:
        raise NotFound("所属食堂不存在")
    merchant = Merchant(name=payload.name, canteen_id=payload.canteen_id)
    db.add(merchant)
    await db.commit()
    return await catalog_service.get_merchant(db, merchant.id)


async def update_merchant(db: AsyncSession, merchant_id: int, payload: MerchantUpdate) -> MerchantOut:
    merchant = await db.get(Merchant, merchant_id)
    if merchant is None:
        raise NotFound("商家不存在")
    if payload.canteen_id is not None:
        if await db.get(Canteen, payload.canteen_id) is None:
            raise NotFound("所属食堂不存在")
        merchant.canteen_id = payload.canteen_id
    if payload.name is not None:
        merchant.name = payload.name
    await db.commit()
    return await catalog_service.get_merchant(db, merchant_id)


async def delete_merchant(db: AsyncSession, merchant_id: int) -> None:
    merchant = await db.get(Merchant, merchant_id)
    if merchant is None:
        raise NotFound("商家不存在")
    dish_count = await _count(db, Dish, Dish.merchant_id == merchant_id)
    if dish_count:
        raise Conflict(f"该商家下还有 {dish_count} 个菜品，请先删除或下架后处理")
    await db.delete(merchant)
    await db.commit()


# ---------------------------------------------------------------- 菜品


async def list_dishes(
    db: AsyncSession,
    offset: int,
    limit: int,
    merchant_id: int | None = None,
    include_unavailable: bool = True,
) -> tuple[list[DishOut], int]:
    total_stmt = select(func.count()).select_from(Dish)
    if merchant_id is not None:
        total_stmt = total_stmt.where(Dish.merchant_id == merchant_id)
    if not include_unavailable:
        total_stmt = total_stmt.where(Dish.is_available.is_(True))
    total = int(await db.scalar(total_stmt) or 0)

    ids_stmt = select(Dish.id).order_by(Dish.id).offset(offset).limit(limit)
    if merchant_id is not None:
        ids_stmt = ids_stmt.where(Dish.merchant_id == merchant_id)
    if not include_unavailable:
        ids_stmt = ids_stmt.where(Dish.is_available.is_(True))
    ids = (await db.execute(ids_stmt)).scalars().all()

    items = [await catalog_service.get_dish(db, dish_id) for dish_id in ids]
    return items, total


async def create_dish(db: AsyncSession, payload: DishCreate) -> DishOut:
    if await db.get(Merchant, payload.merchant_id) is None:
        raise NotFound("所属商家不存在")
    dish = Dish(name=payload.name, merchant_id=payload.merchant_id, image_url=payload.image_url)
    db.add(dish)
    await db.commit()
    return await catalog_service.get_dish(db, dish.id)


async def update_dish(db: AsyncSession, dish_id: int, payload: DishUpdate) -> DishOut:
    dish = await db.get(Dish, dish_id)
    if dish is None:
        raise NotFound("菜品不存在")
    if payload.merchant_id is not None:
        if await db.get(Merchant, payload.merchant_id) is None:
            raise NotFound("所属商家不存在")
        dish.merchant_id = payload.merchant_id
    if payload.name is not None:
        dish.name = payload.name
    if payload.image_url is not None:
        dish.image_url = payload.image_url
    await db.commit()
    return await catalog_service.get_dish(db, dish_id)


async def set_dish_availability(db: AsyncSession, dish_id: int, is_available: bool) -> DishOut:
    dish = await db.get(Dish, dish_id)
    if dish is None:
        raise NotFound("菜品不存在")
    dish.is_available = is_available
    await db.commit()
    return await catalog_service.get_dish(db, dish_id)


async def delete_dish(db: AsyncSession, dish_id: int) -> None:
    dish = await db.get(Dish, dish_id)
    if dish is None:
        raise NotFound("菜品不存在")
    post_count = await _count(db, Post, Post.dish_id == dish_id)
    rating_count = await _count(db, Rating, Rating.dish_id == dish_id)
    if post_count or rating_count:
        raise Conflict(
            f"该菜品已有 {post_count} 条帖子、{rating_count} 条评分引用，无法物理删除；请改为下架"
        )
    await db.delete(dish)
    await db.commit()


async def list_posts(
    db: AsyncSession, offset: int, limit: int, keyword: str | None = None
) -> tuple[list, int]:
    """管理端帖子列表：复用 feed 的查询，多一个关键词筛选。

    viewer 传 None：后台不需要 is_liked，省一次点赞查询。
    """
    return await post_service.list_posts(db, offset=offset, limit=limit, keyword=keyword)


async def delete_post(db: AsyncSession, post_id: int) -> None:
    """应急删除违规帖子（非审核流程）。计数一并回滚，避免榜单数据漂移。"""
    post = await db.get(Post, post_id)
    if post is None:
        raise NotFound("帖子不存在")
    dish_id = post.dish_id
    await db.delete(post)  # 评论与点赞由外键 ON DELETE CASCADE 收拾
    await db.flush()

    # 帖子被删后菜品聚合可能变化，重算一次
    from sqlalchemy import text

    await db.execute(
        text(
            """
            UPDATE dishes d SET
                avg_rating = COALESCE((SELECT ROUND(AVG(r.score), 2) FROM ratings r WHERE r.dish_id = d.id), 0),
                rating_count = (SELECT COUNT(*) FROM ratings r WHERE r.dish_id = d.id)
            WHERE d.id = :dish_id
            """
        ),
        {"dish_id": dish_id},
    )
    await db.commit()
