from pydantic import BaseModel, Field

from app.schemas.user import UserOut

USERNAME_PATTERN = r"^[a-zA-Z0-9_]{3,50}$"


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=USERNAME_PATTERN, description="字母/数字/下划线")
    nickname: str = Field(min_length=1, max_length=50)
    # 上限 32 字符：bcrypt 只吃前 72 字节，中文密码容易超，这里从源头卡住
    password: str = Field(min_length=6, max_length=32)


class LoginIn(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=1, max_length=32)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="有效期秒数")
    user: UserOut
