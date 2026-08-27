"""AI 鉴权问答路由：鉴权流式问答与会话历史管理。"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from admin.core.deps import CurrentUser, get_current_user, require_permissions
from admin.core.response import ok
from admin.database import get_db
from admin.schemas.ai import ChatStreamRequest
from admin.services import ai_chat_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatStreamRequest,
    current_user: CurrentUser = Depends(require_permissions("op:ai:chat")),
    session: AsyncSession = Depends(get_db),
):
    """鉴权问答（SSE 流式）：召回 → 数据权限过滤 → 白名单问答 → 代理转发。"""
    return StreamingResponse(
        ai_chat_service.chat_stream(session, current_user, payload.question, payload.session_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sessions")
async def list_sessions(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """我的会话列表（从问答事实聚合最近会话）。"""
    items = await ai_chat_service.list_sessions(session, current_user.id)
    return ok([item.model_dump() for item in items])


@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: str,
    _: CurrentUser = Depends(get_current_user),
):
    """历史消息（转发 RAG `/api/v1/history`）。"""
    data = await ai_chat_service.get_messages(session_id)
    return ok(data)


@router.delete("/sessions/{session_id}")
async def clear_session(
    session_id: str,
    _: CurrentUser = Depends(get_current_user),
):
    """清空会话（转发 RAG `/api/v1/history`）。"""
    data = await ai_chat_service.clear_session(session_id)
    return ok(data)
