"""组织架构服务：部门树 / 用户 / 角色与权限分配。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.core.exceptions import BadRequestError, ConflictError, NotFoundError
from admin.core.security import hash_password
from admin.models.org import Department, Role
from admin.models.user import User, UserRole
from admin.repositories import org_repository, user_repository
from admin.schemas.org import (
    DepartmentCreate,
    DepartmentOut,
    DepartmentTreeNode,
    DepartmentUpdate,
    PermissionItem,
    RoleBrief,
    RoleCreate,
    RoleOut,
    RoleUpdate,
    UserCreate,
    UserListResult,
    UserOut,
    UserUpdate,
)


# ---- 部门 ----
async def list_department_tree(session: AsyncSession) -> list[DepartmentTreeNode]:
    """加载全部部门并组装为树形结构（按 sort_order 排序）。"""
    depts = await org_repository.list_all_departments(session)
    nodes: dict[int, DepartmentTreeNode] = {}
    for d in depts:
        nodes[d.id] = DepartmentTreeNode(
            id=d.id, parent_id=d.parent_id, name=d.name, leader_id=d.leader_id, sort_order=d.sort_order
        )
    roots: list[DepartmentTreeNode] = []
    for node in nodes.values():
        if node.parent_id is not None and node.parent_id in nodes:
            nodes[node.parent_id].children.append(node)
        else:
            roots.append(node)
    return roots


async def create_department(session: AsyncSession, data: DepartmentCreate) -> DepartmentOut:
    if data.parent_id is not None and await org_repository.get_department(session, data.parent_id) is None:
        raise NotFoundError("父部门不存在")
    if await org_repository.exists_department_name(session, data.name):
        raise ConflictError("部门名称已存在")

    dept = Department(
        parent_id=data.parent_id,
        name=data.name,
        leader_id=data.leader_id,
        sort_order=data.sort_order,
    )
    session.add(dept)
    await session.flush()
    await session.commit()
    return DepartmentOut.model_validate(dept)


async def update_department(session: AsyncSession, dept_id: int, data: DepartmentUpdate) -> DepartmentOut:
    dept = await org_repository.get_department(session, dept_id)
    if dept is None:
        raise NotFoundError("部门不存在")

    if data.parent_id is not None:
        if data.parent_id == dept_id:
            raise BadRequestError("部门不能作为自己的父部门")
        if await org_repository.get_department(session, data.parent_id) is None:
            raise NotFoundError("父部门不存在")
        dept.parent_id = data.parent_id
    if data.name is not None and data.name != dept.name:
        if await org_repository.exists_department_name(session, data.name, exclude_id=dept_id):
            raise ConflictError("部门名称已存在")
        dept.name = data.name
    if data.leader_id is not None:
        dept.leader_id = data.leader_id
    if data.sort_order is not None:
        dept.sort_order = data.sort_order

    await session.flush()
    await session.commit()
    return DepartmentOut.model_validate(dept)


async def delete_department(session: AsyncSession, dept_id: int) -> None:
    dept = await org_repository.get_department(session, dept_id)
    if dept is None:
        raise NotFoundError("部门不存在")
    if await org_repository.count_children(session, dept_id) > 0:
        raise ConflictError("存在子部门，无法删除")
    if await org_repository.count_members(session, dept_id) > 0:
        raise ConflictError("部门下存在用户，无法删除")

    await session.delete(dept)
    await session.commit()


# ---- 用户 ----
async def list_users(
    session: AsyncSession,
    *,
    keyword: str | None = None,
    department_id: int | None = None,
    status: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> UserListResult:
    users, total = await user_repository.list_users(
        session,
        keyword=keyword,
        department_id=department_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return UserListResult(
        items=await _to_user_out_list(session, users),
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_user_detail(session: AsyncSession, user_id: int) -> UserOut:
    user = await user_repository.get_by_id(session, user_id)
    if user is None:
        raise NotFoundError("用户不存在")
    return (await _to_user_out_list(session, [user]))[0]


async def create_user(session: AsyncSession, data: UserCreate) -> UserOut:
    if await user_repository.exists_username(session, data.username):
        raise ConflictError("用户名已存在")
    if data.department_id is not None and await org_repository.get_department(session, data.department_id) is None:
        raise NotFoundError("部门不存在")
    if data.role_ids and not await _roles_exist(session, data.role_ids):
        raise NotFoundError("角色不存在")

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        display_name=data.display_name,
        department_id=data.department_id,
        status=data.status,
    )
    session.add(user)
    await session.flush()
    if data.role_ids:
        await user_repository.replace_roles(session, user.id, data.role_ids)
    await session.flush()

    result = await get_user_detail(session, user.id)
    await session.commit()
    return result


async def update_user(session: AsyncSession, user_id: int, data: UserUpdate) -> UserOut:
    user = await user_repository.get_by_id(session, user_id)
    if user is None:
        raise NotFoundError("用户不存在")
    if data.department_id is not None and await org_repository.get_department(session, data.department_id) is None:
        raise NotFoundError("部门不存在")
    if data.role_ids is not None and data.role_ids and not await _roles_exist(session, data.role_ids):
        raise NotFoundError("角色不存在")

    if data.display_name is not None:
        user.display_name = data.display_name
    if data.department_id is not None:
        user.department_id = data.department_id
    if data.role_ids is not None:
        await user_repository.replace_roles(session, user_id, data.role_ids)
    await session.flush()

    result = await get_user_detail(session, user_id)
    await session.commit()
    return result


async def reset_password(session: AsyncSession, user_id: int, password: str) -> None:
    user = await user_repository.get_by_id(session, user_id)
    if user is None:
        raise NotFoundError("用户不存在")
    user.password_hash = hash_password(password)
    await session.commit()


async def update_user_status(session: AsyncSession, user_id: int, status: int) -> None:
    user = await user_repository.get_by_id(session, user_id)
    if user is None:
        raise NotFoundError("用户不存在")
    user.status = status
    await session.commit()


# ---- 角色 ----
async def list_roles(session: AsyncSession) -> list[RoleOut]:
    return [RoleOut.model_validate(r) for r in await org_repository.list_all_roles(session)]


async def create_role(session: AsyncSession, data: RoleCreate) -> RoleOut:
    if await org_repository.exists_role_code(session, data.role_code):
        raise ConflictError("角色编码已存在")
    role = Role(role_name=data.role_name, role_code=data.role_code, description=data.description)
    session.add(role)
    await session.flush()
    await session.commit()
    return RoleOut.model_validate(role)


async def update_role(session: AsyncSession, role_id: int, data: RoleUpdate) -> RoleOut:
    role = await org_repository.get_role(session, role_id)
    if role is None:
        raise NotFoundError("角色不存在")
    if data.role_name is not None:
        role.role_name = data.role_name
    if data.description is not None:
        role.description = data.description
    await session.commit()
    return RoleOut.model_validate(role)


async def delete_role(session: AsyncSession, role_id: int) -> None:
    role = await org_repository.get_role(session, role_id)
    if role is None:
        raise NotFoundError("角色不存在")
    if await org_repository.count_role_users(session, role_id) > 0:
        raise ConflictError("角色已分配给用户，无法删除")
    await session.delete(role)
    await session.commit()


async def get_role_permissions(session: AsyncSession, role_id: int) -> list[PermissionItem]:
    if await org_repository.get_role(session, role_id) is None:
        raise NotFoundError("角色不存在")
    perms = await org_repository.list_role_permissions(session, role_id)
    return [PermissionItem(permission_code=p.permission_code, permission_type=p.permission_type) for p in perms]


async def set_role_permissions(session: AsyncSession, role_id: int, items: list[PermissionItem]) -> None:
    if await org_repository.get_role(session, role_id) is None:
        raise NotFoundError("角色不存在")
    for item in items:
        if item.permission_type not in ("menu", "button"):
            raise BadRequestError(f"非法权限类型: {item.permission_type}")
    await org_repository.replace_role_permissions(
        session, role_id, [(i.permission_code, i.permission_type) for i in items]
    )
    await session.commit()


# ---- 内部辅助 ----
async def _roles_exist(session: AsyncSession, role_ids: list[int]) -> bool:
    roles = await org_repository.list_roles_by_ids(session, role_ids)
    return len(roles) == len(set(role_ids))


async def _to_user_out_list(session: AsyncSession, users: list[User]) -> list[UserOut]:
    """批量组装用户输出（补部门名与角色）。"""
    if not users:
        return []

    dept_ids = {u.department_id for u in users if u.department_id is not None}
    dept_map: dict[int, str] = {}
    if dept_ids:
        for dept in (await session.execute(select(Department).where(Department.id.in_(dept_ids)))).scalars():
            dept_map[dept.id] = dept.name

    user_ids = [u.id for u in users]
    user_role_map: dict[int, list[int]] = {}
    role_ids: set[int] = set()
    for ur in (await session.execute(select(UserRole).where(UserRole.user_id.in_(user_ids)))).scalars():
        user_role_map.setdefault(ur.user_id, []).append(ur.role_id)
        role_ids.add(ur.role_id)
    role_map = {r.id: r for r in await org_repository.list_roles_by_ids(session, list(role_ids))}

    result: list[UserOut] = []
    for u in users:
        roles = [RoleBrief.model_validate(role_map[rid]) for rid in user_role_map.get(u.id, []) if rid in role_map]
        result.append(
            UserOut(
                id=u.id,
                username=u.username,
                display_name=u.display_name,
                department_id=u.department_id,
                department_name=dept_map.get(u.department_id),
                status=u.status,
                roles=roles,
            )
        )
    return result
