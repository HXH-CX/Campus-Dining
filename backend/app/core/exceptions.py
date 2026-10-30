"""业务异常与全局错误码。

约定：路由/服务层只抛 BizError 子类，由 main.py 里的处理器统一包装成
{"code": ..., "message": ..., "data": null}，不允许路由自己拼 dict。
"""

from typing import Any


class ErrorCode:
    OK = 0
    BAD_REQUEST = 40001
    UNAUTHORIZED = 40101
    FORBIDDEN = 40301
    NOT_FOUND = 40401
    CONFLICT = 40901
    TOO_MANY_REQUESTS = 42901
    INTERNAL_ERROR = 50000


# 业务码 -> HTTP 状态码
CODE_TO_HTTP: dict[int, int] = {
    ErrorCode.OK: 200,
    ErrorCode.BAD_REQUEST: 400,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.TOO_MANY_REQUESTS: 429,
    ErrorCode.INTERNAL_ERROR: 500,
}


class BizError(Exception):
    """所有可预期业务异常的基类。"""

    code: int = ErrorCode.BAD_REQUEST

    def __init__(self, message: str = "请求失败", *, data: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.data = data

    @property
    def http_status(self) -> int:
        return CODE_TO_HTTP.get(self.code, 400)


class BadRequest(BizError):
    code = ErrorCode.BAD_REQUEST


class Unauthorized(BizError):
    code = ErrorCode.UNAUTHORIZED

    def __init__(self, message: str = "未登录或登录已过期") -> None:
        super().__init__(message)


class Forbidden(BizError):
    code = ErrorCode.FORBIDDEN

    def __init__(self, message: str = "无权执行该操作") -> None:
        super().__init__(message)


class NotFound(BizError):
    code = ErrorCode.NOT_FOUND

    def __init__(self, message: str = "资源不存在") -> None:
        super().__init__(message)


class Conflict(BizError):
    code = ErrorCode.CONFLICT


class TooManyRequests(BizError):
    code = ErrorCode.TOO_MANY_REQUESTS

    def __init__(self, message: str = "操作太频繁，请稍后再试") -> None:
        super().__init__(message)
