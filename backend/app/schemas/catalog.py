"""食堂 / 商家 / 菜品相关的请求与响应模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class RandomDishOut(BaseModel):
    """「今天吃什么」的抽取结果。"""

    dish: DishOut
    pool_size: int = Field(description="本次抽取的候选池大小，1 表示没得换")
    from_top: bool = Field(description="是否来自高分池（够分且够人评）")


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


class DishUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    merchant_id: int | None = None
    image_url: str | None = Field(default=None, max_length=255)


class DishAvailabilityUpdate(BaseModel):
    is_available: bool


class UploadOut(BaseModel):
    url: str
    size: int
