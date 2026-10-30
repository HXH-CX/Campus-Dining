"""统一响应体与分页封装。"""

from typing import Any, Generic, Sequence, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: T | None = None


class PageData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


def ok(data: Any = None, message: str = "ok") -> dict[str, Any]:
    return {"code": 0, "message": message, "data": data}


def paginated(items: Sequence[Any], total: int, page: int, page_size: int) -> dict[str, Any]:
    return {
        "code": 0,
        "message": "ok",
        "data": {"items": list(items), "total": total, "page": page, "page_size": page_size},
    }
