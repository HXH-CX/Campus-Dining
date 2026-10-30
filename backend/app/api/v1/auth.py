from fastapi import APIRouter

from app.api.deps import DbSession
from app.core.response import ApiResponse, ok
from app.core.security import create_access_token
from app.schemas.auth import LoginIn, RegisterIn, TokenOut
from app.services import auth_service
from app.services.user_service import to_user_out

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=ApiResponse[TokenOut], summary="学生注册")
async def register(payload: RegisterIn, db: DbSession):
    user = await auth_service.register(db, payload)
    # 注册成功直接发 token，省一次登录往返
    token, expires_in = create_access_token(user.id)
    return ok(TokenOut(access_token=token, expires_in=expires_in, user=to_user_out(user)))


@router.post("/login", response_model=ApiResponse[TokenOut], summary="登录，返回 JWT")
async def login(payload: LoginIn, db: DbSession):
    user, token, expires_in = await auth_service.login(db, payload)
    return ok(TokenOut(access_token=token, expires_in=expires_in, user=to_user_out(user)))
