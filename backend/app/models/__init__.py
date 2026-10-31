"""所有 ORM 模型集中导出。

Alembic 的 env.py 只 import 本模块，即可保证 Base.metadata 里注册了全部表。
"""

from app.models.catalog import Canteen, Dish, Merchant
from app.models.post import Comment, Like, Post
from app.models.rating import Rating
from app.models.social import Follow, UserAchievement, Want
from app.models.user import User

__all__ = [
    "Canteen",
    "Comment",
    "Dish",
    "Follow",
    "Like",
    "Merchant",
    "Post",
    "Rating",
    "User",
    "UserAchievement",
    "Want",
]
