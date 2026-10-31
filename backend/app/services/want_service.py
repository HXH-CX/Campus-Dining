"""想吃清单。

只做标记，不参与评分、不改变菜品聚合。
用途是给「今天吃什么」提供一份**用户自己挑过**的候选池：
存 → 抽 → 吃 → 评，这条链路里它负责"存"那一步。
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.exceptions import BadRequest, NotFound
from app.models.catalog import Canteen, Dish, Merchant
from app.models.social import Want
from app.models.user import User
from app.schemas.catalog import DishOut
from app.services.catalog_service import to_dish_out


async def count_of(db: AsyncSession, dish_id: int) -> int:
    return int(await db.scalar(select(func.count()).select_from(Want).where(Want.dish_id == dish_id)) or 0)


async def state_of(db: AsyncSession, dish_id: int, viewer_id: int | None) -> tuple[int, bool]:
    """返回 (想吃人数, 我是否想吃)。未登录时 is_wanted 恒为 False，人数照常返回。"""
    count = await count_of(db, dish_id)
    if viewer_id is None:
        return count, False
    return count, await db.get(Want, (viewer_id, dish_id)) is not None


async def toggle(db: AsyncSession, user: User, dish_id: int) -> tuple[bool, int]:
    """加入 / 移出清单，返回 (操作后是否在清单里, 最新想吃人数)。"""
    dish = await db.get(Dish, dish_id)
    if dish is None:
        raise NotFound("菜品不存在")

    existing = await db.get(Want, (user.id, dish_id))
    if existing is not None:
        await db.delete(existing)
        wanted = False
    else:
        # 与发帖一致：下架的菜连"想吃"都不让点，避免清单里堆一批已经吃不到的菜
        if not dish.is_available:
            raise BadRequest("该菜品已下架，暂不能加入想吃清单")
        db.add(Want(user_id=user.id, dish_id=dish_id))
        wanted = True

    await db.commit()
    return wanted, await count_of(db, dish_id)


async def list_wants(db: AsyncSession, user_id: int, offset: int, limit: int) -> tuple[list[DishOut], int]:
    """某人的想吃清单，最近加的在前。已下架的菜仍出现在列表里（历史），由前端标记。"""
    if await db.get(User, user_id) is None:
        raise NotFound("用户不存在")

    total = int(await db.scalar(select(func.count()).select_from(Want).where(Want.user_id == user_id)) or 0)
    stmt = (
        select(Dish, Merchant.name, Canteen.name)
        .join(Want, Want.dish_id == Dish.id)
        .join(Merchant, Dish.merchant_id == Merchant.id)
        .join(Canteen, Merchant.canteen_id == Canteen.id)
        .where(Want.user_id == user_id)
        .order_by(Want.created_at.desc(), Dish.id.desc())
        .offset(offset)
        .limit(limit)
        .options(noload(Dish.merchant))
    )
    rows = (await db.execute(stmt)).all()
    return [to_dish_out(dish, merchant_name, canteen_name) for dish, merchant_name, canteen_name in rows], total
