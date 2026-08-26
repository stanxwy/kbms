"""Recall-only endpoint for KBMS admin.

Performs a hybrid (dense+sparse) search against the chunks collection and
returns the **distinct file_titles** with their top scores. The admin uses
``file_title`` as the cross-system anchor to look up ``KnowledgeUnit.id`` and
then runs ``check-permissions``.

Filter expression: ``file_title in [...]`` if the caller passed a list, else open.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.v1.deps import get_chunks_vector_db
from app.domain.ports.vector_db import ChunksVectorDB
from app.infra.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["recall"])


class RecallRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User question in natural language")
    top_k: int = Field(10, ge=1, le=50, description="Number of distinct file_titles to return")
    item_names: list[str] | None = Field(default=None, description="Optional filter by item_name (RAG-side item recognition)")


class RecallHit(BaseModel):
    file_title: str
    item_name: str | None = None
    score: float


class RecallResponse(BaseModel):
    hits: list[RecallHit]


@router.post("/recall", response_model=RecallResponse)
async def recall(
    payload: RecallRequest,
    vector_db: ChunksVectorDB = Depends(get_chunks_vector_db),
    settings: Settings = Depends(get_settings),
) -> RecallResponse:
    item_names = payload.item_names or []
    raw = vector_db.hybrid_search_chunks(payload.query, item_names=item_names)

    # Aggregate by file_title, keep the top score per title.
    best_by_title: dict[str, dict[str, Any]] = {}
    for hit in (raw or []):
        entity = hit.get("entity", {}) or {}
        file_title = entity.get("file_title")
        if not file_title:
            continue
        score = float(hit.get("distance") or 0.0)
        item_name = entity.get("item_name")
        existing = best_by_title.get(file_title)
        if existing is None or score > existing["score"]:
            best_by_title[file_title] = {"score": score, "item_name": item_name}

    sorted_hits = sorted(best_by_title.items(), key=lambda kv: kv[1]["score"], reverse=True)[: payload.top_k]
    return RecallResponse(
        hits=[RecallHit(file_title=ft, item_name=v["item_name"], score=v["score"]) for ft, v in sorted_hits]
    )