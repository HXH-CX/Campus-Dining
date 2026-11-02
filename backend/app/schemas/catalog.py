"""食堂 / 商家 / 菜品相关的请求与响应模型。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.tags import clean_tags


# ---------------------------------------------------------------- 输出


class CanteenOut(BaseModel):
    id: int
    name: str
    merchant_count: int = 0


class MerchantOut(BaseModel):
    id: int
    name: str
    canteen_id: int
    canteen_name: str
    overall_rating: float = Field(description="上架菜品按评价数加权的综合评分")
    dish_count: int = 0


class DishOut(BaseModel):
    id: int
    name: str
    image_url: str | None = None
    merchant_id: int
    merchant_name: str
    canteen_name: str
    avg_rating: float
    rating_count: int
    is_available: bool
    # 口味/形态标签，白名单见 app/core/tags.py
    tags: list[str] = Field(default_factory=list)
    # 想吃清单相关：只有菜品详情会填真值，列表接口留默认值（列表不展示这两个字段）
    want_count: int = 0
    is_wanted: bool = False


class DishTagOut(BaseModel):
    """标签清单项：前端据此渲染筛选 chips，count 用来把没菜的标签灰掉。"""

    name: str
    emoji: str
    group: str
    count: int = Field(default=0, description="挂了这个标签的在售菜品数")


class WantResult(BaseModel):
    wanted: bool = Field(description="操作后是否在清单里")
    want_count: int = Field(description="该菜品当前有多少人想吃")


class RandomDishOut(BaseModel):
    """「今天吃什么」的抽取结果。"""

    dish: DishOut
    pool_size: int = Field(description="本次抽取的候选池大小，1 表示没得换")
    source: Literal["top", "all", "wants"] = Field(
        description="候选池来源：top 高分池 / all 全部在售 / wants 我的想吃清单"
    )


class DishBrief(BaseModel):
    """嵌在帖子里的菜品信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    image_url: str | None = None
    avg_rating: float
    rating_count: int


class RatingOut(BaseModel):
    user_id: int
    nickname: str
    avatar_url: str | None = None
    score: int
    updated_at: datetime


# ---------------------------------------------------------------- 输入（管理端）


class CanteenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CanteenUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class MerchantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    canteen_id: int


class MerchantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    canteen_id: int | None = None


class DishCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    merchant_id: int
    image_url: str | None = Field(default=None, max_length=255)
    tags: list[str] = Field(default_factory=list, description="白名单见 /dishes/tags")

    @field_validator("tags")
    @classmethod
    def _check_tags(cls, value: list[str]) -> list[str]:
        # 抛 ValueError → 全局处理器转 400，不在 schema 里造 HTTP 异常
        return clean_tags(value)


class DishUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    merchant_id: int | None = None
    image_url: str | None = Field(default=None, max_length=255)
    # 不传 = 不动；传 [] = 清空。靠 model_fields_set 区分
    tags: list[str] | None = None

    @field_validator("tags")
    @classmethod
    def _check_tags(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else clean_tags(value)


class DishAvailabilityUpdate(BaseModel):
    is_available: bool


class UploadOut(BaseModel):
    url: str
    size: int
