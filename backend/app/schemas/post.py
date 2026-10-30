"""帖子、评论、点赞相关的请求与响应模型。"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class PostCreate(BaseModel):
    dish_id: int
    # 评分必填：语义是"我现在对这道菜的看法"，重复发帖会覆盖
    score: int = Field(ge=1, le=5, description="1-5 星")
    content: str | None = Field(default=None, max_length=500)
    images: list[str] = Field(default_factory=list, max_length=4, description="先调上传接口拿到的 URL")

    @field_validator("content")
    @classmethod
    def _strip_content(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("images")
    @classmethod
    def _check_images(cls, value: list[str]) -> list[str]:
        for url in value:
            # 只接受站内静态路径或 http(s)，防止前端塞 javascript: 之类的串
            if not (url.startswith("/uploads/") or url.startswith(("http://", "https://"))):
                raise ValueError("图片地址必须以 /uploads/ 或 http(s):// 开头")
        return value


class AuthorBrief(BaseModel):
    id: int
    nickname: str
    avatar_url: str | None = None
    title_level: int
    title_name: str
    title_emoji: str


class DishInPost(BaseModel):
    id: int
    name: str
    image_url: str | None = None
    avg_rating: float
    rating_count: int
    is_available: bool = True


class MerchantInPost(BaseModel):
    id: int
    name: str
    canteen_name: str


class PostOut(BaseModel):
    id: int
    content: str | None = None
    images: list[str] = Field(default_factory=list)
    like_count: int
    comment_count: int
    created_at: datetime

    author: AuthorBrief
    dish: DishInPost
    merchant: MerchantInPost

    author_score: int | None = Field(
        default=None,
        description="作者对这道菜的当前评分。注意是'当前'而非'发帖当时'——评分可被后续发帖覆盖",
    )
    is_liked: bool = False


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)

    @field_validator("content")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("评论不能为空")
        return value


class CommentOut(BaseModel):
    id: int
    content: str
    created_at: datetime
    author: AuthorBrief


class LikeResult(BaseModel):
    liked: bool
    like_count: int
