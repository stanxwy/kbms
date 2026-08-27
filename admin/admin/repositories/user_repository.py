"""用户与用户-角色的数据访问层。"""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.models.user import User, UserRole


async def get_by_username(session: AsyncSession, username: str) -> User | None:
    return (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def exists_username(session: AsyncSession, username: str, exclude_id: int | None = None) -> bool:
    stmt = select(User.id).where(User.username == username)
    if exclude_id is not None:
        stmt = stmt.where(User.id != exclude_id)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def list_users(
    session: AsyncSession,
    *,
    keyword: str | None,
    department_id: int | None,
    status: int | None,
    page: int,
    page_size: int,
) -> tuple[list[User], int]:
    """按过滤条件分页用户，返回 (rows, total)。"""
    conditions = []
    if keyword:
        like = f"%{keyword}%"
        conditions.append(User.username.ilike(like) | User.display_name.ilike(like))
    if department_id is not None:
        conditions.append(User.department_id == department_id)
    if status is not None:
        conditions.append(User.status == status)

    count_stmt = select(func.count()).select_from(User)
    stmt = select(User)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
        stmt = stmt.where(*conditions)

    total = (await session.execute(count_stmt)).scalar_one()
    rows = (
        (await session.execute(stmt.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )
    return list(rows), total


async def replace_roles(session: AsyncSession, user_id: int, role_ids: list[int]) -> None:
    """全量覆盖用户角色关联。"""
    await session.execute(delete(UserRole).where(UserRole.user_id == user_id))
    for role_id in role_ids:
        session.add(UserRole(user_id=user_id, role_id=role_id))
