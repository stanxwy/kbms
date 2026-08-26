"""KBMS 幂等种子数据脚本。

预置内容（与 SPEC §10 / PRD §4 对齐）：
  - 示例部门树：总公司 -> 研发部 / 产品部 / 运营部
  - 内置角色：system_admin(系统管理员) / knowledge_admin(知识管理员) / user(普通用户)
  - 操作权限码全集（menu/button，与 SPEC §4 接口权限列一致）
  - 初始超管（admin）并绑定 system_admin 角色

重复执行安全：以唯一键（department.name / role.role_code /
user.username / role_permissions(role_id, permission_code) / user_roles(user_id, role_id)）
做「不存在才插入」的幂等处理。

用法（在 admin/ 目录下）：
    python scripts/init_seed.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# 确保 `import admin` 可解析（无论从 admin/ 目录还是仓库根启动）。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from admin.config import get_settings  # noqa: E402
from admin.core.security import hash_password  # noqa: E402
from admin.database import AsyncSessionLocal  # noqa: E402
from admin.models.org import Department, Role, RolePermission  # noqa: E402
from admin.models.user import User, UserRole  # noqa: E402

# ---- 权限码全集：[(permission_code, permission_type)] ----
ALL_PERMISSIONS: list[tuple[str, str]] = [
    # 菜单（menu）
    ("menu:org:user", "menu"),
    ("menu:org:dept", "menu"),
    ("menu:org:role", "menu"),
    ("menu:dashboard", "menu"),
    ("menu:settlement:faq", "menu"),
    ("menu:settlement:gap", "menu"),
    # 按钮/接口操作（button）
    ("op:knowledge:import", "button"),
    ("op:knowledge:unit:read", "button"),
    ("op:knowledge:unit:update", "button"),
    ("op:knowledge:unit:delete", "button"),
    ("op:ai:chat", "button"),
    ("op:settlement:faq:review", "button"),
]

# ---- 角色 -> 授权权限码集合 ----
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "system_admin": {code for code, _ in ALL_PERMISSIONS},
    "knowledge_admin": {
        "op:knowledge:import",
        "op:knowledge:unit:read",
        "op:knowledge:unit:update",
        "op:knowledge:unit:delete",
        "op:settlement:faq:review",
        "menu:settlement:faq",
        "menu:settlement:gap",
    },
    "user": {"op:ai:chat"},
}

# ---- 内置角色：[(role_code, role_name, description)] ----
ROLES: list[tuple[str, str, str]] = [
    ("system_admin", "系统管理员", "用户/角色/部门维护、菜单与操作权限配置、监控看板"),
    ("knowledge_admin", "知识管理员", "知识单元导入/编辑/删除、配置数据权限、审核 FAQ、维护知识缺口"),
    ("user", "普通用户", "登录后进行 AI 智能问答"),
]

# ---- 示例部门树：[(name, parent_name | None)] ----
DEPARTMENTS: list[tuple[str, str | None]] = [
    ("总公司", None),
    ("研发部", "总公司"),
    ("产品部", "总公司"),
    ("运营部", "总公司"),
]


async def _seed_departments(session: AsyncSession) -> None:
    """按名称幂等创建部门树，返回 name -> Department 映射。"""
    created: dict[str, Department] = {}
    for name, parent_name in DEPARTMENTS:
        existing = (
            await session.execute(select(Department).where(Department.name == name))
        ).scalar_one_or_none()
        if existing is not None:
            created[name] = existing
            continue
        parent = created.get(parent_name) if parent_name else None
        dept = Department(name=name, parent_id=parent.id if parent else None)
        session.add(dept)
        # 立即 flush 使 dept.id 生成，供后续子部门引用 parent_id。
        await session.flush()
        created[name] = dept


async def _seed_roles_and_permissions(session: AsyncSession) -> dict[str, Role]:
    """幂等创建角色并补齐 role_permissions，返回 role_code -> Role 映射。"""
    roles: dict[str, Role] = {}
    for role_code, role_name, description in ROLES:
        role = (
            await session.execute(select(Role).where(Role.role_code == role_code))
        ).scalar_one_or_none()
        if role is None:
            role = Role(role_code=role_code, role_name=role_name, description=description)
            session.add(role)
            await session.flush()
        roles[role_code] = role

        # 补齐缺失的权限码（幂等：UNIQUE(role_id, permission_code)）。
        existing_codes = set(
            (
                await session.execute(
                    select(RolePermission.permission_code).where(
                        RolePermission.role_id == role.id
                    )
                )
            ).scalars()
        )
        for code in sorted(ROLE_PERMISSIONS[role_code] - existing_codes):
            permission_type = next(t for c, t in ALL_PERMISSIONS if c == code)
            session.add(
                RolePermission(
                    role_id=role.id,
                    permission_code=code,
                    permission_type=permission_type,
                )
            )
    await session.flush()
    return roles


async def _seed_superuser(session: AsyncSession, roles: dict[str, Role]) -> None:
    """幂等创建初始超管并绑定 system_admin 角色。"""
    settings = get_settings()
    username = settings.INITIAL_SUPERUSER_USERNAME

    user = (
        await session.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if user is None:
        user = User(
            username=username,
            password_hash=hash_password(settings.INITIAL_SUPERUSER_PASSWORD),
            display_name="系统管理员",
            status=1,
        )
        session.add(user)
        await session.flush()

    role = roles["system_admin"]
    already_linked = (
        await session.execute(
            select(UserRole).where(
                UserRole.user_id == user.id, UserRole.role_id == role.id
            )
        )
    ).scalar_one_or_none()
    if already_linked is None:
        session.add(UserRole(user_id=user.id, role_id=role.id))
    await session.flush()


async def main() -> None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await _seed_departments(session)
            roles = await _seed_roles_and_permissions(session)
            await _seed_superuser(session, roles)
    print("seed completed (idempotent)")


if __name__ == "__main__":
    asyncio.run(main())