"""settlement_service 单元测试。

覆盖：FAQ 自动挖掘（频次聚合 + 语义去重 + 阈值/幂等）、知识缺口识别、
FAQ 语义缓存命中、FAQ 审核/编辑/删除、知识缺口补全与忽略。
RAG /embed 通过 monkeypatch 打桩返回确定性向量，不发起真实网络请求。
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from admin.core.exceptions import NotFoundError
from admin.integrations import rag_client
from admin.models.knowledge import KnowledgeUnit
from admin.models.log import QaAccessLog
from admin.models.settlement import FAQ, KnowledgeGap
from admin.schemas.settlement import FAQReviewRequest, FAQUpdate, KnowledgeGapResolveRequest
from admin.services import settlement_service


# ---- 纯函数 ----
def test_cosine_similarity():
    assert settlement_service._cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert settlement_service._cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    # 维度不一致 / 零向量返回 0。
    assert settlement_service._cosine_similarity([], []) == 0.0
    assert settlement_service._cosine_similarity([1.0], [1.0, 0.0]) == 0.0


def test_semantic_cluster_groups_similar():
    questions = ["q1", "q2", "q3"]
    vectors = [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]]
    freqs = {"q1": 2, "q2": 1, "q3": 3}

    clusters = settlement_service._semantic_cluster(questions, vectors, freqs, 0.85)

    by_rep = {c.representative: c for c in clusters}
    assert set(by_rep) == {"q1", "q3"}
    assert by_rep["q1"].members == ["q1", "q2"]
    assert by_rep["q1"].frequency == 3
    assert by_rep["q3"].frequency == 3


def test_window_since_is_aware():
    since = settlement_service._window_since(7)
    assert since.tzinfo is not None


# ---- FAQ 挖掘 ----
async def test_mine_faqs_creates_pending_candidate(settlement_session, monkeypatch):
    session = settlement_session
    monkeypatch.setattr(settlement_service, "_window_since", lambda days: datetime(2026, 1, 1))
    for i in range(5):
        session.add(QaAccessLog(id=i + 1, session_id=f"s{i}", question="如何登录？", created_at=datetime(2026, 8, 1)))
    await session.commit()

    async def fake_embed(texts):
        return {"dense": [[1.0, 0.0] for _ in texts]}

    monkeypatch.setattr(rag_client, "embed", fake_embed)

    result = await settlement_service.mine_faqs(session)

    assert result == {"mined": 1}
    faq = (await session.execute(select(FAQ))).scalar_one()
    assert faq.question == "如何登录？"
    assert faq.status == "pending_review"
    assert faq.source_type == "auto_mined"
    assert faq.answer == ""


async def test_mine_faqs_skips_below_threshold(settlement_session, monkeypatch):
    session = settlement_session
    monkeypatch.setattr(settlement_service, "_window_since", lambda days: datetime(2026, 1, 1))
    for i in range(4):
        session.add(QaAccessLog(id=i + 1, session_id=f"s{i}", question="如何登录？", created_at=datetime(2026, 8, 1)))
    await session.commit()

    async def fake_embed(texts):
        return {"dense": [[1.0, 0.0] for _ in texts]}

    monkeypatch.setattr(rag_client, "embed", fake_embed)

    assert await settlement_service.mine_faqs(session) == {"mined": 0}


async def test_mine_faqs_semantic_dedup(settlement_session, monkeypatch):
    session = settlement_session
    monkeypatch.setattr(settlement_service, "_window_since", lambda days: datetime(2026, 1, 1))
    specs = [("如何登录？", None)] * 3 + [("怎么登录系统", None)] * 2
    for i, (q, _a) in enumerate(specs, start=1):
        session.add(QaAccessLog(id=i, session_id=f"s{i}", question=q, created_at=datetime(2026, 8, 1)))
    await session.commit()

    async def fake_embed(texts):
        # 两个提问派发同一向量 → 相似度 1.0，聚成一行，频次 3+2=5 达阈值。
        return {"dense": [[1.0, 0.0] for _ in texts]}

    monkeypatch.setattr(rag_client, "embed", fake_embed)

    result = await settlement_service.mine_faqs(session)
    assert result == {"mined": 1}
    faq = (await session.execute(select(FAQ))).scalar_one()
    assert faq.question == "如何登录？"


async def test_mine_faqs_skips_existing_question(settlement_session, monkeypatch):
    session = settlement_session
    session.add(FAQ(question="如何登录？", answer="", source_type="manual", status="published"))
    await session.commit()

    monkeypatch.setattr(settlement_service, "_window_since", lambda days: datetime(2026, 1, 1))
    for i in range(5):
        session.add(QaAccessLog(id=i + 1, session_id=f"s{i}", question="如何登录？", created_at=datetime(2026, 8, 1)))
    await session.commit()

    async def fake_embed(texts):
        return {"dense": [[1.0, 0.0] for _ in texts]}

    monkeypatch.setattr(rag_client, "embed", fake_embed)

    assert await settlement_service.mine_faqs(session) == {"mined": 0}


async def test_mine_faqs_empty(settlement_session, monkeypatch):
    monkeypatch.setattr(settlement_service, "_window_since", lambda days: datetime(2026, 1, 1))
    assert await settlement_service.mine_faqs(settlement_session) == {"mined": 0}


# ---- 知识缺口识别 ----
async def test_identify_gaps_creates_unresolved(settlement_session, monkeypatch):
    session = settlement_session
    monkeypatch.setattr(settlement_service, "_window_since", lambda days: datetime(2026, 1, 1))
    for i in range(3):
        session.add(QaAccessLog(id=i + 1, session_id=f"s{i}", question="什么是RAG？", created_at=datetime(2026, 8, 1)))
    await session.commit()

    async def fake_embed(texts):
        return {"dense": [[1.0, 0.0] for _ in texts]}

    monkeypatch.setattr(rag_client, "embed", fake_embed)

    result = await settlement_service.identify_gaps(session)
    assert result["gaps_created"] == 1
    gap = (await session.execute(select(KnowledgeGap))).scalar_one()
    assert gap.question_pattern == "什么是RAG？"
    assert gap.ask_count == 3
    assert gap.status == "unresolved"
    assert gap.sample_questions_json == ["什么是RAG？"]


async def test_identify_gaps_skips_answered_or_authorized(settlement_session, monkeypatch):
    session = settlement_session
    monkeypatch.setattr(settlement_service, "_window_since", lambda days: datetime(2026, 1, 1))
    specs = [
        ("怎么做X？", "这是一条回答"),  # 已回答 → 非缺口
        ("怎么做Y？", None, [1]),  # 已授权单元 → 非缺口
        ("怎么做X？", None, None),  # 未命中 → 缺口
    ]
    for i, spec in enumerate(specs, start=1):
        q, answer = spec[0], spec[1]
        authorized = spec[2] if len(spec) > 2 else None
        session.add(
            QaAccessLog(
                id=i,
                session_id=f"s{i}",
                question=q,
                answer=answer,
                authorized_unit_ids_json=authorized,
                created_at=datetime(2026, 8, 1),
            )
        )
    await session.commit()

    async def fake_embed(texts):
        return {"dense": [[1.0, 0.0] for _ in texts]}

    monkeypatch.setattr(rag_client, "embed", fake_embed)

    result = await settlement_service.identify_gaps(session)
    assert result["gaps_created"] == 1
    gap = (await session.execute(select(KnowledgeGap))).scalar_one()
    assert gap.question_pattern == "怎么做X？"
    assert gap.ask_count == 1


async def test_identify_gaps_updates_existing_unresolved(settlement_session, monkeypatch):
    session = settlement_session
    session.add(
        KnowledgeGap(
            question_pattern="怎么做X？", sample_questions_json=["怎么做X？"], ask_count=1, status="unresolved"
        )
    )
    await session.commit()

    monkeypatch.setattr(settlement_service, "_window_since", lambda days: datetime(2026, 1, 1))
    for i in range(2):
        session.add(QaAccessLog(id=i + 1, session_id=f"s{i}", question="怎么做X？", created_at=datetime(2026, 8, 1)))
    await session.commit()

    async def fake_embed(texts):
        return {"dense": [[1.0, 0.0] for _ in texts]}

    monkeypatch.setattr(rag_client, "embed", fake_embed)

    result = await settlement_service.identify_gaps(session)
    assert result["gaps_created"] == 0
    assert result["gaps_updated"] == 1
    gap = (await session.execute(select(KnowledgeGap))).scalar_one()
    assert gap.ask_count == 2


# ---- FAQ 语义缓存命中 ----
async def test_find_faq_match_hit(settlement_session, monkeypatch):
    session = settlement_session
    session.add(FAQ(question="如何登录？", answer="标准答案", source_type="manual", status="published"))
    await session.commit()

    async def fake_embed(texts):
        return {"dense": [[1.0, 0.0] for _ in texts]}

    monkeypatch.setattr(rag_client, "embed", fake_embed)

    faq = await settlement_service.find_faq_match(session, "怎么登录")
    assert faq is not None
    assert faq.answer == "标准答案"
    assert faq.hit_count == 1


async def test_find_faq_match_miss(settlement_session, monkeypatch):
    session = settlement_session
    session.add(FAQ(question="如何登录？", answer="标准答案", source_type="manual", status="published"))
    await session.commit()

    async def fake_embed(texts):
        # 问题向量与 FAQ 向量正交 → 相似度 0.0。
        return {"dense": [[1.0, 0.0], [0.0, 1.0]]}

    monkeypatch.setattr(rag_client, "embed", fake_embed)

    assert await settlement_service.find_faq_match(session, "报销流程") is None


async def test_find_faq_match_no_published(settlement_session):
    session = settlement_session
    session.add(FAQ(question="如何登录？", answer="x", source_type="manual", status="pending_review"))
    await session.commit()

    assert await settlement_service.find_faq_match(session, "怎么登录") is None


# ---- FAQ 审核 ----
async def test_review_faq_approve(settlement_session):
    session = settlement_session
    session.add(FAQ(question="q", answer="", source_type="auto_mined", status="pending_review"))
    await session.commit()
    faq = (await session.execute(select(FAQ))).scalar_one()

    payload = FAQReviewRequest(action="approve", edited_answer="标准答案", category="登录")
    item = await settlement_service.review_faq(session, faq.id, SimpleNamespace(id=9), payload)

    assert item.status == "published"
    assert item.answer == "标准答案"
    assert item.category == "登录"
    assert item.reviewer_id == 9
    assert item.reviewed_at is not None


async def test_review_faq_reject(settlement_session):
    session = settlement_session
    session.add(FAQ(question="q", answer="", source_type="auto_mined", status="pending_review"))
    await session.commit()
    faq = (await session.execute(select(FAQ))).scalar_one()

    item = await settlement_service.review_faq(
        session, faq.id, SimpleNamespace(id=9), FAQReviewRequest(action="reject")
    )

    assert item.status == "rejected"


async def test_review_faq_not_found(settlement_session):
    with pytest.raises(NotFoundError):
        await settlement_service.review_faq(
            settlement_session, 999, SimpleNamespace(id=9), FAQReviewRequest(action="approve")
        )


# ---- FAQ 列表 / 编辑 / 删除 ----
async def test_list_faq_recommendations(settlement_session):
    session = settlement_session
    session.add(FAQ(question="p1", answer="", source_type="auto_mined", status="pending_review"))
    session.add(FAQ(question="pub", answer="a", source_type="manual", status="published"))
    await session.commit()

    result = await settlement_service.list_faq_recommendations(session, page=1, page_size=20)

    assert result.total == 1
    assert result.items[0].question == "p1"
    assert result.items[0].status == "pending_review"


async def test_list_faqs_filter(settlement_session):
    session = settlement_session
    for i in range(3):
        session.add(FAQ(question=f"问题{i}", answer="a", source_type="manual", status="published"))
    session.add(FAQ(question="目标问题", answer="a", source_type="manual", status="published"))
    await session.commit()

    result = await settlement_service.list_faqs(session, keyword="目标", page=1, page_size=20)

    assert result.total == 1
    assert result.items[0].question == "目标问题"


async def test_update_faq(settlement_session):
    session = settlement_session
    session.add(FAQ(question="q", answer="a", source_type="manual", status="published"))
    await session.commit()
    faq = (await session.execute(select(FAQ))).scalar_one()

    item = await settlement_service.update_faq(session, faq.id, FAQUpdate(answer="新答案", category="新类"))

    assert item.answer == "新答案"
    assert item.category == "新类"
    assert item.question == "q"


async def test_delete_faq(settlement_session):
    session = settlement_session
    session.add(FAQ(question="q", answer="a", source_type="manual", status="published"))
    await session.commit()
    faq = (await session.execute(select(FAQ))).scalar_one()

    await settlement_service.delete_faq(session, faq.id)

    assert (await session.execute(select(FAQ))).scalar_one_or_none() is None


# ---- 知识缺口列表 / 补全 / 忽略 ----
async def test_list_knowledge_gaps(settlement_session):
    session = settlement_session
    session.add(
        KnowledgeGap(question_pattern="缺口1", sample_questions_json=["a", "b"], ask_count=2, status="unresolved")
    )
    await session.commit()

    result = await settlement_service.list_knowledge_gaps(session, page=1, page_size=20)

    assert result.total == 1
    assert result.items[0].question_pattern == "缺口1"
    assert result.items[0].sample_questions == ["a", "b"]
    assert result.items[0].ask_count == 2


async def test_resolve_gap(settlement_session):
    session = settlement_session
    session.add(KnowledgeGap(question_pattern="怎么报销？", ask_count=3, status="unresolved"))
    await session.commit()
    gap = (await session.execute(select(KnowledgeGap))).scalar_one()

    payload = KnowledgeGapResolveRequest(title="报销流程", content="报销需要提交单据", category="财务")
    item = await settlement_service.resolve_gap(session, gap.id, SimpleNamespace(id=7), payload)

    assert item.status == "resolved"
    assert item.resolved_unit_id is not None
    unit = await session.get(KnowledgeUnit, item.resolved_unit_id)
    assert unit is not None
    assert unit.title == "报销流程"
    assert unit.status == "draft"
    assert unit.creator_id == 7


async def test_ignore_gap(settlement_session):
    session = settlement_session
    session.add(KnowledgeGap(question_pattern="缺口", status="unresolved"))
    await session.commit()
    gap = (await session.execute(select(KnowledgeGap))).scalar_one()

    await settlement_service.ignore_gap(session, gap.id)

    assert (await session.get(KnowledgeGap, gap.id)).status == "ignored"
