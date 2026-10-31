"""社区：发帖、信息流、热榜、点赞、评论。"""

from typing import Literal

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession, OptionalUser, Paging
from app.core.response import ApiResponse, PageData, ok, paginated
from app.schemas.post import CommentCreate, CommentOut, LikeResult, PostCreate, PostOut, PostUpdate
from app.services import catalog_service, hot_service, post_service, title_service

router = APIRouter(tags=["社区"])


@router.post("/posts", response_model=ApiResponse[PostOut], summary="发布帖子（含菜品评分）")
async def create_post(payload: PostCreate, db: DbSession, current: CurrentUser):
    post = await post_service.create_post(db, current, payload)
    hot_service.invalidate()  # 新帖立刻有机会进榜
    await title_service.refresh(db, current)  # 发帖后懒更新称号
    return ok(post)


@router.get(
    "/posts/feed",
    response_model=ApiResponse[PageData[PostOut]],
    summary="信息流（latest / hot）",
)
async def feed(
    db: DbSession,
    paging: Paging,
    viewer: OptionalUser,
    sort: Literal["latest", "hot"] = "latest",
    keyword: str = Query("", max_length=50, description="按帖子文案模糊匹配"),
):
    items, total = await post_service.list_posts(
        db, offset=paging.offset, limit=paging.limit, viewer=viewer, sort=sort, keyword=keyword
    )
    return paginated(items, total, paging.page, paging.page_size)


@router.get("/posts/hot", response_model=ApiResponse[list[PostOut]], summary="24小时热榜 Top10")
async def hot(db: DbSession, viewer: OptionalUser):
    return ok(await hot_service.get_hot(db, viewer))


@router.get("/posts/{post_id}", response_model=ApiResponse[PostOut], summary="帖子详情")
async def read_post(post_id: int, db: DbSession, viewer: OptionalUser):
    return ok(await post_service.get_post(db, post_id, viewer=viewer))


@router.put("/posts/{post_id}", response_model=ApiResponse[PostOut], summary="编辑自己的帖子（文案与配图）")
async def update_post(post_id: int, payload: PostUpdate, db: DbSession, current: CurrentUser):
    post = await post_service.update_post(db, current, post_id, payload)
    # 文案变了会影响关键词搜索，但互动数没变，热榜排序不受影响，无需 invalidate
    return ok(post)


@router.delete("/posts/{post_id}", response_model=ApiResponse[None], summary="删除自己的帖子")
async def delete_post(post_id: int, db: DbSession, current: CurrentUser):
    await post_service.delete_post(db, current, post_id)
    hot_service.invalidate()
    return ok(None, "已删除")


@router.post("/posts/{post_id}/like", response_model=ApiResponse[LikeResult], summary="点赞 / 取消点赞")
async def toggle_like(post_id: int, db: DbSession, current: CurrentUser):
    result = await post_service.toggle_like(db, current, post_id)
    hot_service.invalidate()
    return ok(result)


@router.get(
    "/posts/{post_id}/comments",
    response_model=ApiResponse[PageData[CommentOut]],
    summary="评论列表",
)
async def list_comments(post_id: int, db: DbSession, paging: Paging):
    items, total = await post_service.list_comments(db, post_id, paging.offset, paging.limit)
    return paginated(items, total, paging.page, paging.page_size)


@router.post("/posts/{post_id}/comments", response_model=ApiResponse[CommentOut], summary="发表评论")
async def add_comment(post_id: int, payload: CommentCreate, db: DbSession, current: CurrentUser):
    comment = await post_service.add_comment(db, current, post_id, payload.content)
    hot_service.invalidate()  # 评论权重是点赞的 2 倍，榜单会变
    return ok(comment)


# ---------------------------------------------------------------- 按商家 / 菜品查帖子


@router.get(
    "/merchants/{merchant_id}/posts",
    response_model=ApiResponse[PageData[PostOut]],
    summary="某商家下的帖子",
)
async def merchant_posts(merchant_id: int, db: DbSession, paging: Paging, viewer: OptionalUser):
    await catalog_service.get_merchant(db, merchant_id)  # 商家不存在直接 404
    items, total = await post_service.list_posts(
        db, offset=paging.offset, limit=paging.limit, viewer=viewer, merchant_id=merchant_id
    )
    return paginated(items, total, paging.page, paging.page_size)


@router.get(
    "/dishes/{dish_id}/posts",
    response_model=ApiResponse[PageData[PostOut]],
    summary="某菜品下的帖子",
)
async def dish_posts(dish_id: int, db: DbSession, paging: Paging, viewer: OptionalUser):
    await catalog_service.get_dish(db, dish_id)  # 菜品不存在直接 404
    items, total = await post_service.list_posts(
        db, offset=paging.offset, limit=paging.limit, viewer=viewer, dish_id=dish_id
    )
    return paginated(items, total, paging.page, paging.page_size)
