"""知识沉淀服务：FAQ 挖掘/审核/缓存命中与知识缺口识别。

FAQ 缓存语义匹配与缺口聚类复用 RAG `/embed`（BGE-M3 稠密向量），不本地部署向量模型；
挖掘算法为「频次聚合 + 贪心语义去重 + 阈值筛选」，结果落 PostgreSQL（faqs / knowledge_gaps）。
"""

from __future__ import annotations

import math
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from admin.config import get_settings
from admin.core.deps import CurrentUser
from admin.core.exceptions import NotFoundError
from admin.integrations import rag_client
from admin.models.knowledge import KnowledgeUnit
from admin.models.settlement import FAQ, KnowledgeGap
from admin.repositories import settlement_repository
from admin.schemas.settlement import (
    FAQItem,
    FAQListResult,
    FAQReviewRequest,
    FAQUpdate,
    KnowledgeGapItem,
    KnowledgeGapListResult,
    KnowledgeGapResolveRequest,
)

# 单个缺口聚类最多保留的样本问题数。
_GAP_SAMPLE_MAX = 5
# RAG /embed 单次请求文本数上限。
_EMBED_BATCH = 64


@dataclass
class _Cluster:
    """一次语义聚类结果：代表问题 + 聚合频次 + 成员问题。"""

    representative: str
    frequency: int
    members: list[str]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """稠密向量余弦相似度；维度不一致或零向量时返回 0。"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _semantic_cluster(
    questions: list[str],
    vectors: list[list[float]],
    freqs: dict[str, int],
    threshold: float,
) -> list[_Cluster]:
    """贪心语义去重：按频次降序，首见问题建簇，相似问题并入（余弦 ≥ 阈值）。"""
    n = len(questions)
    assigned = [False] * n
    clusters: list[_Cluster] = []
    for i in range(n):
        if assigned[i]:
            continue
        rep = questions[i]
        members = [rep]
        freq = freqs.get(rep, 0)
        assigned[i] = True
        for j in range(i + 1, n):
            if assigned[j]:
                continue
            if _cosine_similarity(vectors[i], vectors[j]) >= threshold:
                members.append(questions[j])
                freq += freqs.get(questions[j], 0)
                assigned[j] = True
        clusters.append(_Cluster(representative=rep, frequency=freq, members=members))
    return clusters


async def _embed_texts(texts: list[str]) -> list[list[float]]:
    """批量向量化（按 /embed 上限分批），返回与输入顺序对应的稠密向量。"""
    if not texts:
        return []
    dense: list[list[float]] = []
    for i in range(0, len(texts), _EMBED_BATCH):
        chunk = texts[i : i + _EMBED_BATCH]
        data = await rag_client.embed(chunk)
        dense.extend(data.get("dense") or [])
    return dense


def _window_since(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


def _gap_to_item(gap: KnowledgeGap) -> KnowledgeGapItem:
    return KnowledgeGapItem(
        id=gap.id,
        question_pattern=gap.question_pattern,
        sample_questions=gap.sample_questions_json or [],
        ask_count=gap.ask_count,
        last_asked_at=gap.last_asked_at,
        status=gap.status,
        resolved_unit_id=gap.resolved_unit_id,
    )


async def mine_faqs(session: AsyncSession) -> dict[str, int]:
    """FAQ 自动挖掘：窗口内问答 → 频次聚合 + 语义去重 → 待审核候选落库。

    仅当聚类频次达 ``FAQ_MIN_FREQ_THRESHOLD`` 且代表问题尚未入 faqs 时写入，
    答案留空由审核环节补充（``source_type=auto_mined, status=pending_review``）。
    """
    settings = get_settings()
    since = _window_since(settings.FAQ_MIN_WINDOW_DAYS)
    rows = await settlement_repository.fetch_recent_logs(session, since)

    freqs: Counter[str] = Counter()
    for question, _answer, _authorized, _ts in rows:
        text = (question or "").strip()
        if text:
            freqs[text] += 1
    if not freqs:
        return {"mined": 0}

    questions = [q for q, _ in freqs.most_common()]
    vectors = await _embed_texts(questions)
    clusters = _semantic_cluster(questions, vectors, freqs, settings.FAQ_MATCH_THRESHOLD)

    existing = await settlement_repository.list_faq_questions(session)
    created = 0
    for cluster in clusters:
        if cluster.frequency < settings.FAQ_MIN_FREQ_THRESHOLD:
            continue
        if cluster.representative in existing:
            continue
        session.add(
            FAQ(
                question=cluster.representative,
                answer="",
                source_type="auto_mined",
                status="pending_review",
            )
        )
        created += 1
    await session.commit()
    return {"mined": created}


async def identify_gaps(session: AsyncSession) -> dict[str, int]:
    """知识缺口识别：窗口内「未命中」（无授权单元/无回答）提问聚类为未解决缺口。

    以 question_pattern 幂等：已存在 unresolved 缺口则更新频次与样本，否则新建。
    """
    settings = get_settings()
    since = _window_since(settings.FAQ_MIN_WINDOW_DAYS)
    rows = await settlement_repository.fetch_recent_logs(session, since)

    freqs: Counter[str] = Counter()
    latest: dict[str, datetime] = {}
    for question, answer, authorized, ts in rows:
        text = (question or "").strip()
        if not text:
            continue
        if answer or authorized:
            continue  # 已命中/已回答，不视为缺口
        freqs[text] += 1
        if text not in latest or ts > latest[text]:
            latest[text] = ts
    if not freqs:
        return {"gaps_created": 0, "gaps_updated": 0}

    questions = [q for q, _ in freqs.most_common()]
    vectors = await _embed_texts(questions)
    clusters = _semantic_cluster(questions, vectors, freqs, settings.FAQ_MATCH_THRESHOLD)

    unresolved = {g.question_pattern: g for g in await settlement_repository.list_unresolved_gaps(session)}
    created = updated = 0
    for cluster in clusters:
        rep = cluster.representative
        sample = cluster.members[:_GAP_SAMPLE_MAX]
        gap = unresolved.get(rep)
        if gap is not None:
            gap.ask_count = cluster.frequency
            gap.sample_questions_json = sample
            gap.last_asked_at = latest[rep]
            updated += 1
        else:
            session.add(
                KnowledgeGap(
                    question_pattern=rep,
                    sample_questions_json=sample,
                    ask_count=cluster.frequency,
                    last_asked_at=latest[rep],
                    status="unresolved",
                )
            )
            created += 1
    await session.commit()
    return {"gaps_created": created, "gaps_updated": updated}


async def mine_knowledge(session: AsyncSession) -> dict[str, int]:
    """沉淀挖掘总入口：一次跑 FAQ 挖掘 + 知识缺口识别。"""
    faq_result = await mine_faqs(session)
    gap_result = await identify_gaps(session)
    return {**faq_result, **gap_result}


async def find_faq_match(session: AsyncSession, question: str) -> FAQ | None:
    """语义匹配已发布 FAQ，命中则返回该 FAQ 并累加 hit_count（由调用方提交）。

    无已发布 FAQ 或最佳相似度低于 ``FAQ_MATCH_THRESHOLD`` 时返回 None。
    """
    faqs = await settlement_repository.list_published_faqs(session)
    if not faqs:
        return None

    texts = [question, *[f.question for f in faqs]]
    vectors = await _embed_texts(texts)
    if len(vectors) < len(texts):
        return None

    question_vec = vectors[0]
    threshold = get_settings().FAQ_MATCH_THRESHOLD
    best: FAQ | None = None
    best_score = -1.0
    for faq, faq_vec in zip(faqs, vectors[1:], strict=True):
        score = _cosine_similarity(question_vec, faq_vec)
        if score > best_score:
            best_score = score
            best = faq
    if best is not None and best_score >= threshold:
        best.hit_count += 1
        return best
    return None


async def list_faq_recommendations(session: AsyncSession, *, page: int, page_size: int) -> FAQListResult:
    """待审核 FAQ 推荐列表（status=pending_review）。"""
    rows, total = await settlement_repository.list_faqs(
        session, status="pending_review", keyword=None, page=page, page_size=page_size
    )
    return FAQListResult(items=[FAQItem.model_validate(f) for f in rows], total=total, page=page, page_size=page_size)


async def list_faqs(
    session: AsyncSession,
    *,
    status: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> FAQListResult:
    """已发布/按状态 FAQ 列表。"""
    rows, total = await settlement_repository.list_faqs(
        session, status=status, keyword=keyword, page=page, page_size=page_size
    )
    return FAQListResult(items=[FAQItem.model_validate(f) for f in rows], total=total, page=page, page_size=page_size)


async def review_faq(
    session: AsyncSession, faq_id: int, current_user: CurrentUser, payload: FAQReviewRequest
) -> FAQItem:
    """FAQ 审核：approve 发布（可选覆盖标准答案），reject 驳回。"""
    faq = await settlement_repository.get_faq(session, faq_id)
    if faq is None:
        raise NotFoundError("FAQ 不存在")

    if payload.action == "approve":
        if payload.edited_answer is not None:
            faq.answer = payload.edited_answer
        faq.status = "published"
    else:
        faq.status = "rejected"
    if payload.category is not None:
        faq.category = payload.category

    faq.reviewer_id = current_user.id
    faq.reviewed_at = datetime.now(UTC)
    await session.commit()
    return FAQItem.model_validate(faq)


async def update_faq(session: AsyncSession, faq_id: int, data: FAQUpdate) -> FAQItem:
    """编辑 FAQ（仅更新提供的字段）。"""
    faq = await settlement_repository.get_faq(session, faq_id)
    if faq is None:
        raise NotFoundError("FAQ 不存在")
    if data.question is not None:
        faq.question = data.question
    if data.answer is not None:
        faq.answer = data.answer
    if data.category is not None:
        faq.category = data.category
    if data.related_unit_id is not None:
        faq.related_unit_id = data.related_unit_id
    await session.commit()
    return FAQItem.model_validate(faq)


async def delete_faq(session: AsyncSession, faq_id: int) -> None:
    """删除 FAQ。"""
    faq = await settlement_repository.get_faq(session, faq_id)
    if faq is None:
        raise NotFoundError("FAQ 不存在")
    await session.delete(faq)
    await session.commit()


async def list_knowledge_gaps(
    session: AsyncSession,
    *,
    status: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> KnowledgeGapListResult:
    """知识缺口列表。"""
    rows, total = await settlement_repository.list_gaps(
        session, status=status, keyword=keyword, page=page, page_size=page_size
    )
    return KnowledgeGapListResult(items=[_gap_to_item(g) for g in rows], total=total, page=page, page_size=page_size)


async def resolve_gap(
    session: AsyncSession, gap_id: int, current_user: CurrentUser, payload: KnowledgeGapResolveRequest
) -> KnowledgeGapItem:
    """一键补全：据缺口创建草稿知识单元并标记 resolved。"""
    gap = await settlement_repository.get_gap(session, gap_id)
    if gap is None:
        raise NotFoundError("知识缺口不存在")

    unit = KnowledgeUnit(
        unit_code=f"KU-{uuid.uuid4().hex}",
        title=payload.title or gap.question_pattern,
        content=payload.content,
        category=payload.category,
        source_file_name=f"gap-{gap_id}-{uuid.uuid4().hex[:8]}",
        file_type="manual",
        file_size=0,
        status="draft",
        creator_id=current_user.id,
    )
    session.add(unit)
    await session.flush()

    gap.status = "resolved"
    gap.resolved_unit_id = unit.id
    await session.commit()
    return _gap_to_item(gap)


async def ignore_gap(session: AsyncSession, gap_id: int) -> None:
    """忽略知识缺口。"""
    gap = await settlement_repository.get_gap(session, gap_id)
    if gap is None:
        raise NotFoundError("知识缺口不存在")
    gap.status = "ignored"
    await session.commit()
