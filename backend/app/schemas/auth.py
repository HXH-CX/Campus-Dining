from pydantic import BaseModel, Field, field_validator

from app.schemas.user import UserOut

USERNAME_PATTERN = r"^[a-zA-Z0-9_]{3,50}$"


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=USERNAME_PATTERN, description="字母/数字/下划线")
    nickname: str = Field(min_length=1, max_length=50)
    # 上限 32 字符：bcrypt 只吃前 72 字节，中文密码容易超，这里从源头卡住
    password: str = Field(min_length=8, max_length=32, description="8-32 位，需含字母和数字")

    @field_validator("password")
    @classmethod
    def _needs_letter_and_digit(cls, value: str) -> str:
        # 不强制大小写和符号：学生群体的实际体验是"规则越复杂，越多人写成 123456a"
        # 有字母有数字已经能挡住绝大多数撞库字典，再严就得配找回密码流程了
        if not any(ch.isalpha() for ch in value):
            raise ValueError("密码需要包含字母")
        if not any(ch.isdigit() for ch in value):
            raise ValueError("密码需要包含数字")
        return value


class LoginIn(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=1, max_length=32)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="有效期秒数")
    user: UserOut
