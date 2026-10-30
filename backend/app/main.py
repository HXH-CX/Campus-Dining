"""FastAPI 应用入口。

约定：所有异常（业务异常 / 参数校验 / HTTPException / 未捕获异常）
都由本文件的处理器统一包装成 {code, message, data}，路由层不自己拼 dict。
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import BizError, ErrorCode
from app.core.response import ok
from app.db.session import AsyncSessionLocal, dispose_engine
from app.services import hot_service

logger = logging.getLogger("app")

_HTTP_STATUS_TO_CODE = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.BAD_REQUEST,
    429: ErrorCode.TOO_MANY_REQUESTS,
}


def _error(status_code: int, code: int, message: str, data: Any = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": code, "message": message, "data": data})


async def _refresh_hot_cache() -> None:
    """定时/启动时预热热榜。失败不能影响主流程——接口有按需重算兜底。"""
    try:
        async with AsyncSessionLocal() as session:
            await hot_service.refresh(session)
    except Exception:  # noqa: BLE001
        logger.exception("热榜预热失败，已降级为按需重算")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    await _refresh_hot_cache()  # 启动即预热，首页首次访问不用等

    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        _refresh_hot_cache,
        "interval",
        seconds=settings.HOT_CACHE_TTL_SECONDS,
        id="hot_cache_refresh",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="校园美食点评与分享社区 API",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- 异常处理器 ----
    @app.exception_handler(BizError)
    async def handle_biz_error(request: Request, exc: BizError) -> JSONResponse:
        return _error(exc.http_status, exc.code, exc.message, exc.data)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        message = "参数校验失败"
        if errors:
            first = errors[0]
            location = ".".join(str(part) for part in first.get("loc", ()) if part not in ("body", "query", "path"))
            detail = first.get("msg", "参数错误")
            message = f"{location}: {detail}" if location else detail
        return _error(400, ErrorCode.BAD_REQUEST, message)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_STATUS_TO_CODE.get(exc.status_code, ErrorCode.INTERNAL_ERROR if exc.status_code >= 500 else ErrorCode.BAD_REQUEST)
        return _error(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("未捕获异常: %s %s", request.method, request.url.path)
        message = "服务器内部错误" if not settings.DEBUG else f"{type(exc).__name__}: {exc}"
        return _error(500, ErrorCode.INTERNAL_ERROR, message)

    # ---- 系统探针 ----
    @app.get("/health", tags=["系统"], summary="服务存活检查")
    async def health():
        return ok({"status": "ok", "version": settings.APP_VERSION})

    @app.get("/health/db", tags=["系统"], summary="数据库连通性检查")
    async def health_db():
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
        except Exception as exc:  # noqa: BLE001 - 探针就是要吞掉异常给出可读结论
            return _error(500, ErrorCode.INTERNAL_ERROR, f"数据库连接失败: {type(exc).__name__}: {exc}")
        return ok({"database": "up"})

    # ---- 业务路由与静态资源 ----
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # 上传目录必须先存在，StaticFiles 在初始化时就会校验
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(settings.upload_path)), name="uploads")

    return app


app = create_app()
