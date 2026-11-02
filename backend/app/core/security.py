"""密码哈希与 JWT 签发/校验。

说明：文档原写 passlib[bcrypt]，但 passlib 1.7.4 在 Python 3.13 上依赖已移除的
标准库 `crypt` 模块，容易在导入期直接报错；这里直接用官方 `bcrypt` 库，
接口语义一致，少一层维护停滞的中间件。已同步到 Tech Design 3.8。
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# bcrypt 只处理前 72 字节，超出部分会被截断；注册时也按此上限校验，避免"看起来能用实际无效"
BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")[:BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:BCRYPT_MAX_BYTES], password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        # 哈希串损坏时按"密码错误"处理，不把 500 抛给用户
        return False


def create_access_token(user_id: int, token_version: int = 0) -> tuple[str, int]:
    """返回 (token, 有效期秒数)。MVP 不做 refresh token，过期即重新登录。

    ver 是"令牌版本"：登出 / 改密时把 users.token_version +1，旧 token 立刻失效。
    JWT 本身无法撤回，这是不引入黑名单表就能做到吊销的最小代价。
    """
    expires_delta = timedelta(days=settings.JWT_EXPIRE_DAYS)
    expire_at = datetime.now(timezone.utc) + expires_delta
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "ver": token_version,
        "exp": expire_at,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> tuple[int, int] | None:
    """解出 (user_id, 令牌版本)；任何异常（过期/签名错/格式错）一律返回 None。

    ver 缺失时按 0 处理：这个字段是后加的，早期签发的 token 里没有它，
    而所有用户的 token_version 初始就是 0，这样老 token 不会被误判成失效。
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            return None
        return int(sub), int(payload.get("ver", 0))
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
