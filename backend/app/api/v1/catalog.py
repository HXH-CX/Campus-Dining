"""食堂 / 商家 / 菜品 的公开只读接口（无需登录）。"""

from fastapi import APIRouter, Query

from app.api.deps import DbSession, Paging
from app.core.response import ApiResponse, PageData, ok, paginated
from app.schemas.catalog import CanteenOut, DishOut, MerchantOut, RatingOut
from app.services import catalog_service

router = APIRouter(tags=["食堂与菜品"])


@router.get("/canteens", response_model=ApiResponse[list[CanteenOut]], summary="食堂列表")
async def list_canteens(db: DbSession):
    return ok(await catalog_service.list_canteens(db))


@router.get(
    "/canteens/{canteen_id}/merchants",
    response_model=ApiResponse[list[MerchantOut]],
    summary="某食堂下的商家列表",
)
async def list_merchants(canteen_id: int, db: DbSession):
    await catalog_service.get_canteen(db, canteen_id)  # 食堂不存在直接 404
    return ok(await catalog_service.list_merchants(db, canteen_id=canteen_id))


@router.get("/merchants/{merchant_id}", response_model=ApiResponse[MerchantOut], summary="商家详情")
async def get_merchant(merchant_id: int, db: DbSession):
    return ok(await catalog_service.get_merchant(db, merchant_id))


@router.get(
    "/merchants/{merchant_id}/dishes",
    response_model=ApiResponse[list[DishOut]],
    summary="商家菜品列表",
)
async def list_dishes(
    merchant_id: int,
    db: DbSession,
    include_unavailable: bool = Query(False, description="是否包含已下架菜品"),
):
    return ok(await catalog_service.list_dishes(db, merchant_id, include_unavailable=include_unavailable))


@router.get("/dishes", response_model=ApiResponse[PageData[DishOut]], summary="菜品搜索 / 全部菜品")
async def search_dishes_route(
    db: DbSession,
    paging: Paging,
    keyword: str = Query("", max_length=50, description="按菜名或商家名模糊匹配，留空返回全部"),
):
    items, total = await catalog_service.search_dishes(db, keyword, paging.offset, paging.limit)
    return paginated(items, total, paging.page, paging.page_size)


# 注意：/dishes/top 必须注册在 /dishes/{dish_id} 之前，否则会被路径参数吞掉（返回 422 而非榜单）
@router.get("/dishes/top", response_model=ApiResponse[list[DishOut]], summary="高分榜（够分且够人评）")
async def top_dishes(
    db: DbSession,
    min_rating: float = Query(4.0, ge=0, le=5, description="最低均分"),
    min_count: int = Query(2, ge=1, le=100, description="最少评价人数，防止一人打五星就登顶"),
    limit: int = Query(6, ge=1, le=20),
):
    return ok(await catalog_service.top_dishes(db, min_rating, min_count, limit))


@router.get("/dishes/{dish_id}", response_model=ApiResponse[DishOut], summary="菜品详情")
async def get_dish(dish_id: int, db: DbSession):
    return ok(await catalog_service.get_dish(db, dish_id))


@router.get(
    "/dishes/{dish_id}/ratings",
    response_model=ApiResponse[PageData[RatingOut]],
    summary="菜品的打分记录",
)
async def list_dish_ratings(dish_id: int, db: DbSession, paging: Paging):
    items, total = await catalog_service.list_dish_ratings(db, dish_id, paging.offset, paging.limit)
    return paginated(items, total, paging.page, paging.page_size)
