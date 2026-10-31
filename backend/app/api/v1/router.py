"""v1 路由汇总。

按域拆模块，逐个 include；未实现的域先注释占位，避免空路由污染 OpenAPI。
"""

from fastapi import APIRouter

from app.api.v1 import admin, auth, catalog, notifications, posts, uploads, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(uploads.router)
api_router.include_router(catalog.router)
api_router.include_router(posts.router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)

# 全部 v1 模块已接入；后续新增按域拆文件再 include 即可。
