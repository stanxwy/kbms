"""部门、角色、角色-权限的数据访问层。"""
from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.models.org import Department, Role, RolePermission
from admin.models.user import User, UserRole


# ---- 部门 ----
async def list_all_departments(session: AsyncSession) -> list[Department]:
    return list(
        (
            await session.execute(
                select(Department).order_by(Department.sort_order, Department.id)
            )
        ).scalars()
    )


async def get_department(session: AsyncSession, dept_id: int) -> Department | None:
    return await session.get(Department, dept_id)


async def exists_department_name(
    session: AsyncSession, name: str, exclude_id: int | None = None
) -> bool:
    stmt = select(Department.id).where(Department.name == name)
    if exclude_id is not None:
        stmt = stmt.where(Department.id != exclude_id)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def count_children(session: AsyncSession, dept_id: int) -> int:
    return (
        await session.execute(
            select(func.count()).select_from(Department).where(Department.parent_id == dept_id)
        )
    ).scalar_one()


async def count_members(session: AsyncSession, dept_id: int) -> int:
    return (
        await session.execute(
            select(func.count()).select_from(User).where(User.department_id == dept_id)
        )
    ).scalar_one()


# ---- 角色 ----
async def list_all_roles(session: AsyncSession) -> list[Role]:
    return list((await session.execute(select(Role).order_by(Role.id))).scalars())


async def list_roles_by_ids(session: AsyncSession, role_ids: list[int]) -> list[Role]:
    if not role_ids:
        return []
    return list(
        (await session.execute(select(Role).where(Role.id.in_(role_ids)))).scalars()
    )


async def get_role(session: AsyncSession, role_id: int) -> Role | None:
    return await session.get(Role, role_id)


async def exists_role_code(
    session: AsyncSession, role_code: str, exclude_id: int | None = None
) -> bool:
    stmt = select(Role.id).where(Role.role_code == role_code)
    if exclude_id is not None:
        stmt = stmt.where(Role.id != exclude_id)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def count_role_users(session: AsyncSession, role_id: int) -> int:
    return (
        await session.execute(
            select(func.count()).select_from(UserRole).where(UserRole.role_id == role_id)
        )
    ).scalar_one()


# ---- 角色-操作权限 ----
async def list_role_permissions(session: AsyncSession, role_id: int) -> list[RolePermission]:
    return list(
        (
            await session.execute(
                select(RolePermission).where(RolePermission.role_id == role_id)
            )
        ).scalars()
    )


async def replace_role_permissions(
    session: AsyncSession, role_id: int, items: list[tuple[str, str]]
) -> None:
    """全量覆盖角色权限（items 为 (permission_code, permission_type)）。"""
    await session.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    for code, ptype in items:
        session.add(RolePermission(role_id=role_id, permission_code=code, permission_type=ptype))
