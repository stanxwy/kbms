"""知识沉淀相关 Pydantic 模型：FAQ 审核/缓存与知识缺口。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from admin.schemas.common import PageResult


class FAQItem(BaseModel):
    """FAQ 列表/详情输出。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    answer: str
    category: str | None = None
    related_unit_id: int | None = None
    source_type: str
    status: str
    hit_count: int = 0
    reviewer_id: int | None = None
    reviewed_at: datetime | None = None


class FAQListResult(PageResult[FAQItem]):
    """FAQ 分页响应。"""


class FAQReviewRequest(BaseModel):
    """FAQ 审核请求：approve 发布 / reject 驳回。"""

    action: str = Field(..., pattern="^(approve|reject)$")
    edited_answer: str | None = Field(default=None, max_length=5000)
    category: str | None = Field(default=None, max_length=128)


class FAQUpdate(BaseModel):
    """FAQ 编辑请求（仅更新提供的字段）。"""

    question: str | None = Field(default=None, min_length=1)
    answer: str | None = Field(default=None, max_length=5000)
    category: str | None = Field(default=None, max_length=128)
    related_unit_id: int | None = Field(default=None, ge=1)


class KnowledgeGapItem(BaseModel):
    """知识缺口列表/详情输出。"""

    id: int
    question_pattern: str
    sample_questions: list[str] = Field(default_factory=list)
    ask_count: int = 0
    last_asked_at: datetime | None = None
    status: str
    resolved_unit_id: int | None = None


class KnowledgeGapListResult(PageResult[KnowledgeGapItem]):
    """知识缺口分页响应。"""


class KnowledgeGapResolveRequest(BaseModel):
    """知识缺口一键补全请求（创建草稿知识单元）。"""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = None
    category: str | None = Field(default=None, max_length=128)
