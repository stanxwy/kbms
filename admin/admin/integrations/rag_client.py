"""RAG 核心 HTTP 客户端。

封装 admin 对 RAG `/api/v1` 的调用（upload / chunks / recall / embed / query /
task / history），统一超时、重试与错误处理。

说明：RAG 侧响应并非 admin 统一的 `{code, message, data}` 结构，本模块只负责
「发起请求 → 解析 JSON → 出错抛 :class:`RagError`」，字段判读交给业务层。
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx

from admin.config import get_settings
from admin.core.exceptions import AppError

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=5.0)
_GET_RETRIES = 2


class RagError(AppError):
    """RAG 服务调用失败（作为网关 502 返回给前端）。"""

    status_code = 502
    code = 502
    message = "rag service error"


async def _request(method: str, path: str, *, retries: int = 0, **kwargs: Any) -> dict[str, Any]:
    settings = get_settings()
    url = f"{settings.RAG_BASE_URL.rstrip('/')}{path}"
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
                response = await client.request(method, url, **kwargs)
            if response.is_error:
                raise RagError(f"RAG 返回 HTTP {response.status_code}: {response.text[:200]}")
            return response.json() if response.content else {}
        except httpx.HTTPError as exc:
            last_error = exc
            if attempt >= retries:
                break
            logger.warning("RAG 请求失败，重试 %d/%d：%s", attempt + 1, retries, exc)
    raise RagError(f"RAG 服务不可达：{last_error}") from last_error


async def upload_files(files: list[tuple[str, bytes, str]]) -> list[str]:
    """上传文件到 RAG，返回与输入顺序对应的 task_ids。

    ``files`` 每个元素为 ``(filename, content_bytes, content_type)``。
    """
    payload = [("files", (name, content, ctype)) for name, content, ctype in files]
    data = await _request("POST", "/api/v1/upload", files=payload)
    return list(data.get("task_ids") or [])


async def get_task_status(task_id: str) -> dict[str, Any]:
    """查询导入任务进度。"""
    return await _request("GET", f"/api/v1/task/status/{quote(task_id)}", retries=_GET_RETRIES)


async def delete_chunks(file_title: str) -> int:
    """按 file_title 删除向量 chunk（跨系统锚点）。"""
    data = await _request("DELETE", f"/api/v1/chunks/{quote(file_title)}")
    return int(data.get("deleted_count") or 0)


async def recall(query: str, top_k: int = 10, item_names: list[str] | None = None) -> dict[str, Any]:
    """候选召回：返回去重后的 file_title 列表。"""
    body: dict[str, Any] = {"query": query, "top_k": top_k}
    if item_names:
        body["item_names"] = item_names
    return await _request("POST", "/api/v1/recall", json=body)


async def embed(texts: list[str]) -> dict[str, Any]:
    """文本向量化（FAQ 缓存 / 缺口聚类复用）。"""
    return await _request("POST", "/api/v1/embed", json={"texts": texts})


async def query(
    query: str,
    session_id: str,
    is_stream: bool = False,
    focus_file_titles: list[str] | None = None,
) -> dict[str, Any]:
    """鉴权问答（非流式返回 answer，流式返回 session_id/task_id）。"""
    body: dict[str, Any] = {
        "query": query,
        "session_id": session_id,
        "is_stream": is_stream,
    }
    if focus_file_titles:
        body["focus_file_titles"] = focus_file_titles
    return await _request("POST", "/api/v1/query", json=body)


async def get_history(session_id: str, limit: int = 50) -> dict[str, Any]:
    """查询会话历史信息。"""
    return await _request("GET", f"/api/v1/history/{quote(session_id)}", params={"limit": limit}, retries=_GET_RETRIES)


async def clear_history(session_id: str) -> dict[str, Any]:
    """清空会话历史。"""
    return await _request("DELETE", f"/api/v1/history/{quote(session_id)}")
