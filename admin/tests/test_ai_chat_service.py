"""ai_chat_service 单元测试。

覆盖：SSE 帧打包、无白名单时的权限提示短路、鉴权问答全链路（召回→鉴权→转发）。
RAG 依赖与访问日志写入通过 monkeypatch 打桩，不发起真实网络请求。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from admin.integrations import rag_client
from admin.models.knowledge import KnowledgeUnit, UnitPermission
from admin.models.user import User
from admin.services import ai_chat_service, settlement_service


def test_sse_pack():
    frame = ai_chat_service._sse_pack("delta", {"delta": "你好"})
    assert frame == 'event: delta\ndata: {"delta": "你好"}\n\n'


async def test_chat_stream_no_whitelist_shortcuts(session, monkeypatch):
    async def fake_recall(query, top_k=10, item_names=None):
        return {"hits": []}

    monkeypatch.setattr(rag_client, "recall", fake_recall)
    monkeypatch.setattr(settlement_service, "find_faq_match", AsyncMock(return_value=None))
    monkeypatch.setattr(ai_chat_service, "_write_access_log", AsyncMock())

    frames = [f async for f in ai_chat_service.chat_stream(session, SimpleNamespace(id=1), "问题", None)]
    joined = "\n".join(frames)

    assert "event: result" in joined
    assert "没有权限" in joined
    assert "event: sources" not in joined
    assert "event: delta" not in joined


async def test_chat_stream_authorized_flow(authz_session, monkeypatch):
    session = authz_session
    session.add(User(id=1, username="alice", password_hash="x", display_name="Alice", status=1))
    await session.flush()
    unit = KnowledgeUnit(id=1, unit_code="KU-1", title="Guide", source_file_name="guide", file_type="pdf")
    session.add(unit)
    await session.flush()
    session.add(UnitPermission(unit_id=unit.id, target_type="global", target_id=0))
    await session.flush()

    captured_focus: dict = {}

    async def fake_recall(query, top_k=10, item_names=None):
        return {"hits": [{"file_title": "guide", "score": 0.9}]}

    async def fake_query(query, session_id, is_stream=False, focus_file_titles=None):
        captured_focus["focus"] = list(focus_file_titles or [])
        return {"session_id": "rag-sid"}

    async def fake_stream(session_id):
        yield ("delta", {"delta": "你好"})
        yield ("final", {"answer": "你好"})

    monkeypatch.setattr(rag_client, "recall", fake_recall)
    monkeypatch.setattr(rag_client, "query", fake_query)
    monkeypatch.setattr(rag_client, "stream_events", fake_stream)
    monkeypatch.setattr(settlement_service, "find_faq_match", AsyncMock(return_value=None))
    monkeypatch.setattr(ai_chat_service, "_write_access_log", AsyncMock())

    frames = [f async for f in ai_chat_service.chat_stream(session, SimpleNamespace(id=1), "guide?", None)]
    joined = "\n".join(frames)

    assert captured_focus["focus"] == ["guide"]
    assert "event: sources" in joined
    assert "event: delta" in joined
    assert '"delta": "你好"' in joined
    assert "event: result" in joined
    assert "event: unauthorized" not in joined
