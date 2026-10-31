"""帖子：发布、信息流、点赞、评论。

关键语义（PRD 2.3.3 定稿）：
- 发帖必带评分，评分写入 ratings 表走 upsert（一人一菜一条），冲突时覆盖而非报错。
- 评分覆盖后必须在同一事务内重算菜品聚合，避免首页评分与打分记录不一致。
- 帖子的展示分数 = 作者对该菜的**当前**评分，所以可能随作者再次发帖而变化。
"""

from sqlalchemy import and_, case, func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.exceptions import BadRequest, Forbidden, NotFound, Unauthorized
from app.core.titles import title_of
from app.models.catalog import Canteen, Dish, Merchant
from app.models.post import Comment, Like, Post
from app.models.rating import Rating
from app.models.social import Follow
from app.models.user import User
from app.schemas.post import (
    AuthorBrief,
    CommentOut,
    DishInPost,
    LikeResult,
    MerchantInPost,
    PostCreate,
    PostUpdate,
    PostOut,
)

SORT_LATEST = "latest"
SORT_HOT = "hot"
SORT_FOLLOWING = "following"
HOT_LIMIT = 10
HOT_WINDOW_HOURS = 24


def _followed_author_ids(user_id: int):
    """我关注的人的 id 子查询。

    用 IN 子查询而不是 join follows：帖子表对关注关系没有多对多，
    join 还要额外 distinct，反而更慢也更容易写错。
    不包含我自己——「关注」就是关注别人，自己的动态在个人主页看。
    """
    return select(Follow.following_id).where(Follow.follower_id == user_id)


def _base_query():
    """帖子 + 作者 + 菜品 + 商家 + 食堂 + 作者当前评分，一次查完。

    关系上配了 selectin 预加载，这里显式 join 后统一 noload 关掉，避免重复查询。
    """
    return (
        select(Post, User, Dish, Merchant, Canteen, Rating.score)
        .join(User, Post.user_id == User.id)
        .join(Dish, Post.dish_id == Dish.id)
        .join(Merchant, Dish.merchant_id == Merchant.id)
        .join(Canteen, Merchant.canteen_id == Canteen.id)
        .outerjoin(Rating, and_(Rating.user_id == Post.user_id, Rating.dish_id == Post.dish_id))
        .options(noload(Post.author), noload(Post.dish))
    )


def _author_brief(user: User) -> AuthorBrief:
    title = title_of(user.title_level)
    return AuthorBrief(
        id=user.id,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        title_level=user.title_level,
        title_name=title["name"],
        title_emoji=title["emoji"],
    )


def _to_post_out(row, is_liked: bool) -> PostOut:
    post, user, dish, merchant, canteen, score = row
    return PostOut(
        id=post.id,
        content=post.content,
        images=post.images or [],
        like_count=post.like_count,
        comment_count=post.comment_count,
        created_at=post.created_at,
        author=_author_brief(user),
        dish=DishInPost(
            id=dish.id,
            name=dish.name,
            image_url=dish.image_url,
            avg_rating=float(dish.avg_rating),
            rating_count=dish.rating_count,
            is_available=dish.is_available,
        ),
        merchant=MerchantInPost(id=merchant.id, name=merchant.name, canteen_name=canteen.name),
        author_score=score,
        is_liked=is_liked,
    )


async def _with_like_state(db: AsyncSession, rows, viewer: User | None) -> list[PostOut]:
    """批量补 is_liked，避免逐条查。"""
    if not rows:
        return []
    liked_ids: set[int] = set()
    if viewer is not None:
        post_ids = [row[0].id for row in rows]
        liked_ids = set(
            (
                await db.execute(
                    select(Like.post_id).where(Like.user_id == viewer.id, Like.post_id.in_(post_ids))
                )
            ).scalars()
        )
    return [_to_post_out(row, row[0].id in liked_ids) for row in rows]


async def _count_posts(
    db: AsyncSession,
    dish_id: int | None = None,
    merchant_id: int | None = None,
    user_id: int | None = None,
    keyword: str | None = None,
    following_of: int | None = None,
) -> int:
    stmt = select(func.count()).select_from(Post).join(Dish, Post.dish_id == Dish.id)
    if dish_id is not None:
        stmt = stmt.where(Post.dish_id == dish_id)
    if merchant_id is not None:
        stmt = stmt.where(Dish.merchant_id == merchant_id)
    if user_id is not None:
        stmt = stmt.where(Post.user_id == user_id)
    if keyword and keyword.strip():
        stmt = stmt.where(Post.content.like(f"%{keyword.strip()}%"))
    if following_of is not None:
        stmt = stmt.where(Post.user_id.in_(_followed_author_ids(following_of)))
    return int(await db.scalar(stmt) or 0)


