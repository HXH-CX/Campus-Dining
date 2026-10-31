"""站内通知：列表、未读数、标记已读。"""

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession, Paging
from app.core.exceptions import NotFound
from app.core.response import ApiResponse, PageData, ok, paginated
from app.schemas.notification import MarkReadOut, NotificationOut, UnreadOut
from app.services import notify_service

router = APIRouter(prefix="/notifications", tags=["通知"])


@router.get("", response_model=ApiResponse[PageData[NotificationOut]], summary="通知列表")
async def list_notifications(
    db: DbSession,
    current: CurrentUser,
    paging: Paging,
    unread_only: bool = Query(False, description="只看未读"),
):
    items, total = await notify_service.list_notifications(
        db, current.id, paging.offset, paging.limit, unread_only=unread_only
    )
    return paginated(items, total, paging.page, paging.page_size)


@router.get("/unread-count", response_model=ApiResponse[UnreadOut], summary="未读数（铃铛红点）")
async def unread_count(db: DbSession, current: CurrentUser):
    return ok(UnreadOut(count=await notify_service.unread_count(db, current.id)))


@router.post("/read", response_model=ApiResponse[MarkReadOut], summary="全部标为已读")
async def mark_all_read(db: DbSession, current: CurrentUser):
    updated = await notify_service.mark_all_read(db, current.id)
    return ok(MarkReadOut(updated=updated, unread=0))


@router.post("/{notification_id}/read", response_model=ApiResponse[MarkReadOut], summary="单条标为已读")
async def mark_read(notification_id: int, db: DbSession, current: CurrentUser):
    if not await notify_service.mark_read(db, current.id, notification_id):
        raise NotFound("通知不存在")
    return ok(MarkReadOut(updated=1, unread=await notify_service.unread_count(db, current.id)))
