"""Delete-only endpoint for KBMS admin.

按 ``file_title``（跨系统锚点，对应 ``knowledge_units.source_file_name``）
删除 chunks 集合中的向量，服务知识单元删除时的「同步删向量」。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.deps import get_chunks_vector_db
from app.domain.ports.vector_db import ChunksVectorDB
from app.workflows.ingestion.exceptions import VectorDBError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chunk"])


@router.delete("/chunks/{file_title}")
async def delete_chunks(
    file_title: str,
    vector_db: ChunksVectorDB = Depends(get_chunks_vector_db),
) -> dict:
    try:
        result = vector_db.delete_data_by_file_title(file_title)
    except VectorDBError as exc:
        logger.exception("删除向量失败: %s", file_title)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    deleted_count = 0
    if isinstance(result, dict):
        deleted_count = int(result.get("delete_count") or 0)
    elif result is not None:
        deleted_count = int(getattr(result, "delete_count", 0))
    return {"deleted_count": deleted_count}