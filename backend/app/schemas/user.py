from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.catalog import DishBrief


class AchievementOut(BaseModel):
    code: str
    name: str
    emoji: str
    description: str
    unlocked_at: datetime


class UserBrief(BaseModel):
    """列表/帖子作者等只需要基础信息的场景。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nickname: str
    avatar_url: str | None = None


class UserOut(BaseModel):
    """完整用户信息。称号名称由后端按 title_level 映射后一起返回。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nickname: str
    avatar_url: str | None = None
    is_admin: bool = False
    title_level: int
    title_name: str
    title_emoji: str
    follower_count: int
    following_count: int
    achievements: list[AchievementOut] = Field(default_factory=list)
    created_at: datetime


class UserCard(BaseModel):
    """关注/粉丝列表里的用户卡片。is_mutual 由查询两侧关系推导，不落库。"""

    id: int
    nickname: str
    avatar_url: str | None = None
    title_level: int
    title_name: str
    title_emoji: str
    is_mutual: bool = False
    followed_by_me: bool = False


class UserRatingOut(BaseModel):
    """"我的评价"列表项。"""

    dish: DishBrief
    score: int
    updated_at: datetime


class CommentedPost(BaseModel):
    """评论挂在哪个帖子上——前端据此渲染"来自某某的食评"并可点击跳转。"""

    id: int
    dish_name: str
    excerpt: str | None = Field(default=None, description="帖子文案前 40 字")
    image_url: str | None = Field(default=None, description="帖子首图，没有则回落菜品图")


class UserCommentOut(BaseModel):
    """"我的评论"列表项。"""

    id: int
    content: str
    created_at: datetime
    post: CommentedPost


class UserUpdate(BaseModel):
    """本人可改的资料。用户名不可改（登录凭据），称号由系统计算。"""

    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    avatar_url: str | None = Field(default=None, max_length=255)

    @field_validator("nickname")
    @classmethod
    def _nickname_strip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("昵称不能为空")
        return value

    @field_validator("avatar_url")
    @classmethod
    def _avatar_check(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if value and not (value.startswith("/uploads/") or value.startswith(("http://", "https://"))):
            raise ValueError("头像地址必须以 /uploads/ 或 http(s):// 开头")
        return value or None
