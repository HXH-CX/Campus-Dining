"""管理后台：食堂 / 商家 / 菜品 的完整 CRUD，以及应急删帖。

整个路由挂 get_current_admin 依赖，非管理员统一返回 40301。
"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, Paging, get_current_admin
from app.core.response import ApiResponse, PageData, ok, paginated
from app.schemas.admin import AdminOverviewOut
from app.schemas.catalog import (
    CanteenCreate,
    CanteenOut,
    CanteenUpdate,
    DishAvailabilityUpdate,
    DishCreate,
    DishOut,
    DishUpdate,
    MerchantCreate,
    MerchantOut,
    MerchantUpdate,
)
from app.schemas.post import PostOut
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["管理后台"], dependencies=[Depends(get_current_admin)])


# ---------------------------------------------------------------- 概览


@router.get("/overview", response_model=ApiResponse[AdminOverviewOut], summary="后台数据概览")
async def overview(db: DbSession):
    return ok(await admin_service.overview(db))


# ---------------------------------------------------------------- 食堂


@router.get("/canteens", response_model=ApiResponse[PageData[CanteenOut]], summary="食堂列表")
async def list_canteens(db: DbSession, paging: Paging):
    items, total = await admin_service.list_canteens(db, paging.offset, paging.limit)
    return paginated(items, total, paging.page, paging.page_size)


@router.post("/canteens", response_model=ApiResponse[CanteenOut], summary="创建食堂")
async def create_canteen(payload: CanteenCreate, db: DbSession):
    return ok(await admin_service.create_canteen(db, payload))


@router.put("/canteens/{canteen_id}", response_model=ApiResponse[CanteenOut], summary="修改食堂")
async def update_canteen(canteen_id: int, payload: CanteenUpdate, db: DbSession):
    return ok(await admin_service.update_canteen(db, canteen_id, payload))


@router.delete("/canteens/{canteen_id}", response_model=ApiResponse[None], summary="删除食堂")
async def delete_canteen(canteen_id: int, db: DbSession):
    await admin_service.delete_canteen(db, canteen_id)
    return ok(None, "已删除")


# ---------------------------------------------------------------- 商家


@router.get("/merchants", response_model=ApiResponse[PageData[MerchantOut]], summary="商家列表")
async def list_merchants(
    db: DbSession,
    paging: Paging,
    canteen_id: int | None = Query(None, description="按食堂筛选"),
):
    items, total = await admin_service.list_merchants(db, paging.offset, paging.limit, canteen_id)
    return paginated(items, total, paging.page, paging.page_size)


@router.post("/merchants", response_model=ApiResponse[MerchantOut], summary="创建商家")
async def create_merchant(payload: MerchantCreate, db: DbSession):
    return ok(await admin_service.create_merchant(db, payload))


@router.put("/merchants/{merchant_id}", response_model=ApiResponse[MerchantOut], summary="修改商家")
async def update_merchant(merchant_id: int, payload: MerchantUpdate, db: DbSession):
    return ok(await admin_service.update_merchant(db, merchant_id, payload))


@router.delete("/merchants/{merchant_id}", response_model=ApiResponse[None], summary="删除商家")
async def delete_merchant(merchant_id: int, db: DbSession):
    await admin_service.delete_merchant(db, merchant_id)
    return ok(None, "已删除")


# ---------------------------------------------------------------- 菜品


@router.get("/dishes", response_model=ApiResponse[PageData[DishOut]], summary="菜品列表")
async def list_dishes(
    db: DbSession,
    paging: Paging,
    merchant_id: int | None = Query(None, description="按商家筛选"),
    include_unavailable: bool = Query(True, description="是否包含已下架菜品"),
):
    items, total = await admin_service.list_dishes(
        db, paging.offset, paging.limit, merchant_id, include_unavailable
    )
    return paginated(items, total, paging.page, paging.page_size)


@router.post("/dishes", response_model=ApiResponse[DishOut], summary="创建菜品")
async def create_dish(payload: DishCreate, db: DbSession):
    return ok(await admin_service.create_dish(db, payload))


@router.put("/dishes/{dish_id}", response_model=ApiResponse[DishOut], summary="修改菜品")
async def update_dish(dish_id: int, payload: DishUpdate, db: DbSession):
    return ok(await admin_service.update_dish(db, dish_id, payload))


@router.patch(
    "/dishes/{dish_id}/availability",
    response_model=ApiResponse[DishOut],
    summary="上架 / 下架菜品",
)
async def set_dish_availability(dish_id: int, payload: DishAvailabilityUpdate, db: DbSession):
    return ok(await admin_service.set_dish_availability(db, dish_id, payload.is_available))


@router.delete("/dishes/{dish_id}", response_model=ApiResponse[None], summary="删除菜品（被引用时禁止）")
async def delete_dish(dish_id: int, db: DbSession):
    await admin_service.delete_dish(db, dish_id)
    return ok(None, "已删除")


# ---------------------------------------------------------------- 帖子（应急）


@router.get("/posts", response_model=ApiResponse[PageData[PostOut]], summary="帖子列表")
async def list_posts(
    db: DbSession,
    paging: Paging,
    keyword: str | None = Query(None, description="按帖子内容模糊搜索"),
):
    items, total = await admin_service.list_posts(db, paging.offset, paging.limit, keyword)
    return paginated(items, total, paging.page, paging.page_size)


@router.delete("/posts/{post_id}", response_model=ApiResponse[None], summary="应急删除帖子")
async def delete_post(post_id: int, db: DbSession):
    await admin_service.delete_post(db, post_id)
    return ok(None, "已删除")
