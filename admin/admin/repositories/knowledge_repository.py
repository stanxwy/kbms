"""知识单元与数据权限的数据访问层。"""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.models.knowledge import KnowledgeUnit, UnitPermission


async def get_unit(session: AsyncSession, unit_id: int) -> KnowledgeUnit | None:
    return await session.get(KnowledgeUnit, unit_id)


async def get_units_by_ids(session: AsyncSession, unit_ids: list[int]) -> list[KnowledgeUnit]:
    if not unit_ids:
        return []
    return list((await session.execute(select(KnowledgeUnit).where(KnowledgeUnit.id.in_(unit_ids)))).scalars())


async def get_by_source_file_name(session: AsyncSession, source_file_name: str) -> KnowledgeUnit | None:
    return (
        await session.execute(select(KnowledgeUnit).where(KnowledgeUnit.source_file_name == source_file_name))
    ).scalar_one_or_none()


async def list_units(
    session: AsyncSession,
    *,
    keyword: str | None,
    category: str | None,
    status: str | None,
    file_type: str | None,
    page: int,
    page_size: int,
) -> tuple[list[KnowledgeUnit], int]:
    """按过滤条件分页知识单元，返回 (rows, total)。"""
    conditions = []
    if keyword:
        like = f"%{keyword}%"
        conditions.append(KnowledgeUnit.title.ilike(like) | KnowledgeUnit.source_file_name.ilike(like))
    if category:
        conditions.append(KnowledgeUnit.category == category)
    if status:
        conditions.append(KnowledgeUnit.status == status)
    if file_type:
        conditions.append(KnowledgeUnit.file_type == file_type)

    count_stmt = select(func.count()).select_from(KnowledgeUnit)
    stmt = select(KnowledgeUnit)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
        stmt = stmt.where(*conditions)

    total = (await session.execute(count_stmt)).scalar_one()
    rows = (
        (await session.execute(stmt.order_by(KnowledgeUnit.id.desc()).offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )
    return list(rows), total


async def delete_units(session: AsyncSession, unit_ids: list[int]) -> None:
    if unit_ids:
        await session.execute(delete(KnowledgeUnit).where(KnowledgeUnit.id.in_(unit_ids)))


async def list_unit_permissions(session: AsyncSession, unit_id: int) -> list[UnitPermission]:
    return list((await session.execute(select(UnitPermission).where(UnitPermission.unit_id == unit_id))).scalars())


async def replace_unit_permissions(session: AsyncSession, unit_id: int, items: list[tuple[str, int]]) -> None:
    """全量覆盖知识单元数据权限（items 为 (target_type, target_id)）。"""
    await session.execute(delete(UnitPermission).where(UnitPermission.unit_id == unit_id))
    for target_type, target_id in items:
        session.add(UnitPermission(unit_id=unit_id, target_type=target_type, target_id=target_id))
