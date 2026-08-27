"""AI 鉴权问答与数据权限判定的 Pydantic 模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CheckPermissionsRequest(BaseModel):
    """数据权限批量判定请求。

    ``user_id`` 缺省时以当前登录用户为判定主体；内部（AI 服务）可显式指定。
    """

    unit_ids: list[int] = Field(..., min_length=1)
    user_id: int | None = Field(default=None, ge=1)


class CheckPermissionsResult(BaseModel):
    """数据权限判定结果。"""

    authorized_unit_ids: list[int] = Field(default_factory=list)
    unauthorized_unit_ids: list[int] = Field(default_factory=list)


class ChatStreamRequest(BaseModel):
    """鉴权问答（SSE 流式）请求。"""

    question: str = Field(..., min_length=1)
    session_id: str | None = Field(default=None, max_length=64)


class SourceItem(BaseModel):
    """知识引用来源卡片。"""

    unit_id: int
    title: str
    source_file_name: str


class UnauthorizedItem(BaseModel):
    """无权限召回项缺失提示。"""

    unit_id: int
    title: str


class SessionItem(BaseModel):
    """会话列表项（从 qa_access_logs 聚合最近会话）。"""

    session_id: str
    last_question: str | None = None
    updated_at: str | None = None
