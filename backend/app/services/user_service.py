"""用户对象的响应组装与资料修改。称号映射在这里做，路由层不碰文案。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.titles import achievement_of, title_of
from app.models.user import User
from app.schemas.user import AchievementOut, UserOut, UserUpdate


def to_user_out(user: User) -> UserOut:
    title = title_of(user.title_level)
    achievements = []
    for item in user.achievements:
        meta = achievement_of(item.code)
        achievements.append(
            AchievementOut(
                code=item.code,
                name=meta["name"],
                emoji=meta["emoji"],
                description=meta.get("description", ""),
                unlocked_at=item.unlocked_at,
            )
        )
    return UserOut(
        id=user.id,
        username=user.username,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        is_admin=user.is_admin,
        title_level=user.title_level,
        title_name=title["name"],
        title_emoji=title["emoji"],
        follower_count=user.follower_count,
        following_count=user.following_count,
        achievements=achievements,
        created_at=user.created_at,
    )


async def update_profile(db: AsyncSession, user: User, payload: UserUpdate) -> User:
    """只允许改昵称和头像；用户名是登录凭据，称号由贡献度计算，都不能在这里改。

    用 model_fields_set 区分"没传这个字段"和"传了空值"——前者不动，后者表示清空头像，
    否则用户永远删不掉自己的头像。
    """
    provided = payload.model_fields_set
    if "nickname" in provided and payload.nickname is not None:
        user.nickname = payload.nickname
    if "avatar_url" in provided:
        user.avatar_url = payload.avatar_url

    await db.commit()
    # 重新查一次，保证 achievements 这类 selectin 关系已加载
    refreshed = await db.execute(select(User).where(User.id == user.id))
    return refreshed.scalar_one()
