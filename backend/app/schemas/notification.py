"""站内通知的响应模型。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.post import AuthorBrief


class NotificationPostBrief(BaseModel):
    """通知里带一点原帖信息，让用户不必点进去就知道说的是哪条。

    正文只给原文，截断交给前端 line-clamp——按字符截会截在半个词上，
    不同宽度下的可读长度也不一样。
    """

    id: int
    dish_name: str
    content: str | None = None
    image_url: str | None = None


class NotificationOut(BaseModel):
    id: int
    type: Literal["like", "comment", "follow"]
    is_read: bool
    created_at: datetime
    actor: AuthorBrief
    post: NotificationPostBrief | None = None
    comment_content: str | None = None


class UnreadOut(BaseModel):
    count: int = 0


class MarkReadOut(BaseModel):
    updated: int = 0
    unread: int = 0
