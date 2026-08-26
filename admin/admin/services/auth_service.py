"""认证服务：登录、刷新、当前用户。"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from admin.core.deps import CurrentUser, load_user_identity
from admin.core.exceptions import UnauthorizedError
from admin.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from admin.repositories import org_repository, user_repository
from admin.schemas.auth import LoginResponse, MeResponse, RefreshResponse, UserInfo
from admin.schemas.org import RoleBrief


async def login(session: AsyncSession, username: str, password: str) -> LoginResponse:
    """校验凭证、签发令牌，返回 token + 用户信息 + 权限集。"""
    user = await user_repository.get_by_username(session, username)
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("用户名或密码错误")
    if user.status != 1:
        raise UnauthorizedError("用户已停用")

    identity = await load_user_identity(session, user.id)
    return LoginResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        token_type="Bearer",
        user_info=UserInfo(
            id=identity.id,
            username=identity.username,
            display_name=identity.display_name,
            department_id=identity.department_id,
        ),
        permissions=sorted(identity.permissions),
    )


async def refresh(session: AsyncSession, refresh_token: str) -> RefreshResponse:
    """校验 refresh token 并换发新的 access token。"""
    payload = decode_token(refresh_token, "refresh")
    user = await user_repository.get_by_id(session, int(payload["sub"]))
    if user is None or user.status != 1:
        raise UnauthorizedError("token 无效或用户已停用")
    return RefreshResponse(access_token=create_access_token(user.id))


async def get_me(session: AsyncSession, current_user: CurrentUser) -> MeResponse:
    """返回当前用户及角色、权限、部门信息。"""
    roles = await org_repository.list_roles_by_ids(session, current_user.role_ids)
    department_name = None
    if current_user.department_id is not None:
        dept = await org_repository.get_department(session, current_user.department_id)
        if dept is not None:
            department_name = dept.name

    return MeResponse(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        department_id=current_user.department_id,
        department_name=department_name,
        roles=[RoleBrief.model_validate(r) for r in roles],
        permissions=sorted(current_user.permissions),
    )
