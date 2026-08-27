"""数据看板相关 Pydantic 模型：核心指标、榜单与趋势。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DashboardMetrics(BaseModel):
    """运营核心指标（基于 qa_access_logs 与 knowledge_units 聚合）。"""

    access_count: int = 0
    uv: int = 0
    unit_count: int = 0
    total_tokens: int = 0
    avg_response_time_ms: float = 0.0


class QuestionRankItem(BaseModel):
    """高频问题榜单项。"""

    question: str
    count: int


class UnitRankItem(BaseModel):
    """最常访问知识单元榜单项。"""

    unit_id: int
    title: str | None = None
    source_file_name: str | None = None
    count: int


class TokenTrendPoint(BaseModel):
    """Token 消耗与响应时间趋势桶。"""

    bucket: str
    total_tokens: int = 0
    avg_response_time_ms: float = 0.0


class AccessTrendPoint(BaseModel):
    """访问趋势桶。"""

    bucket: str
    access_count: int = 0
    uv: int = 0


class DashboardQuery(BaseModel):
    """看板趋势/榜单通用查询参数。"""

    granularity: str = Field("day", pattern="^(day|week)$")
    days: int = Field(30, ge=1, le=366)
    limit: int = Field(10, ge=1, le=50)
