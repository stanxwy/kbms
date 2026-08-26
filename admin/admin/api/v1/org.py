"""组织架构路由：部门 / 用户 / 角色与权限。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from admin.core.deps import CurrentUser, get_current_user, require_permissions
from admin.core.response import ok
from admin.database import get_db
from admin.schemas.org import (
    DepartmentCreate,
    DepartmentUpdate,
    ResetPasswordRequest,
    RoleCreate,
    RolePermissionsUpdate,
    RoleUpdate,
    UserCreate,
    UserStatusUpdate,
    UserUpdate,
)
from admin.services import org_service

router = APIRouter(prefix="/org", tags=["org"])


# ---- 部门 ----
@router.get("/departments")
async def list_departments(
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    tree = await org_service.list_department_tree(session)
    return ok([node.model_dump() for node in tree])


@router.post("/departments")
async def create_department(
    payload: DepartmentCreate,
    _: CurrentUser = Depends(require_permissions("menu:org:dept")),
    session: AsyncSession = Depends(get_db),
):
    dept = await org_service.create_department(session, payload)
    return ok(dept.model_dump())


@router.put("/departments/{dept_id}")
async def update_department(
    dept_id: int,
    payload: DepartmentUpdate,
    _: CurrentUser = Depends(require_permissions("menu:org:dept")),
    session: AsyncSession = Depends(get_db),
):
    dept = await org_service.update_department(session, dept_id, payload)
    return ok(dept.model_dump())


@router.delete("/departments/{dept_id}")
async def delete_department(
    dept_id: int,
    _: CurrentUser = Depends(require_permissions("menu:org:dept")),
    session: AsyncSession = Depends(get_db),
):
    await org_service.delete_department(session, dept_id)
    return ok(None)


# ---- 用户 ----
@router.get("/users")
async def list_users(
    keyword: str | None = Query(None),
    department_id: int | None = Query(None),
    status: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: CurrentUser = Depends(require_permissions("menu:org:user")),
    session: AsyncSession = Depends(get_db),
):
    data = await org_service.list_users(
        session,
        keyword=keyword,
        department_id=department_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return ok(data.model_dump())


@router.post("/users")
async def create_user(
    payload: UserCreate,
    _: CurrentUser = Depends(require_permissions("menu:org:user")),
    session: AsyncSession = Depends(get_db),
):
    data = await org_service.create_user(session, payload)
    return ok(data.model_dump())


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    _: CurrentUser = Depends(require_permissions("menu:org:user")),
    session: AsyncSession = Depends(get_db),
):
    data = await org_service.get_user_detail(session, user_id)
    return ok(data.model_dump())


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    _: CurrentUser = Depends(require_permissions("menu:org:user")),
    session: AsyncSession = Depends(get_db),
):
    data = await org_service.update_user(session, user_id, payload)
    return ok(data.model_dump())


@router.post("/users/{user_id}/password")
async def reset_password(
    user_id: int,
    payload: ResetPasswordRequest,
    _: CurrentUser = Depends(require_permissions("menu:org:user")),
    session: AsyncSession = Depends(get_db),
):
    await org_service.reset_password(session, user_id, payload.password)
    return ok(None)


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    _: CurrentUser = Depends(require_permissions("menu:org:user")),
    session: AsyncSession = Depends(get_db),
):
    await org_service.update_user_status(session, user_id, payload.status)
    return ok(None)


# ---- 角色 ----
@router.get("/roles")
async def list_roles(
    _: CurrentUser = Depends(require_permissions("menu:org:role")),
    session: AsyncSession = Depends(get_db),
):
    data = await org_service.list_roles(session)
    return ok([r.model_dump() for r in data])


@router.post("/roles")
async def create_role(
    payload: RoleCreate,
    _: CurrentUser = Depends(require_permissions("menu:org:role")),
    session: AsyncSession = Depends(get_db),
):
    data = await org_service.create_role(session, payload)
    return ok(data.model_dump())


@router.put("/roles/{role_id}")
async def update_role(
    role_id: int,
    payload: RoleUpdate,
    _: CurrentUser = Depends(require_permissions("menu:org:role")),
    session: AsyncSession = Depends(get_db),
):
    data = await org_service.update_role(session, role_id, payload)
    return ok(data.model_dump())


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    _: CurrentUser = Depends(require_permissions("menu:org:role")),
    session: AsyncSession = Depends(get_db),
):
    await org_service.delete_role(session, role_id)
    return ok(None)


@router.get("/roles/{role_id}/permissions")
async def get_role_permissions(
    role_id: int,
    _: CurrentUser = Depends(require_permissions("menu:org:role")),
    session: AsyncSession = Depends(get_db),
):
    data = await org_service.get_role_permissions(session, role_id)
    return ok([p.model_dump() for p in data])


@router.post("/roles/{role_id}/permissions")
async def set_role_permissions(
    role_id: int,
    payload: RolePermissionsUpdate,
    _: CurrentUser = Depends(require_permissions("menu:org:role")),
    session: AsyncSession = Depends(get_db),
):
    await org_service.set_role_permissions(session, role_id, payload.permissions)
    return ok(None)
