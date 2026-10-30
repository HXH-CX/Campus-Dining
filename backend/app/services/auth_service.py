"""认证业务逻辑。"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, Unauthorized
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def register(db: AsyncSession, payload: RegisterIn) -> User:
    if await get_user_by_username(db, payload.username) is not None:
        raise Conflict("该用户名已被注册")

    user = User(
        username=payload.username,
        nickname=payload.nickname,
        password_hash=hash_password(payload.password),
        title_level=1,  # 注册即 Lv.1 干饭练习生
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        # 并发注册同名时兜底，靠数据库唯一键裁决
        await db.rollback()
        raise Conflict("该用户名已被注册") from None

    # commit 后重新查一次，确保 selectin 关系（achievements）已加载，序列化时不触发异步懒加载
    refreshed = await db.execute(select(User).where(User.id == user.id))
    return refreshed.scalar_one()


async def login(db: AsyncSession, payload: LoginIn) -> tuple[User, str, int]:
    user = await get_user_by_username(db, payload.username)
    # 用户名不存在与密码错误返回同一句提示，避免被用来枚举账号
    if user is None or not verify_password(payload.password, user.password_hash):
        raise Unauthorized("用户名或密码错误")

    token, expires_in = create_access_token(user.id)
    return user, token, expires_in
