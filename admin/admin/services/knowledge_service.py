"""知识维护服务：导入、知识单元 CRUD 与数据权限配置。"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from admin.core.deps import CurrentUser
from admin.core.exceptions import BadRequestError, NotFoundError
from admin.integrations import rag_client
from admin.models.knowledge import KnowledgeUnit
from admin.repositories import knowledge_repository
from admin.schemas.knowledge import (
    KnowledgeUnitDetail,
    KnowledgeUnitListResult,
    KnowledgeUnitOut,
    KnowledgeUnitUpdate,
    UnitPermissionItem,
)


def _gen_unit_code() -> str:
    return f"KU-{uuid.uuid4().hex}"


def _file_meta(filename: str, size: int) -> tuple[str, str]:
    """由文件名推导 (file_title 锚点, file_type)。

    RAG 侧 ``file_title`` 取文件 stem（去扩展名），故 ``source_file_name`` 以
    stem 存储以保持跨系统锚点一致。
    """
    path = Path(filename)
    stem = path.stem or filename
    ext = path.suffix.lstrip(".").lower() or "unknown"
    return stem, ext


async def import_knowledge(session: AsyncSession, current_user: CurrentUser, files: list[UploadFile]) -> list[str]:
    """转发文件到 RAG 导入，并按文件落 `knowledge_units` 元数据。"""
    if not files:
        raise BadRequestError("未选择要导入的文件")

    payloads: list[tuple[str, bytes, str]] = []
    metas: list[dict] = []
    for file in files:
        filename = file.filename or "unnamed"
        content = await file.read()
        content_type = file.content_type or "application/octet-stream"
        stem, ext = _file_meta(filename, len(content))
        payloads.append((filename, content, content_type))
        metas.append({"stem": stem, "ext": ext, "size": len(content)})

    task_ids = await rag_client.upload_files(payloads)

    for meta in metas:
        await _upsert_unit_on_import(session, current_user, meta)
    await session.commit()
    return task_ids


async def _upsert_unit_on_import(session: AsyncSession, current_user: CurrentUser, meta: dict) -> None:
    """导入锚点幂等：同名（stem）已存在则复用，否则新建草稿。"""
    stem = meta["stem"]
    unit = await knowledge_repository.get_by_source_file_name(session, stem)
    if unit is None:
        session.add(
            KnowledgeUnit(
                unit_code=_gen_unit_code(),
                title=stem,
                source_file_name=stem,
                file_type=meta["ext"],
                file_size=meta["size"],
                status="draft",
                creator_id=current_user.id,
            )
        )
    else:
        unit.file_type = meta["ext"]
        unit.file_size = meta["size"]
        unit.status = "draft"


async def get_import_task(task_id: str) -> dict:
    """转发 RAG 导入任务进度。"""
    return await rag_client.get_task_status(task_id)


async def list_units(
    session: AsyncSession,
    *,
    keyword: str | None = None,
    category: str | None = None,
    status: str | None = None,
    file_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> KnowledgeUnitListResult:
    rows, total = await knowledge_repository.list_units(
        session,
        keyword=keyword,
        category=category,
        status=status,
        file_type=file_type,
        page=page,
        page_size=page_size,
    )
    return KnowledgeUnitListResult(
        items=[KnowledgeUnitOut.model_validate(u) for u in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_unit_detail(session: AsyncSession, unit_id: int) -> KnowledgeUnitDetail:
    unit = await knowledge_repository.get_unit(session, unit_id)
    if unit is None:
        raise NotFoundError("知识单元不存在")
    perms = await knowledge_repository.list_unit_permissions(session, unit_id)
    detail = KnowledgeUnitDetail.model_validate(unit)
    detail.permissions = [UnitPermissionItem(target_type=p.target_type, target_id=p.target_id) for p in perms]
    return detail


async def update_unit(session: AsyncSession, unit_id: int, data: KnowledgeUnitUpdate) -> KnowledgeUnitOut:
    unit = await knowledge_repository.get_unit(session, unit_id)
    if unit is None:
        raise NotFoundError("知识单元不存在")

    if data.title is not None:
        unit.title = data.title
    if data.content is not None:
        unit.content = data.content
    if data.summary is not None:
        unit.summary = data.summary
    if data.category is not None:
        unit.category = data.category
    if data.status is not None:
        unit.status = data.status

    await session.commit()
    return KnowledgeUnitOut.model_validate(unit)


async def delete_units(session: AsyncSession, unit_ids: list[int]) -> None:
    """批量删除：先同步删 RAG 向量，再删知识单元行。"""
    units = await knowledge_repository.get_units_by_ids(session, unit_ids)
    if not units:
        raise NotFoundError("知识单元不存在")
    for unit in units:
        await rag_client.delete_chunks(unit.source_file_name)
    await knowledge_repository.delete_units(session, [u.id for u in units])
    await session.commit()


async def get_unit_permissions(session: AsyncSession, unit_id: int) -> list[UnitPermissionItem]:
    if await knowledge_repository.get_unit(session, unit_id) is None:
        raise NotFoundError("知识单元不存在")
    perms = await knowledge_repository.list_unit_permissions(session, unit_id)
    return [UnitPermissionItem(target_type=p.target_type, target_id=p.target_id) for p in perms]


async def set_unit_permissions(session: AsyncSession, unit_id: int, items: list[UnitPermissionItem]) -> None:
    if await knowledge_repository.get_unit(session, unit_id) is None:
        raise NotFoundError("知识单元不存在")
    normalized: list[tuple[str, int]] = []
    for item in items:
        target_id = 0 if item.target_type == "global" else item.target_id
        normalized.append((item.target_type, target_id))
    await knowledge_repository.replace_unit_permissions(session, unit_id, normalized)
    await session.commit()
