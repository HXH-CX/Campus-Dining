"""管理后台概览的响应模型。

只读、不落库：所有数字都是查询时现算的，避免多一套需要维护的统计表。
"""

from pydantic import BaseModel, Field


class DayCount(BaseModel):
    date: str = Field(description="YYYY-MM-DD")
    count: int


class UntastedDish(BaseModel):
    """上架但还没人打过分的菜——最该被推一把的那批。"""

    id: int
    name: str
    merchant_name: str


class EmptyMerchant(BaseModel):
    """一个在售菜品都没有的商家：用户点进去会看到空列表。"""

    id: int
    name: str
    canteen_name: str


class AdminOverviewOut(BaseModel):
    # 总量
    users: int
    posts: int
    comments: int
    ratings: int
    dishes: int
    merchants: int
    canteens: int
    wants: int

    # 今日新增（按服务器本地时间的 0 点切）
    today_users: int
    today_posts: int
    today_comments: int

    # 近 7 天发帖趋势，含今天，没有数据的天补 0
    posts_by_day: list[DayCount] = Field(default_factory=list)

    # 运营提示
    untasted_total: int = 0
    untasted_dishes: list[UntastedDish] = Field(default_factory=list)
    empty_merchant_total: int = 0
    empty_merchants: list[EmptyMerchant] = Field(default_factory=list)
    unavailable_dishes: int = 0
