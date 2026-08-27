"""知识沉淀数据访问层：FAQ、知识缺口与挖掘事实源读取。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.models.log import QaAccessLog
from admin.models.settlement import FAQ, KnowledgeGap


async def get_faq(session: AsyncSession, faq_id: int) -> FAQ | None:
    return await session.get(FAQ, faq_id)


async def list_faqs(
    session: AsyncSession,
    *,
    status: str | None,
    keyword: str | None,
    page: int,
    page_size: int,
) -> tuple[list[FAQ], int]:
    """按状态/关键词分页 FAQ，返回 (rows, total)。"""
    conditions = []
    if status:
        conditions.append(FAQ.status == status)
    if keyword:
        conditions.append(FAQ.question.ilike(f"%{keyword}%"))

    count_stmt = select(func.count()).select_from(FAQ)
    stmt = select(FAQ)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
        stmt = stmt.where(*conditions)

    total = (await session.execute(count_stmt)).scalar_one()
    rows = (
        (await session.execute(stmt.order_by(FAQ.id.desc()).offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )
    return list(rows), total


async def list_published_faqs(session: AsyncSession) -> list[FAQ]:
    """读取全部已发布 FAQ（供语义命中匹配）。"""
    return list((await session.execute(select(FAQ).where(FAQ.status == "published"))).scalars())


async def list_faq_questions(session: AsyncSession) -> set[str]:
    """已存在 FAQ 的问题文本集合（供挖掘去重，避免重复生成候选）。"""
    return set((await session.execute(select(FAQ.question))).scalars())


async def get_gap(session: AsyncSession, gap_id: int) -> KnowledgeGap | None:
    return await session.get(KnowledgeGap, gap_id)


async def list_gaps(
    session: AsyncSession,
    *,
    status: str | None,
    keyword: str | None,
    page: int,
    page_size: int,
) -> tuple[list[KnowledgeGap], int]:
    """按状态/关键词分页知识缺口，返回 (rows, total)。"""
    conditions = []
    if status:
        conditions.append(KnowledgeGap.status == status)
    if keyword:
        conditions.append(KnowledgeGap.question_pattern.ilike(f"%{keyword}%"))

    count_stmt = select(func.count()).select_from(KnowledgeGap)
    stmt = select(KnowledgeGap)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
        stmt = stmt.where(*conditions)

    total = (await session.execute(count_stmt)).scalar_one()
    rows = (
        (await session.execute(stmt.order_by(KnowledgeGap.id.desc()).offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )
    return list(rows), total


async def list_unresolved_gaps(session: AsyncSession) -> list[KnowledgeGap]:
    """未解决缺口（供挖掘幂等更新，避免重复建缺口）。"""
    return list((await session.execute(select(KnowledgeGap).where(KnowledgeGap.status == "unresolved"))).scalars())


async def fetch_recent_logs(
    session: AsyncSession, since: datetime
) -> list[tuple[str, str | None, list | None, datetime]]:
    """读取窗口内问答事实：``(question, answer, authorized_unit_ids, created_at)``。

    轻量列投影，避免加载 prompt/completion token 等无关大字段；供挖掘服务的
    频次聚合与「未命中」判定在 Python 内归约。
    """
    rows = (
        await session.execute(
            select(
                QaAccessLog.question,
                QaAccessLog.answer,
                QaAccessLog.authorized_unit_ids_json,
                QaAccessLog.created_at,
            ).where(QaAccessLog.created_at >= since, QaAccessLog.question.is_not(None))
        )
    ).all()
    return [tuple(row) for row in rows]
