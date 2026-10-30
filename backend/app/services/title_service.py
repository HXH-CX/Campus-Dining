"""称号与隐藏成就的懒更新。

不建冗余计数列，直接按索引 COUNT（校园站量级足够），避免计数漂移。
只升不降：算出新等级后与当前比较，更大才写库。
"""

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.titles import level_by_contribution
from app.models.catalog import Dish
from app.models.post import Like, Post
from app.models.rating import Rating
from app.models.social import UserAchievement
from app.models.user import User

PURE_LOVE_CODE = "pure_love_warrior"
PURE_LOVE_DAYS = 30
PURE_LOVE_MIN_RATINGS = 3


async def refresh(db: AsyncSession, user: User) -> User:
    """重算等级与隐藏成就，返回最新的 User 对象（成就列表已加载）。"""
    post_count = int(await db.scalar(select(func.count()).select_from(Post).where(Post.user_id == user.id)) or 0)
    like_count = int(
        await db.scalar(
            select(func.count())
            .select_from(Like)
            .join(Post, Like.post_id == Post.id)
            .where(Post.user_id == user.id)
        )
        or 0
    )

    level = level_by_contribution(post_count, like_count)
    dirty = False
    if level > user.title_level:  # 只升不降
        user.title_level = level
        dirty = True

    if await _try_unlock_pure_love(db, user.id):
        dirty = True

    if dirty:
        try:
            await db.commit()
        except IntegrityError:
            # 并发解锁同一个成就：另一路已经写进去了，回滚后重读即可，不该给用户 500
            await db.rollback()
        refreshed = await db.execute(select(User).where(User.id == user.id))
        return refreshed.scalar_one()
    return user


async def _try_unlock_pure_love(db: AsyncSession, user_id: int) -> bool:
    """近 30 天打分次数 ≥3 且全部来自同一商家 -> 解锁纯爱战神（一次性永久保留）。"""
    row = (
        await db.execute(
            select(
                func.count().label("cnt"),
                func.count(func.distinct(Dish.merchant_id)).label("merchants"),
            )
            .select_from(Rating)
            .join(Dish, Rating.dish_id == Dish.id)
            .where(
                Rating.user_id == user_id,
                Rating.updated_at >= text(f"NOW() - INTERVAL {PURE_LOVE_DAYS} DAY"),
            )
        )
    ).one()

    if int(row.cnt or 0) < PURE_LOVE_MIN_RATINGS or int(row.merchants or 0) != 1:
        return False

    # 先查再插：INSERT IGNORE 虽然也能去重，但驱动会把重复键当警告打到 stderr，日志很脏
    unlocked = await db.scalar(
        select(UserAchievement.id).where(
            UserAchievement.user_id == user_id, UserAchievement.code == PURE_LOVE_CODE
        )
    )
    if unlocked is not None:
        return False

    db.add(UserAchievement(user_id=user_id, code=PURE_LOVE_CODE))
    return True
