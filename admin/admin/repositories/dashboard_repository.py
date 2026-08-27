"""数据看板数据访问层：指标聚合、榜单与趋势原始数据读取。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.models.knowledge import KnowledgeUnit
from admin.models.log import QaAccessLog


async def get_metrics(session: AsyncSession) -> dict:
    """核心指标聚合：访问次数 / UV / Token 总量 / 平均耗时，外加知识单元数。"""
    access_count, uv, total_tokens, avg_response = (
        await session.execute(
            select(
                func.count(),
                func.count(func.distinct(QaAccessLog.user_id)),
                func.coalesce(func.sum(QaAccessLog.total_tokens), 0),
                func.coalesce(func.avg(QaAccessLog.response_time_ms), 0),
            ).select_from(QaAccessLog)
        )
    ).one()
    unit_count = (await session.execute(select(func.count()).select_from(KnowledgeUnit))).scalar_one()
    return {
        "access_count": access_count,
        "uv": uv,
        "unit_count": unit_count,
        "total_tokens": total_tokens,
        "avg_response_time_ms": float(avg_response),
    }


async def get_question_ranking(session: AsyncSession, limit: int) -> list[tuple[str, int]]:
    """高频问题 TOP 榜：按提问文本聚合计数，降序取前 N。"""
    count_label = func.count(QaAccessLog.id).label("cnt")
    rows = (
        await session.execute(
            select(QaAccessLog.question, count_label)
            .where(QaAccessLog.question.is_not(None))
            .group_by(QaAccessLog.question)
            .order_by(count_label.desc(), QaAccessLog.question.asc())
            .limit(limit)
        )
    ).all()
    return [(question, cnt) for question, cnt in rows]


async def get_authorized_unit_ids(session: AsyncSession) -> list[list[int]]:
    """读取全部「已授权使用」的知识单元 id 序列（供服务层归约成访问频次）。"""
    rows = (await session.execute(select(QaAccessLog.authorized_unit_ids_json))).scalars().all()
    return [ids for ids in rows if ids]


async def fetch_access_series(session: AsyncSession, since: datetime) -> list[tuple[datetime, int | None, int, int]]:
    """读取 ``since`` 之后的轻量时序数据：``(created_at, user_id, total_tokens, response_time_ms)``。

    只取时间桶归属与聚合所需的最小列，避免加载 answer/question 大文本。
    """
    rows = (
        await session.execute(
            select(
                QaAccessLog.created_at,
                QaAccessLog.user_id,
                QaAccessLog.total_tokens,
                QaAccessLog.response_time_ms,
            ).where(QaAccessLog.created_at >= since)
        )
    ).all()
    return [tuple(row) for row in rows]
