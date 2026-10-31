"""用户：个人信息、帖子、评价、评论、关注/粉丝。"""

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession, OptionalUser, Paging
from app.core.exceptions import Forbidden, NotFound
from app.core.response import ApiResponse, PageData, ok, paginated
from app.models.user import User
from app.schemas.catalog import DishOut
from app.schemas.post import PostOut
from app.schemas.user import UserCard, UserCommentOut, UserOut, UserRatingOut, UserUpdate
from app.services import post_service, social_service, title_service, user_service, want_service
from app.services.user_service import to_user_out

router = APIRouter(prefix="/users", tags=["用户"])


@router.get("", response_model=ApiResponse[PageData[UserCard]], summary="用户搜索（按昵称）")
async def search_users_route(
    db: DbSession,
    paging: Paging,
    viewer: OptionalUser,
    keyword: str = Query("", max_length=50, description="按昵称模糊匹配，留空返回全部用户"),
):
    items, total = await social_service.search_users(db, keyword, viewer, paging.offset, paging.limit)
    return paginated(items, total, paging.page, paging.page_size)


# 注意：/me 必须注册在 /{user_id} 之前，否则会被路径参数吞掉
@router.get("/me", response_model=ApiResponse[UserOut], summary="当前登录用户（顺带懒更新称号）")
async def read_me(db: DbSession, current: CurrentUser):
    fresh = await title_service.refresh(db, current)
    return ok(to_user_out(fresh))


@router.put("/me", response_model=ApiResponse[UserOut], summary="修改昵称 / 头像")
async def update_me(payload: UserUpdate, db: DbSession, current: CurrentUser):
    user = await user_service.update_profile(db, current, payload)
    return ok(to_user_out(user))


@router.get("/{user_id}", response_model=ApiResponse[UserOut], summary="用户公开主页信息")
async def read_user(user_id: int, db: DbSession):
    user = await db.get(User, user_id)
    if user is None:
        raise NotFound("用户不存在")
    return ok(to_user_out(user))


@router.get("/{user_id}/posts", response_model=ApiResponse[PageData[PostOut]], summary="某用户的帖子")
async def user_posts(user_id: int, db: DbSession, paging: Paging, viewer: OptionalUser):
    if await db.get(User, user_id) is None:
        raise NotFound("用户不存在")
    items, total = await post_service.list_posts(
        db, offset=paging.offset, limit=paging.limit, viewer=viewer, user_id=user_id
    )
    return paginated(items, total, paging.page, paging.page_size)


# 只对自己开放：点过赞什么是隐私，不该被同学翻出来
@router.get(
    "/{user_id}/liked-posts",
    response_model=ApiResponse[PageData[PostOut]],
    summary="我赞过的帖子（仅本人）",
)
async def user_liked_posts(user_id: int, db: DbSession, paging: Paging, current: CurrentUser):
    if current.id != user_id:
        raise Forbidden("只能查看自己的点赞")
    items, total = await post_service.list_liked_posts(db, user_id, paging.offset, paging.limit, current)
    return paginated(items, total, paging.page, paging.page_size)


@router.get(
    "/{user_id}/ratings",
    response_model=ApiResponse[PageData[UserRatingOut]],
    summary="某用户的评价记录（我的评价）",
)
async def user_ratings(user_id: int, db: DbSession, paging: Paging):
    items, total = await social_service.list_user_ratings(db, user_id, paging.offset, paging.limit)
    return paginated(items, total, paging.page, paging.page_size)


@router.get(
    "/{user_id}/comments",
    response_model=ApiResponse[PageData[UserCommentOut]],
    summary="某用户发过的评论（我的评论）",
)
async def user_comments(user_id: int, db: DbSession, paging: Paging):
    items, total = await social_service.list_user_comments(db, user_id, paging.offset, paging.limit)
    return paginated(items, total, paging.page, paging.page_size)


@router.get(
    "/{user_id}/wants",
    response_model=ApiResponse[PageData[DishOut]],
    summary="想吃清单（最近加的在前）",
)
async def user_wants(user_id: int, db: DbSession, paging: Paging):
    items, total = await want_service.list_wants(db, user_id, paging.offset, paging.limit)
    return paginated(items, total, paging.page, paging.page_size)


@router.get(
    "/{user_id}/followers",
    response_model=ApiResponse[PageData[UserCard]],
    summary="粉丝列表（带互关标记）",
)
async def user_followers(user_id: int, db: DbSession, paging: Paging, viewer: OptionalUser):
    items, total = await social_service.list_followers(db, user_id, viewer, paging.offset, paging.limit)
    return paginated(items, total, paging.page, paging.page_size)


@router.get(
    "/{user_id}/following",
    response_model=ApiResponse[PageData[UserCard]],
    summary="关注列表（带互关标记）",
)
async def user_following(user_id: int, db: DbSession, paging: Paging, viewer: OptionalUser):
    items, total = await social_service.list_following(db, user_id, viewer, paging.offset, paging.limit)
    return paginated(items, total, paging.page, paging.page_size)


@router.post("/{user_id}/follow", response_model=ApiResponse[dict], summary="关注 / 取消关注")
async def follow(user_id: int, db: DbSession, current: CurrentUser):
    following = await social_service.toggle_follow(db, current, user_id)
    return ok({"following": following})
