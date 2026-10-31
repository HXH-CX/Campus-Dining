"""帖子、评论、点赞相关的请求与响应模型。"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _strip_content(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _check_image_urls(value: list[str]) -> list[str]:
    for url in value:
        # 只接受站内静态路径或 http(s)，防止前端塞 javascript: 之类的串
        if not (url.startswith("/uploads/") or url.startswith(("http://", "https://"))):
            raise ValueError("图片地址必须以 /uploads/ 或 http(s):// 开头")
    return value


class PostCreate(BaseModel):
    dish_id: int
    # 评分必填：语义是"我现在对这道菜的看法"，重复发帖会覆盖
    score: int = Field(ge=1, le=5, description="1-5 星")
    content: str | None = Field(default=None, max_length=500)
    images: list[str] = Field(default_factory=list, max_length=4, description="先调上传接口拿到的 URL")

    @field_validator("content")
    @classmethod
    def _v_content(cls, value: str | None) -> str | None:
        return _strip_content(value)

    @field_validator("images")
    @classmethod
    def _v_images(cls, value: list[str]) -> list[str]:
        return _check_image_urls(value)


class PostUpdate(BaseModel):
    """编辑帖子。

    只允许改文案与配图：菜品和评分属于「我的看法」，改它的语义是重新表态，
    应该走发帖（覆盖评分）而不是编辑一条历史帖子。两个字段都可省略，
    传 null 的 content 表示清空文案。
    """

    content: str | None = Field(default=None, max_length=500)
    images: list[str] | None = Field(default=None, max_length=4)

    @field_validator("content")
    @classmethod
    def _v_content(cls, value: str | None) -> str | None:
        return _strip_content(value)

    @field_validator("images")
    @classmethod
    def _v_images(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _check_image_urls(value)


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
