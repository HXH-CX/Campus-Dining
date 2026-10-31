"""关注关系、"我的评价"与"我的评论"。

关注是单向的，互关不单独建模：两侧都能查到边即为互关，查询时推导 is_mutual。
"""

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequest, NotFound
from app.core.titles import title_of
from app.models.catalog import Dish
from app.models.post import Comment, Post
from app.models.rating import Rating
from app.models.social import NOTIFY_FOLLOW, Follow
from app.models.user import User
from app.schemas.catalog import DishBrief
from app.schemas.user import CommentedPost, UserCard, UserCommentOut, UserRatingOut
from app.services import notify_service


async def toggle_follow(db: AsyncSession, follower: User, target_id: int) -> bool:
    """返回操作后的关注状态。"""
    if target_id == follower.id:
        raise BadRequest("不能关注自己")
    if await db.get(User, target_id) is None:
        raise NotFound("用户不存在")

    existing = (
        await db.execute(
            select(Follow).where(Follow.follower_id == follower.id, Follow.following_id == target_id)
        )
    ).scalar_one_or_none()

    if existing is not None:
        await db.delete(existing)
        await db.execute(
            update(User).where(User.id == target_id).values(follower_count=func.greatest(User.follower_count - 1, 0))
        )
        await db.execute(
            update(User).where(User.id == follower.id).values(following_count=func.greatest(User.following_count - 1, 0))
        )
        # 取关后撤回关注通知：作者点开发现自己并没有新粉丝会莫名其妙
        await notify_service.revoke(db, user_id=target_id, actor_id=follower.id, type_=NOTIFY_FOLLOW)
        following = False
    else:
        db.add(Follow(follower_id=follower.id, following_id=target_id))
        await db.execute(update(User).where(User.id == target_id).values(follower_count=User.follower_count + 1))
        await db.execute(update(User).where(User.id == follower.id).values(following_count=User.following_count + 1))
        await notify_service.push(db, user_id=target_id, actor_id=follower.id, type_=NOTIFY_FOLLOW)
        following = True

    await db.commit()
    return following


async def list_followers(
    db: AsyncSession, user_id: int, viewer: User | None, offset: int, limit: int
) -> tuple[list[UserCard], int]:
    await _ensure_user(db, user_id)
    total = int(
        await db.scalar(select(func.count()).select_from(Follow).where(Follow.following_id == user_id)) or 0
    )
    ids = (
        await db.execute(
            select(Follow.follower_id)
            .where(Follow.following_id == user_id)
            .order_by(Follow.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).scalars().all()
    return await _cards(db, list(ids), user_id, viewer), total


async def list_following(
    db: AsyncSession, user_id: int, viewer: User | None, offset: int, limit: int
) -> tuple[list[UserCard], int]:
    await _ensure_user(db, user_id)
    total = int(
        await db.scalar(select(func.count()).select_from(Follow).where(Follow.follower_id == user_id)) or 0
    )
    ids = (
        await db.execute(
            select(Follow.following_id)
            .where(Follow.follower_id == user_id)
            .order_by(Follow.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).scalars().all()
    return await _cards(db, list(ids), user_id, viewer), total


async def _ensure_user(db: AsyncSession, user_id: int) -> None:
    if await db.get(User, user_id) is None:
        raise NotFound("用户不存在")


async def _cards(
    db: AsyncSession, ids: list[int], owner_id: int, viewer: User | None
) -> list[UserCard]:
    if not ids:
        return []

    users = {u.id: u for u in (await db.execute(select(User).where(User.id.in_(ids)))).scalars().all()}

    # owner -> 列表里的人（用于互关判定）
    owner_to_ids = set(
        (
            await db.execute(
                select(Follow.following_id).where(Follow.follower_id == owner_id, Follow.following_id.in_(ids))
            )
        ).scalars()
    )
    # 列表里的人 -> owner
    ids_to_owner = set(
        (
            await db.execute(
                select(Follow.follower_id).where(Follow.following_id == owner_id, Follow.follower_id.in_(ids))
            )
        ).scalars()
    )
    viewer_following: set[int] = set()
    if viewer is not None:
        viewer_following = set(
            (
                await db.execute(
                    select(Follow.following_id).where(
                        Follow.follower_id == viewer.id, Follow.following_id.in_(ids)
                    )
                )
            ).scalars()
        )

    cards: list[UserCard] = []
    for user_id in ids:  # 保持列表顺序
        user = users.get(user_id)
        if user is None:
            continue
        title = title_of(user.title_level)
        cards.append(
            UserCard(
                id=user.id,
                nickname=user.nickname,
                avatar_url=user.avatar_url,
                title_level=user.title_level,
                title_name=title["name"],
                title_emoji=title["emoji"],
                is_mutual=user_id in owner_to_ids and user_id in ids_to_owner,
                followed_by_me=user_id in viewer_following,
            )
        )
    return cards


async def list_user_ratings(
    db: AsyncSession, user_id: int, offset: int, limit: int
) -> tuple[list[UserRatingOut], int]:
    await _ensure_user(db, user_id)
    total = int(await db.scalar(select(func.count()).select_from(Rating).where(Rating.user_id == user_id)) or 0)
    rows = (
        await db.execute(
            select(Rating, Dish)
            .join(Dish, Rating.dish_id == Dish.id)
            .where(Rating.user_id == user_id)
            .order_by(Rating.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    items = [
        UserRatingOut(
            dish=DishBrief(
                id=dish.id,
                name=dish.name,
                image_url=dish.image_url,
                avg_rating=float(dish.avg_rating),
                rating_count=dish.rating_count,
            ),
            score=rating.score,
            updated_at=rating.updated_at,
        )
        for rating, dish in rows
    ]
    return items, total


async def list_user_comments(
    db: AsyncSession, user_id: int, offset: int, limit: int
) -> tuple[list[UserCommentOut], int]:
    """某人发过的评论，带上所属帖子信息，便于跳回原帖。

    评论与帖子是级联关系，帖子被删则评论一起没，所以这里不会出现孤立的评论。
    """
    await _ensure_user(db, user_id)
    total = int(
        await db.scalar(select(func.count()).select_from(Comment).where(Comment.user_id == user_id)) or 0
    )
    rows = (
        await db.execute(
            select(Comment, Post, Dish)
            .join(Post, Comment.post_id == Post.id)
            .join(Dish, Post.dish_id == Dish.id)
            .where(Comment.user_id == user_id)
            .order_by(Comment.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()

    items: list[UserCommentOut] = []
    for comment, post, dish in rows:
        images = post.images or []
        text = (post.content or "").replace("\n", " ").strip()
        items.append(
            UserCommentOut(
                id=comment.id,
                content=comment.content,
                created_at=comment.created_at,
                post=CommentedPost(
                    id=post.id,
                    dish_name=dish.name,
                    excerpt=text[:40] or None,
                    # 帖子没配图就退回菜品封面，列表里总有个缩略图
                    image_url=(images[0] if images else dish.image_url),
                ),
            )
        )
    return items, total
