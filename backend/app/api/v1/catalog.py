"""食堂 / 商家 / 菜品 的公开只读接口（无需登录）。"""

from typing import Literal

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession, OptionalUser, Paging
from app.core.exceptions import Unauthorized
from app.core.response import ApiResponse, PageData, ok, paginated
from app.schemas.catalog import CanteenOut, DishOut, MerchantOut, RandomDishOut, RatingOut, WantResult
from app.services import catalog_service, want_service

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


# 同样要抢在 /dishes/{dish_id} 前面注册
@router.get(
    "/dishes/random",
    response_model=ApiResponse[RandomDishOut],
    summary="随机抽一道菜（今天吃什么）",
)
async def random_dish(
    db: DbSession,
    viewer: OptionalUser,
    source: Literal["auto", "wants"] = Query("auto", description="auto 高分池优先 / wants 只在我的想吃清单里抽"),
    min_rating: float = Query(4.0, ge=0, le=5, description="高分池的均分门槛"),
    min_count: int = Query(2, ge=1, le=100, description="高分池的最少评价人数"),
    exclude_id: int | None = Query(None, ge=1, description="想避开的菜品 id（「换一个」时传当前这道）"),
):
    wanted_by = None
    if source == "wants":
        if viewer is None:
            raise Unauthorized("登录后才能从想吃清单里抽")
        wanted_by = viewer.id
    return ok(
        await catalog_service.random_dish(
            db,
            min_rating=min_rating,
            min_count=min_count,
            exclude_id=exclude_id,
            wanted_by=wanted_by,
        )
    )


@router.get("/dishes/{dish_id}", response_model=ApiResponse[DishOut], summary="菜品详情")
async def get_dish(dish_id: int, db: DbSession, viewer: OptionalUser):
    return ok(
        await catalog_service.get_dish(db, dish_id, viewer_id=viewer.id if viewer else None, with_want=True)
    )


@router.post(
    "/dishes/{dish_id}/want",
    response_model=ApiResponse[WantResult],
    summary="加入 / 移出想吃清单",
)
async def toggle_want(dish_id: int, db: DbSession, current: CurrentUser):
    wanted, want_count = await want_service.toggle(db, current, dish_id)
    return ok(WantResult(wanted=wanted, want_count=want_count))


@router.get(
    "/dishes/{dish_id}/ratings",
    response_model=ApiResponse[PageData[RatingOut]],
    summary="菜品的打分记录",
)
async def list_dish_ratings(dish_id: int, db: DbSession, paging: Paging):
    items, total = await catalog_service.list_dish_ratings(db, dish_id, paging.offset, paging.limit)
    return paginated(items, total, paging.page, paging.page_size)
