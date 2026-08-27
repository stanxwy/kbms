"""knowledge_repository 数据访问层单元测试。

覆盖：分页过滤查询、按 source_file_name 幂等查找、批量获取、数据权限全量覆盖、
批量删除的读写正确性与边界（空结果 / 空列表）。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from admin.models.knowledge import KnowledgeUnit
from admin.repositories import knowledge_repository


async def _seed(session: AsyncSession, make_unit) -> list[KnowledgeUnit]:
    units = [
        make_unit("KU-1", "alpha guide", "alpha", category="ops", status="published"),
        make_unit("KU-2", "beta doc", "beta", category="dev", status="draft", file_type="md"),
        make_unit("KU-3", "gamma", "gamma", category="ops", status="published"),
    ]
    session.add_all(units)
    await session.flush()
    return units


async def test_list_units_filters_and_total(session, make_unit):
    units = await _seed(session, make_unit)

    rows, total = await knowledge_repository.list_units(
        session, keyword=None, category=None, status=None, file_type=None, page=1, page_size=20
    )
    assert total == 3
    # 默认按 id 降序
    assert [u.id for u in rows] == [units[2].id, units[1].id, units[0].id]

    _, total = await knowledge_repository.list_units(
        session, keyword=None, category="ops", status=None, file_type=None, page=1, page_size=20
    )
    assert total == 2

    _, total = await knowledge_repository.list_units(
        session, keyword=None, category=None, status="published", file_type=None, page=1, page_size=20
    )
    assert total == 2

    _, total = await knowledge_repository.list_units(
        session, keyword=None, category=None, status=None, file_type="md", page=1, page_size=20
    )
    assert total == 1

    # keyword 同时匹配 title 与 source_file_name
    rows, total = await knowledge_repository.list_units(
        session, keyword="beta", category=None, status=None, file_type=None, page=1, page_size=20
    )
    assert total == 1
    assert rows[0].title == "beta doc"


async def test_list_units_pagination(session, make_unit):
    units = await _seed(session, make_unit)

    rows, total = await knowledge_repository.list_units(
        session, keyword=None, category=None, status=None, file_type=None, page=1, page_size=2
    )
    assert total == 3
    assert [u.id for u in rows] == [units[2].id, units[1].id]

    rows, total = await knowledge_repository.list_units(
        session, keyword=None, category=None, status=None, file_type=None, page=2, page_size=2
    )
    assert total == 3
    assert [u.id for u in rows] == [units[0].id]


async def test_list_units_empty(session):
    rows, total = await knowledge_repository.list_units(
        session, keyword=None, category=None, status=None, file_type=None, page=1, page_size=20
    )
    assert rows == []
    assert total == 0


async def test_get_by_source_file_name(session, make_unit):
    session.add(make_unit("KU-1", "alpha guide", "alpha"))
    await session.flush()

    found = await knowledge_repository.get_by_source_file_name(session, "alpha")
    assert found is not None
    assert found.unit_code == "KU-1"

    missing = await knowledge_repository.get_by_source_file_name(session, "nope")
    assert missing is None


async def test_get_units_by_ids(session, make_unit):
    units = await _seed(session, make_unit)
    ids = [units[0].id, units[2].id]

    found = await knowledge_repository.get_units_by_ids(session, ids)
    assert {u.id for u in found} == set(ids)

    empty = await knowledge_repository.get_units_by_ids(session, [])
    assert empty == []


async def test_replace_unit_permissions_overwrites(session, make_unit):
    unit = make_unit("KU-1", "alpha", "alpha")
    session.add(unit)
    await session.flush()

    await knowledge_repository.replace_unit_permissions(session, unit.id, [("global", 0), ("role", 7)])
    perms = await knowledge_repository.list_unit_permissions(session, unit.id)
    assert {(p.target_type, p.target_id) for p in perms} == {("global", 0), ("role", 7)}

    # 二次覆盖：旧权限清除，仅剩新实体
    await knowledge_repository.replace_unit_permissions(session, unit.id, [("user", 3)])
    perms = await knowledge_repository.list_unit_permissions(session, unit.id)
    assert [(p.target_type, p.target_id) for p in perms] == [("user", 3)]


async def test_delete_units(session, make_unit):
    units = await _seed(session, make_unit)
    ids = [u.id for u in units]

    await knowledge_repository.delete_units(session, [ids[0], ids[2]])
    remaining = await knowledge_repository.get_unit(session, ids[1])
    assert remaining is not None
    assert await knowledge_repository.get_unit(session, ids[0]) is None
    assert await knowledge_repository.get_unit(session, ids[2]) is None


async def test_delete_units_empty_is_noop(session):
    await knowledge_repository.delete_units(session, [])