async def list_posts(
    db: AsyncSession,
    *,
    offset: int,
    limit: int,
    viewer: User | None = None,
    sort: str = SORT_LATEST,
    dish_id: int | None = None,
    merchant_id: int | None = None,
    user_id: int | None = None,
    keyword: str | None = None,
) -> tuple[list[PostOut], int]:
    # 关注流必须先知道"我是谁"，匿名请求拿不到关注关系，直接 401 而不是返回空列表
    following_of: int | None = None
    if sort == SORT_FOLLOWING:
        if viewer is None:
            raise Unauthorized("登录后才能看关注动态")
        following_of = viewer.id

    total = await _count_posts(
        db,
        dish_id=dish_id,
        merchant_id=merchant_id,
        user_id=user_id,
        keyword=keyword,
        following_of=following_of,
    )

    stmt = _base_query()
    if dish_id is not None:
        stmt = stmt.where(Post.dish_id == dish_id)
    if merchant_id is not None:
        stmt = stmt.where(Dish.merchant_id == merchant_id)
    if user_id is not None:
        stmt = stmt.where(Post.user_id == user_id)
    if keyword and keyword.strip():
        stmt = stmt.where(Post.content.like(f"%{keyword.strip()}%"))
    if following_of is not None:
        stmt = stmt.where(Post.user_id.in_(_followed_author_ids(following_of)))

    if sort == SORT_HOT:
        # 与热榜同一公式，但不限 24h，用于"最热"排序
        hot_score = (Post.like_count + Post.comment_count * 2).label("hot_score")
        stmt = stmt.order_by(hot_score.desc(), Post.created_at.desc(), Post.id.desc())
    else:
        stmt = stmt.order_by(Post.created_at.desc(), Post.id.desc())

    rows = (await db.execute(stmt.offset(offset).limit(limit))).all()
    return await _with_like_state(db, rows, viewer), total


async def get_post(db: AsyncSession, post_id: int, viewer: User | None = None) -> PostOut:
    row = (await db.execute(_base_query().where(Post.id == post_id))).first()
    if row is None:
        raise NotFound("帖子不存在")
    items = await _with_like_state(db, [row], viewer)
    return items[0]


async def create_post(db: AsyncSession, user: User, payload: PostCreate) -> PostOut:
    dish = await db.get(Dish, payload.dish_id)
    if dish is None:
        raise NotFound("菜品不存在")
    if not dish.is_available:
        raise BadRequest("该菜品已下架，暂不支持发布")

    post = Post(
        user_id=user.id,
        dish_id=dish.id,
        content=payload.content,
        images=payload.images,
    )
    db.add(post)
    await db.flush()  # 拿到自增 id

    await _upsert_rating(db, user.id, dish.id, payload.score)
    await _recalc_dish(db, dish.id)

    await db.commit()
    return await get_post(db, post.id, viewer=user)


async def update_post(db: AsyncSession, user: User, post_id: int, payload: PostUpdate) -> PostOut:
    """编辑帖子文案与配图。

    POST 是"又去吃了一次"的表达，编辑是"上次那句话写错了"，所以这里不碰菜品和评分：
    改评分会连带影响菜品均分，那是重新表态，应该走发帖的 upsert。
    """
    post = await db.get(Post, post_id)
    if post is None:
        raise NotFound("帖子不存在")
    if post.user_id != user.id:
        raise Forbidden("只能编辑自己发布的帖子")

    # 用 model_fields_set 区分"没传这个字段"和"传了 null"：
    # 前者保持原样，后者才是一次有意的清空（比如删掉文案或删光配图）
    given = payload.model_fields_set
    if "content" in given:
        post.content = payload.content
    if "images" in given:
        post.images = payload.images or []

    await db.commit()
    return await get_post(db, post_id, viewer=user)


async def delete_post(db: AsyncSession, user: User, post_id: int) -> None:
    post = await db.get(Post, post_id)
    if post is None:
        raise NotFound("帖子不存在")
    if post.user_id != user.id:
        raise Forbidden("只能删除自己发布的帖子")
    # 评分是"我的看法"，独立于帖子，删帖不动评分；评论与点赞由外键级联清理
    await db.delete(post)
    await db.commit()


async def toggle_like(db: AsyncSession, user: User, post_id: int) -> LikeResult:
    post = await db.get(Post, post_id)
    if post is None:
        raise NotFound("帖子不存在")

    existing = (
        await db.execute(select(Like).where(Like.user_id == user.id, Like.post_id == post_id))
    ).scalar_one_or_none()

    if existing is not None:
        await db.delete(existing)
        await db.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(like_count=func.greatest(Post.like_count - 1, 0))
        )
        liked = False
    else:
        try:
            async with db.begin_nested():
                db.add(Like(user_id=user.id, post_id=post_id))
                await db.flush()
        except IntegrityError:
            # 并发重复点赞：唯一键已经挡住了，按"已点赞"处理即可
            return LikeResult(liked=True, like_count=await _read_like_count(db, post_id))
        await db.execute(update(Post).where(Post.id == post_id).values(like_count=Post.like_count + 1))
        liked = True

    await db.commit()
    return LikeResult(liked=liked, like_count=await _read_like_count(db, post_id))


