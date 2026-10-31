"""站内通知：谁赞了你的帖子、谁评论了你、谁关注了你。

三条原则：
1. **不给自己发通知**——自己的操作不该出现在自己的铃铛里。
2. **同一事件只留一条**——取消点赞再点，刷新时间而不是堆出五条"赞了你"。
3. **跟着源数据消失**——帖子/评论被删时靠外键 CASCADE 清掉通知，而不是留一条点开是空的死链。
"""

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import Notification
from app.schemas.notification import NotificationOut, NotificationPostBrief
from app.services.dto import author_brief


def _same_event(user_id: int, actor_id: int, type_: str, post_id: int | None):
    conditions = [
        Notification.user_id == user_id,
        Notification.actor_id == actor_id,
        Notification.type == type_,
    ]
    conditions.append(Notification.post_id.is_(None) if post_id is None else Notification.post_id == post_id)
    return conditions


async def push(
    db: AsyncSession,
    *,
    user_id: int,
    actor_id: int,
    type_: str,
    post_id: int | None = None,
    comment_id: int | None = None,
) -> None:
    """写一条通知。不 commit，由调用方在同一事务里提交。"""
    if user_id == actor_id:
        return
    await db.execute(delete(Notification).where(*_same_event(user_id, actor_id, type_, post_id)))
    db.add(
        Notification(
            user_id=user_id,
            actor_id=actor_id,
            type=type_,
            post_id=post_id,
            comment_id=comment_id,
        )
    )


async def revoke(db: AsyncSession, *, user_id: int, actor_id: int, type_: str, post_id: int | None = None) -> None:
    """撤销（取消点赞 / 取关）。评论删除走 CASCADE，不需要调这里。"""
    await db.execute(delete(Notification).where(*_same_event(user_id, actor_id, type_, post_id)))


def _to_out(row: Notification) -> NotificationOut:
    post = row.post
    return NotificationOut(
        id=row.id,
        type=row.type,
        is_read=row.is_read,
        created_at=row.created_at,
        actor=author_brief(row.actor),
        post=(
            NotificationPostBrief(
                id=post.id,
                dish_name=post.dish.name if post.dish else "",
                content=post.content,
                image_url=(post.images or [None])[0] if post.images else (post.dish.image_url if post.dish else None),
            )
            if post is not None
            else None
        ),
        comment_content=row.comment.content if row.comment else None,
    )


async def list_notifications(
    db: AsyncSession, user_id: int, offset: int, limit: int, unread_only: bool = False
) -> tuple[list[NotificationOut], int]:
    conditions = [Notification.user_id == user_id]
    if unread_only:
        conditions.append(Notification.is_read.is_(False))

    total = int(await db.scalar(select(func.count()).select_from(Notification).where(*conditions)) or 0)
    rows = (
        await db.execute(
            select(Notification)
            .where(*conditions)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset(offset)
            .limit(limit)
        )
    ).scalars()
    return [_to_out(row) for row in rows], total


async def unread_count(db: AsyncSession, user_id: int) -> int:
    return int(
        await db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        )
        or 0
    )


async def mark_all_read(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await db.commit()
    return int(result.rowcount or 0)


async def mark_read(db: AsyncSession, user_id: int, notification_id: int) -> bool:
    """只标记自己的通知；别人的 id 猜到了也改不动（按不存在处理）。"""
    result = await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await db.commit()
    if result.rowcount:
        return True
    # 已经是已读状态也算成功，避免前端连点报错
    owner = await db.scalar(
        select(Notification.id).where(Notification.id == notification_id, Notification.user_id == user_id)
    )
    return owner is not None
