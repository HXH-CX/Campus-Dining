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


def create_access_token(user_id: int) -> tuple[str, int]:
    """返回 (token, 有效期秒数)。MVP 不做 refresh token，过期即重新登录。"""
    expires_delta = timedelta(days=settings.JWT_EXPIRE_DAYS)
    expire_at = datetime.now(timezone.utc) + expires_delta
    payload: dict[str, Any] = {"sub": str(user_id), "exp": expire_at, "iat": datetime.now(timezone.utc)}
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> int | None:
    """解出 user_id；任何异常（过期/签名错/格式错）一律返回 None。"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
