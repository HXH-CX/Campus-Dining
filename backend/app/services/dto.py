"""跨 service 复用的轻量 DTO 组装。

放在这里而不是 post_service，是因为 notify_service 也要用：
如果 notify_service 反过来从 post_service 拿，两个模块会互相 import。
"""

from app.core.titles import title_of
from app.models.user import User
from app.schemas.post import AuthorBrief


def author_brief(user: User) -> AuthorBrief:
    title = title_of(user.title_level)
    return AuthorBrief(
        id=user.id,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        title_level=user.title_level,
        title_name=title["name"],
        title_emoji=title["emoji"],
    )
