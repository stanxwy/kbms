"""认证鉴权路由。"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from admin.core.deps import CurrentUser, get_current_user
from admin.core.response import ok
from admin.database import get_db
from admin.schemas.auth import LoginRequest, RefreshRequest
from admin.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db)):
    data = await auth_service.login(session, payload.username, payload.password)
    return ok(data.model_dump())


@router.post("/refresh")
async def refresh(payload: RefreshRequest, session: AsyncSession = Depends(get_db)):
    data = await auth_service.refresh(session, payload.refresh_token)
    return ok(data.model_dump())


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(_: CurrentUser = Depends(get_current_user)) -> Response:
    """JWT 无状态，登出仅前/客户端丢弃令牌即可。"""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me")
async def me(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    data = await auth_service.get_me(session, current_user)
    return ok(data.model_dump())
