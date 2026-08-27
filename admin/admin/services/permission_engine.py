"""数据权限引擎：四维实体（global/department/role/user）OR 判定。

判定规则（与 SPEC §5.4 一致）：
  1. 用户停用 → 全部拒绝；
  2. 对每个知识单元，读取其 ``unit_permissions``，满足以下任一即放行：
     - 存在 ``target_type='global'``；
     - 存在 ``target_type='department'`` 且 ``target_id`` 属于用户部门（含祖先链）；
     - 存在 ``target_type='role'`` 且 ``target_id`` 属于用户角色；
     - 存在 ``target_type='user'`` 且 ``target_id`` 等于用户 id；
  3. 均不满足则拒绝。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.models.knowledge import UnitPermission
from admin.models.org import Department
from admin.models.user import User, UserRole
from admin.repositories import knowledge_repository

# 四种数据权限实体类型。
_TARGET_TYPE_GLOBAL = "global"
_TARGET_TYPE_DEPARTMENT = "department"
_TARGET_TYPE_ROLE = "role"
_TARGET_TYPE_USER = "user"


@dataclass
class PermissionCheckResult:
    """一次批量判定结果。"""

    authorized_unit_ids: list[int] = field(default_factory=list)
    unauthorized_unit_ids: list[int] = field(default_factory=list)


async def _department_ancestor_ids(session: AsyncSession, department_id: int | None) -> set[int]:
    """返回部门自身及其所有祖先部门 id 集合（含根）。"""
    if department_id is None:
        return set()
    departments = list((await session.execute(select(Department.id, Department.parent_id))).all())
    parent_by_id = {dept_id: parent_id for dept_id, parent_id in departments}

    ancestors: set[int] = set()
    current: int | None = department_id
    seen: set[int] = set()
    while current is not None and current not in seen:
        ancestors.add(current)
        seen.add(current)
        current = parent_by_id.get(current)
    return ancestors


async def check_permissions(
    session: AsyncSession,
    user_id: int,
    unit_ids: list[int],
) -> PermissionCheckResult:
    """判定用户对给定知识单元集合的可访问性。

    停用用户对所有单元一律拒绝；正常用户按四维实体 OR 判定。
    """
    result = PermissionCheckResult()
    if not unit_ids:
        return result

    user = await session.get(User, user_id)
    if user is None or user.status != 1:
        result.unauthorized_unit_ids = list(unit_ids)
        return result

    role_ids = list((await session.execute(select(UserRole.role_id).where(UserRole.user_id == user_id))).scalars())
    role_id_set = set(role_ids)
    ancestor_ids = await _department_ancestor_ids(session, user.department_id)

    permissions = await knowledge_repository.list_unit_permissions_by_unit_ids(session, unit_ids)
    perms_by_unit: dict[int, list[UnitPermission]] = {}
    for perm in permissions:
        perms_by_unit.setdefault(perm.unit_id, []).append(perm)

    for unit_id in unit_ids:
        if _is_authorized(perms_by_unit.get(unit_id, []), user_id, role_id_set, ancestor_ids):
            result.authorized_unit_ids.append(unit_id)
        else:
            result.unauthorized_unit_ids.append(unit_id)
    return result


def _is_authorized(
    permissions: list[UnitPermission],
    user_id: int,
    role_ids: set[int],
    ancestor_ids: set[int],
) -> bool:
    """对单个单元的权限实体做 OR 判定。"""
    for perm in permissions:
        if perm.target_type == _TARGET_TYPE_GLOBAL:
            return True
        if perm.target_type == _TARGET_TYPE_DEPARTMENT and perm.target_id in ancestor_ids:
            return True
        if perm.target_type == _TARGET_TYPE_ROLE and perm.target_id in role_ids:
            return True
        if perm.target_type == _TARGET_TYPE_USER and perm.target_id == user_id:
            return True
    return False
