"""Embed-only endpoint for KBMS admin.

BGE-M3 produces both dense (1024-dim) and sparse vectors; admin uses these for
FAQ semantic caching and knowledge-gap clustering without spinning up its own
embedding model.

Sparse vectors are returned as ``{token_id: weight}`` dicts to keep the JSON
payload compact and human-readable.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.v1.deps import get_embedder
from app.domain.ports.embedder import Embedder

logger = logging.getLogger(__name__)

router = APIRouter(tags=["embed"])


class EmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=64)


class EmbedResponse(BaseModel):
    dense: list[list[float]]
    sparse: list[dict[int, float]]  # sparse[i][token_id] = weight


@router.post("/embed", response_model=EmbedResponse)
async def embed(payload: EmbedRequest, embedder: Embedder = Depends(get_embedder)) -> EmbedResponse:
    out = embedder.generate_embeddings(payload.texts)
    return EmbedResponse(dense=out["dense"], sparse=out["sparse"])