async def _read_like_count(db: AsyncSession, post_id: int) -> int:
    return int(await db.scalar(select(Post.like_count).where(Post.id == post_id)) or 0)


async def list_comments(db: AsyncSession, post_id: int, offset: int, limit: int) -> tuple[list[CommentOut], int]:
    if await db.get(Post, post_id) is None:
        raise NotFound("帖子不存在")

    total = int(await db.scalar(select(func.count()).select_from(Comment).where(Comment.post_id == post_id)) or 0)
    rows = (
        await db.execute(
            select(Comment, User)
            .join(User, Comment.user_id == User.id)
            .where(Comment.post_id == post_id)
            .order_by(Comment.created_at.asc(), Comment.id.asc())
            .offset(offset)
            .limit(limit)
            .options(noload(Comment.author))
        )
    ).all()
    items = [
        CommentOut(id=c.id, content=c.content, created_at=c.created_at, author=_author_brief(u))
        for c, u in rows
    ]
    return items, total


async def add_comment(db: AsyncSession, user: User, post_id: int, content: str) -> CommentOut:
    if await db.get(Post, post_id) is None:
        raise NotFound("帖子不存在")
    comment = Comment(post_id=post_id, user_id=user.id, content=content)
    db.add(comment)
    await db.execute(update(Post).where(Post.id == post_id).values(comment_count=Post.comment_count + 1))
    await db.commit()
    await db.refresh(comment)
    return CommentOut(id=comment.id, content=comment.content, created_at=comment.created_at, author=_author_brief(user))


async def delete_comment(db: AsyncSession, user: User, post_id: int, comment_id: int) -> int:
    """删除评论，返回该帖最新的评论数。

    权限：本人删自己的，管理员可删任意（应急兜底，与删帖同一套思路）。
    comment_count 跟着减：热榜权重是评论×2，计数不准会直接影响排序。
    """
    comment = await db.get(Comment, comment_id)
    # 评论不属于这篇帖子时也按不存在处理，避免有人顺着 id 猜别处的评论
    if comment is None or comment.post_id != post_id:
        raise NotFound("评论不存在")
    if comment.user_id != user.id and not user.is_admin:
        raise Forbidden("只能删除自己的评论")

    await db.delete(comment)
    await db.execute(
        update(Post)
        .where(Post.id == post_id)
        # 用 CASE 兜底：comment_count 是 unsigned，直接 -1 在计数为 0 时会报 out of range
        .values(comment_count=case((Post.comment_count > 0, Post.comment_count - 1), else_=0))
    )
    await db.commit()

    remaining = await db.scalar(select(Post.comment_count).where(Post.id == post_id))
    return int(remaining or 0)


async def list_hot(db: AsyncSession, limit: int = HOT_LIMIT, viewer: User | None = None) -> list[PostOut]:
    """24 小时热榜：点赞×1 + 评论×2，取 Top N。"""
    stmt = (
        _base_query()
        .where(Post.created_at >= text(f"NOW() - INTERVAL {HOT_WINDOW_HOURS} HOUR"))
        .order_by(
            (Post.like_count + Post.comment_count * 2).desc(),
            Post.created_at.desc(),
        )
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return await _with_like_state(db, rows, viewer)


# ---------------------------------------------------------------- 内部：评分与聚合

async def _upsert_rating(db: AsyncSession, user_id: int, dish_id: int, score: int) -> None:
    """一人一菜一条：冲突时覆盖分数并刷新 updated_at（称号统计依赖它）。

    用 ORM 而不是 INSERT ... ON DUPLICATE KEY UPDATE：后者在 MySQL 8.0.20 起
    VALUES() 函数已废弃，会持续刷弃用警告；这里并发冲突交给唯一键和 IntegrityError 兜底。
    """
    existing = (
        await db.execute(select(Rating).where(Rating.user_id == user_id, Rating.dish_id == dish_id))
    ).scalar_one_or_none()

    if existing is not None:
        existing.score = score
        existing.updated_at = func.now()  # 分数没变也要刷新时间，否则 30 天窗口不会顺延
        # 必须显式 flush：后面 _recalc_dish 是原生 SQL，不会带上未提交的内存变更
        await db.flush()
        return

    db.add(Rating(user_id=user_id, dish_id=dish_id, score=score))
    try:
        # 用 SAVEPOINT 包一层：并发冲突回滚到存档点，不会连累外层已经 flush 的帖子
        async with db.begin_nested():
            await db.flush()
    except IntegrityError:
        fallback = (
            await db.execute(select(Rating).where(Rating.user_id == user_id, Rating.dish_id == dish_id))
        ).scalar_one_or_none()
        if fallback is not None:
            fallback.score = score
            fallback.updated_at = func.now()


async def _recalc_dish(db: AsyncSession, dish_id: int) -> None:
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
