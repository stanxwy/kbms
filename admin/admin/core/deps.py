"""依赖注入装配：当前用户、RBAC 鉴权、操作权限拦截。

P1 实现：从 `Authorization: Bearer <access_token>` 解出用户，加载其角色与操作权限，
供路由作为 FastAPI 依赖使用（登录态 / 菜单与按钮级权限拦截）。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.core.exceptions import ForbiddenError, UnauthorizedError
from admin.core.security import decode_token
from admin.database import get_db
from admin.models.org import Role, RolePermission
from admin.models.user import User, UserRole

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    """当前登录用户上下文（含角色集合与操作权限集合）。"""

    id: int
    username: str
    display_name: str | None
    department_id: int | None
    status: int
    role_ids: list[int] = field(default_factory=list)
    role_codes: list[str] = field(default_factory=list)
    permissions: set[str] = field(default_factory=set)


async def load_user_identity(session: AsyncSession, user_id: int) -> CurrentUser:
    """按用户 id 装配身份（用户 + 角色 + 权限），供登录态依赖与登录服务共用。"""
    user = await session.get(User, user_id)
    if user is None or user.status != 1:
        raise UnauthorizedError("用户不存在或已停用")

    role_ids = list((await session.execute(select(UserRole.role_id).where(UserRole.user_id == user_id))).scalars())
    role_codes: list[str] = []
    permissions: set[str] = set()
    if role_ids:
        role_codes = list((await session.execute(select(Role.role_code).where(Role.id.in_(role_ids)))).scalars())
        permissions = set(
            (
                await session.execute(
                    select(RolePermission.permission_code).where(RolePermission.role_id.in_(role_ids))
                )
            ).scalars()
        )

    return CurrentUser(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        department_id=user.department_id,
        status=user.status,
        role_ids=role_ids,
        role_codes=role_codes,
        permissions=permissions,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """解析并校验 access token，返回当前用户身份（未登录/过期/停用则 401）。"""
    if credentials is None:
        raise UnauthorizedError("未提供认证令牌")
    payload = decode_token(credentials.credentials, "access")
    return await load_user_identity(session, int(payload["sub"]))


def require_permissions(*codes: str) -> Callable[..., CurrentUser]:
    """操作权限拦截依赖工厂：用户具备任一指定权限码即放行，否则 403。"""

    async def checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not any(code in current_user.permissions for code in codes):
            raise ForbiddenError("无操作权限")
        return current_user

    return checker


__all__ = ["CurrentUser", "get_current_user", "require_permissions", "load_user_identity"]
