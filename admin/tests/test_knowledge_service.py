"""knowledge_service 业务层单元测试。

重点覆盖：导入落库的幂等锚点、CRUD 语义、删除时同步清理 RAG 向量的调用次序、
数据权限全量覆盖时的 global 归一化，以及不存在资源的 NotFound 异常。
RAG 依赖通过 monkeypatch 打桩，不发起真实网络请求。
"""

from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.core.exceptions import BadRequestError, NotFoundError
from admin.integrations import rag_client
from admin.models.knowledge import KnowledgeUnit, UnitPermission
from admin.schemas.knowledge import KnowledgeUnitUpdate, UnitPermissionItem
from admin.services import knowledge_service


def _current_user(user_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(id=user_id)


async def test_import_knowledge_creates_units(session: AsyncSession, monkeypatch):
    monkeypatch.setattr(rag_client, "upload_files", AsyncMock(return_value=["t1", "t2"]))
    files = [
        UploadFile(file=io.BytesIO(b"hello world"), filename="guide.pdf"),
        UploadFile(file=io.BytesIO(b"abc"), filename="manual.md"),
    ]

    task_ids = await knowledge_service.import_knowledge(session, _current_user(), files)

    assert task_ids == ["t1", "t2"]
    units = (await session.execute(select(KnowledgeUnit))).scalars().all()
    by_name = {u.source_file_name: u for u in units}
    assert set(by_name) == {"guide", "manual"}
    assert by_name["guide"].file_type == "pdf"
    assert by_name["guide"].file_size == len(b"hello world")
    assert by_name["guide"].status == "draft"
    assert by_name["guide"].creator_id == 1


async def test_import_knowledge_idempotent_on_same_source(session: AsyncSession, monkeypatch):
    monkeypatch.setattr(rag_client, "upload_files", AsyncMock(return_value=["t1"]))
    content = b"same content"

    await knowledge_service.import_knowledge(
        session, _current_user(), [UploadFile(file=io.BytesIO(content), filename="guide.pdf")]
    )
    await knowledge_service.import_knowledge(
        session, _current_user(), [UploadFile(file=io.BytesIO(content), filename="guide.pdf")]
    )

    units = (await session.execute(select(KnowledgeUnit))).scalars().all()
    assert len(units) == 1


async def test_import_knowledge_rejects_empty(session: AsyncSession):
    with pytest.raises(BadRequestError):
        await knowledge_service.import_knowledge(session, _current_user(), [])


async def test_get_import_task_proxies_rag(monkeypatch):
    monkeypatch.setattr(rag_client, "get_task_status", AsyncMock(return_value={"status": "completed"}))
    result = await knowledge_service.get_import_task("task-1")
    assert result == {"status": "completed"}


async def test_list_units(session: AsyncSession, make_unit):
    session.add_all(
        [
            make_unit("KU-1", "alpha", "alpha", status="published"),
            make_unit("KU-2", "beta", "beta"),
        ]
    )
    await session.flush()

    result = await knowledge_service.list_units(session, page=1, page_size=20)
    assert result.total == 2
    assert result.page == 1
    assert result.page_size == 20
    assert len(result.items) == 2


async def test_get_unit_detail_with_permissions(session: AsyncSession, make_unit):
    unit = make_unit("KU-1", "alpha", "alpha")
    session.add(unit)
    await session.flush()
    session.add(UnitPermission(unit_id=unit.id, target_type="role", target_id=7))

    detail = await knowledge_service.get_unit_detail(session, unit.id)
    assert detail.id == unit.id
    assert detail.permissions == [UnitPermissionItem(target_type="role", target_id=7)]


async def test_get_unit_detail_not_found(session: AsyncSession):
    with pytest.raises(NotFoundError):
        await knowledge_service.get_unit_detail(session, 999)


async def test_update_unit_partial(session: AsyncSession, make_unit):
    unit = make_unit("KU-1", "alpha", "alpha", category="ops")
    session.add(unit)
    await session.flush()

    updated = await knowledge_service.update_unit(
        session, unit.id, KnowledgeUnitUpdate(title="new title", status="published")
    )
    assert updated.title == "new title"
    assert updated.status == "published"
    assert updated.category == "ops"  # 未提供字段保持不变


async def test_update_unit_not_found(session: AsyncSession):
    with pytest.raises(NotFoundError):
        await knowledge_service.update_unit(session, 999, KnowledgeUnitUpdate(title="x"))


async def test_delete_units_syncs_rag_vectors(session: AsyncSession, make_unit, monkeypatch):
    mock_delete = AsyncMock(return_value=5)
    monkeypatch.setattr(rag_client, "delete_chunks", mock_delete)
    units = [
        make_unit("KU-1", "alpha", "alpha"),
        make_unit("KU-2", "beta", "beta"),
    ]
    session.add_all(units)
    await session.flush()
    ids = [u.id for u in units]

    await knowledge_service.delete_units(session, ids)

    assert mock_delete.await_count == 2
    assert [call.args[0] for call in mock_delete.await_args_list] == ["alpha", "beta"]
    remaining = (await session.execute(select(KnowledgeUnit))).scalars().all()
    assert remaining == []


async def test_delete_units_not_found(session: AsyncSession):
    with pytest.raises(NotFoundError):
        await knowledge_service.delete_units(session, [999])


async def test_set_unit_permissions_normalizes_global(session: AsyncSession, make_unit):
    unit = make_unit("KU-1", "alpha", "alpha")
    session.add(unit)
    await session.flush()

    await knowledge_service.set_unit_permissions(
        session,
        unit.id,
        [
            UnitPermissionItem(target_type="global", target_id=5),
            UnitPermissionItem(target_type="user", target_id=3),
        ],
    )

    perms = (await session.execute(select(UnitPermission))).scalars().all()
    assert {(p.target_type, p.target_id) for p in perms} == {("global", 0), ("user", 3)}


async def test_get_unit_permissions(session: AsyncSession, make_unit):
    unit = make_unit("KU-1", "alpha", "alpha")
    session.add(unit)
    await session.flush()
    session.add(UnitPermission(unit_id=unit.id, target_type="department", target_id=2))
    await session.flush()

    items = await knowledge_service.get_unit_permissions(session, unit.id)
    assert items == [UnitPermissionItem(target_type="department", target_id=2)]
