from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, DbSession
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
    token, expires_in = create_access_token(user.id, user.token_version)
    return ok(TokenOut(access_token=token, expires_in=expires_in, user=to_user_out(user)))


@router.post("/login", response_model=ApiResponse[TokenOut], summary="登录，返回 JWT")
async def login(payload: LoginIn, db: DbSession, request: Request):
    # 限流按「用户名 + 来源 IP」两个维度计，IP 取自直连地址（本项目不走反代）
    client_ip = request.client.host if request.client else None
    user, token, expires_in = await auth_service.login(db, payload, client_ip)
    return ok(TokenOut(access_token=token, expires_in=expires_in, user=to_user_out(user)))


@router.post("/logout", summary="退出登录（当前及此前签发的 token 一并失效）")
async def logout(db: DbSession, current: CurrentUser):
    await auth_service.logout(db, current)
    return ok(None, "已退出登录")
