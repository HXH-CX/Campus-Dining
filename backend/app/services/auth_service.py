"""认证业务逻辑。"""

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, Unauthorized
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn
from app.services import login_guard


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


async def login(db: AsyncSession, payload: LoginIn, client_ip: str | None = None) -> tuple[User, str, int]:
    # 先看有没有被锁，锁定期内连密码都不校验，避免成为爆破的时间侧信道
    login_guard.ensure_allowed(payload.username, client_ip)

    user = await get_user_by_username(db, payload.username)
    # 用户名不存在与密码错误返回同一句提示，避免被用来枚举账号
    if user is None or not verify_password(payload.password, user.password_hash):
        login_guard.record_failure(payload.username, client_ip)
        raise Unauthorized("用户名或密码错误")

    login_guard.reset(payload.username, client_ip)
    token, expires_in = create_access_token(user.id, user.token_version)
    return user, token, expires_in


async def logout(db: AsyncSession, user: User) -> None:
    """登出：把令牌版本 +1，当前及此前签发的 token 全部失效。

    不做"只失效这一个"：那需要按 jti 建黑名单表并定期清理，
    而用户对"退出登录"的预期本来就是所有设备一起退。
    """
    await db.execute(update(User).where(User.id == user.id).values(token_version=User.token_version + 1))
    await db.commit()
