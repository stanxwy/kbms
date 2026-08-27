"""知识维护路由：导入、知识单元 CRUD 与数据权限配置。"""
from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from admin.core.deps import CurrentUser, get_current_user, require_permissions
from admin.core.response import ok
from admin.database import get_db
from admin.schemas.knowledge import (
    BatchDeleteRequest,
    KnowledgeUnitUpdate,
    UnitPermissionsUpdate,
)
from admin.services import knowledge_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/import")
async def import_knowledge(
    files: list[UploadFile] = File(...),
    current_user: CurrentUser = Depends(require_permissions("op:knowledge:import")),
    session: AsyncSession = Depends(get_db),
):
    task_ids = await knowledge_service.import_knowledge(session, current_user, files)
    return ok({"task_ids": task_ids}, message=f"{len(files)} files submitted")


@router.get("/import/tasks/{task_id}")
async def get_import_task(
    task_id: str,
    _: CurrentUser = Depends(get_current_user),
):
    data = await knowledge_service.get_import_task(task_id)
    return ok(data)


@router.get("/units")
async def list_units(
    keyword: str | None = Query(None),
    category: str | None = Query(None),
    status: str | None = Query(None),
    file_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: CurrentUser = Depends(require_permissions("op:knowledge:unit:read")),
    session: AsyncSession = Depends(get_db),
):
    data = await knowledge_service.list_units(
        session,
        keyword=keyword,
        category=category,
        status=status,
        file_type=file_type,
        page=page,
        page_size=page_size,
    )
    return ok(data.model_dump())


@router.get("/units/{unit_id}")
async def get_unit(
    unit_id: int,
    _: CurrentUser = Depends(require_permissions("op:knowledge:unit:read")),
    session: AsyncSession = Depends(get_db),
):
    data = await knowledge_service.get_unit_detail(session, unit_id)
    return ok(data.model_dump())


@router.put("/units/{unit_id}")
async def update_unit(
    unit_id: int,
    payload: KnowledgeUnitUpdate,
    _: CurrentUser = Depends(require_permissions("op:knowledge:unit:update")),
    session: AsyncSession = Depends(get_db),
):
    data = await knowledge_service.update_unit(session, unit_id, payload)
    return ok(data.model_dump())


@router.delete("/units")
async def delete_units(
    payload: BatchDeleteRequest,
    _: CurrentUser = Depends(require_permissions("op:knowledge:unit:delete")),
    session: AsyncSession = Depends(get_db),
):
    await knowledge_service.delete_units(session, payload.ids)
    return ok(None)


@router.get("/units/{unit_id}/permissions")
async def get_unit_permissions(
    unit_id: int,
    _: CurrentUser = Depends(require_permissions("op:knowledge:unit:read")),
    session: AsyncSession = Depends(get_db),
):
    data = await knowledge_service.get_unit_permissions(session, unit_id)
    return ok([p.model_dump() for p in data])


@router.post("/units/{unit_id}/permissions")
async def set_unit_permissions(
    unit_id: int,
    payload: UnitPermissionsUpdate,
    _: CurrentUser = Depends(require_permissions("op:knowledge:unit:update")),
    session: AsyncSession = Depends(get_db),
):
    await knowledge_service.set_unit_permissions(session, unit_id, payload.permissions)
    return ok(None)
