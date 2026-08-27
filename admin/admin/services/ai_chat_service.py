"""AI 鉴权问答服务：召回 → 数据权限过滤 → 白名单问答 → SSE 代理转发。"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.core.deps import CurrentUser
from admin.integrations import rag_client
from admin.models.log import QaAccessLog
from admin.repositories import knowledge_repository
from admin.schemas.ai import SessionItem
from admin.services import permission_engine


def _sse_pack(event: str, data: dict[str, Any]) -> str:
    """打包为 SSE 文本帧（``event:`` / ``data:`` 两行一组）。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def chat_stream(
    session: AsyncSession,
    current_user: CurrentUser,
    question: str,
    session_id: str | None,
) -> AsyncIterator[str]:
    """鉴权问答 SSE 生成器。

    流程：RAG recall 候选 → file_title 映射知识单元 → 数据权限过滤 →
    输出 unauthorized/sources → 以白名单提交 RAG query → 代理转发 delta/result/error。
    """
    started = time.perf_counter()
    sid = session_id or str(uuid.uuid4())

    # 1. 候选召回（去重 file_title）。
    recall_data = await rag_client.recall(question)
    hits = recall_data.get("hits") or []
    titles = [h.get("file_title") for h in hits if h.get("file_title")]

    # 2. file_title 锚点映射知识单元。
    units = await knowledge_repository.get_units_by_source_file_names(session, titles)
    authorized_ids = set()
    unauthorized_ids: list[int] = []
    unit_by_id = {u.id: u for u in units}
    if units:
        perm = await permission_engine.check_permissions(session, current_user.id, [u.id for u in units])
        authorized_ids = set(perm.authorized_unit_ids)
        unauthorized_ids = perm.unauthorized_unit_ids

    authorized_units = [unit_by_id[u] for u in authorized_ids if u in unit_by_id]
    unauthorized_units = [unit_by_id[u] for u in unauthorized_ids if u in unit_by_id]
    white_titles = [u.source_file_name for u in authorized_units]

    # 3. 先输出权限缺失与引用来源。
    if unauthorized_units:
        yield _sse_pack(
            "unauthorized",
            {"items": [{"unit_id": u.id, "title": u.title} for u in unauthorized_units]},
        )
    if authorized_units:
        yield _sse_pack(
            "sources",
            {
                "items": [
                    {"unit_id": u.id, "title": u.title, "source_file_name": u.source_file_name}
                    for u in authorized_units
                ]
            },
        )

    final_answer = ""
    try:
        # 4. 无可用白名单：不进入 RAG，直接给出权限提示（避免无关检索泄露）。
        if not white_titles:
            final_answer = "抱歉，您没有权限访问相关的知识内容，请联系管理员配置数据权限。"
            yield _sse_pack("result", {"answer": final_answer, "session_id": sid})
            return

        # 5. 提交白名单问答任务，取得 RAG 侧流式会话。
        resp = await rag_client.query(question, sid, is_stream=True, focus_file_titles=white_titles)
        rag_session_id = resp.get("session_id") or sid

        # 6. 代理转发 RAG 流式事件为 admin 事件协议。
        async for event, data in rag_client.stream_events(rag_session_id):
            if event == "delta":
                delta = data.get("delta") or ""
                final_answer += delta
                yield _sse_pack("delta", {"delta": delta})
            elif event == "final":
                final_answer = data.get("answer") or final_answer
                yield _sse_pack("result", {"answer": final_answer, "session_id": sid})
            elif event == "error":
                yield _sse_pack("error", {"error": data.get("error") or "rag error"})
    finally:
        # 7. 记录问答事实（异步聚合看板与沉淀的事实来源）。
        await _write_access_log(
            session,
            session_id=sid,
            user_id=current_user.id,
            question=question,
            answer=final_answer,
            recalled_unit_ids=[u.id for u in units],
            authorized_unit_ids=list(authorized_ids),
            unauthorized_unit_ids=unauthorized_ids,
            response_time_ms=int((time.perf_counter() - started) * 1000),
        )


async def _write_access_log(
    session: AsyncSession,
    *,
    session_id: str,
    user_id: int,
    question: str,
    answer: str,
    recalled_unit_ids: list[int],
    authorized_unit_ids: list[int],
    unauthorized_unit_ids: list[int],
    response_time_ms: int,
) -> None:
    """落一条问答访问事实（token 统计由 RAG 侧补充，此处缺省记 0）。"""
    session.add(
        QaAccessLog(
            session_id=session_id,
            user_id=user_id,
            question=question,
            answer=answer,
            recalled_unit_ids_json=recalled_unit_ids,
            authorized_unit_ids_json=authorized_unit_ids,
            unauthorized_unit_ids_json=unauthorized_unit_ids,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            response_time_ms=response_time_ms,
        )
    )
    await session.commit()


async def list_sessions(session: AsyncSession, user_id: int) -> list[SessionItem]:
    """聚合当前用户最近会话（按 session_id 去重，取最近提问）。"""
    rows = (
        (
            await session.execute(
                select(QaAccessLog)
                .where(QaAccessLog.user_id == user_id)
                .order_by(QaAccessLog.created_at.desc())
                .limit(200)
            )
        )
        .scalars()
        .all()
    )

    latest_by_session: dict[str, QaAccessLog] = {}
    for log in rows:
        latest_by_session.setdefault(log.session_id, log)

    items = [
        SessionItem(
            session_id=log.session_id,
            last_question=log.question,
            updated_at=log.created_at.isoformat() if log.created_at else None,
        )
        for log in latest_by_session.values()
    ]
    items.sort(key=lambda i: i.updated_at or "", reverse=True)
    return items


async def get_messages(session_id: str, limit: int = 50) -> dict[str, Any]:
    """转发 RAG 会话历史。"""
    return await rag_client.get_history(session_id, limit)


async def clear_session(session_id: str) -> dict[str, Any]:
    """转发 RAG 清空会话。"""
    return await rag_client.clear_history(session_id)
