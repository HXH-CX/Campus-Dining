"""热榜缓存。

MVP 不上 Redis：进程内缓存 + 1 小时 TTL，配合 APScheduler 每小时预热。
这样即使调度器没起来（比如测试环境），接口读到的也只是"按需重算"的结果，不会报错。
"""

import logging
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.post import Like, Post
from app.schemas.post import PostOut
from app.services import post_service

logger = logging.getLogger("app.hot")

CACHE_TTL_SECONDS = settings.HOT_CACHE_TTL_SECONDS

_cache: dict[str, object] = {"items": [], "expires_at": 0.0}


async def get_hot(db: AsyncSession, viewer=None) -> list[PostOut]:
    items = await _load(db)
    if viewer is None:
        return items  # 已缓存的列表直接复用（调用方只读）

    liked = set(
        (
            await db.execute(
                select(Like.post_id).where(Like.user_id == viewer.id, Like.post_id.in_([i.id for i in items]))
            )
        ).scalars()
    )
    # 缓存不能按用户区分，所以 is_liked 在这里按访问者补
    return [item.model_copy(update={"is_liked": item.id in liked}) for item in items]


async def _load(db: AsyncSession) -> list[PostOut]:
    now = time.monotonic()
    if _cache["items"] and now < float(_cache["expires_at"]):
        return list(_cache["items"])  # type: ignore[arg-type]

    items = await post_service.list_hot(db)
    _cache["items"] = items
    _cache["expires_at"] = now + CACHE_TTL_SECONDS
    return items


async def refresh(db: AsyncSession) -> None:
    """强制重算，供定时任务调用。"""
    items = await post_service.list_hot(db)
    _cache["items"] = items
    _cache["expires_at"] = time.monotonic() + CACHE_TTL_SECONDS
    logger.info("热榜已刷新，共 %d 条", len(items))


def invalidate() -> None:
    """发帖/删帖/点赞后让缓存尽快失效。TTL 兜底，这里只是让榜单更实时。"""
    _cache["expires_at"] = 0.0
