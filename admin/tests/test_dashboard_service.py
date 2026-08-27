"""dashboard_service 单元测试。

覆盖：时间桶纯函数（day/week 归桶与连续零填充）、指标聚合、问题/单元榜单、
按日趋势（含 UV、Token 与平均耗时）。所有 DB 用例基于内存 SQLite，不依赖网络与真实 RAG。
"""

from __future__ import annotations

from datetime import datetime

from admin.models.knowledge import KnowledgeUnit
from admin.models.log import QaAccessLog
from admin.services import dashboard_service


# ---- 时间桶纯函数 ----
def test_bucket_key_day():
    assert dashboard_service._bucket_key(datetime(2026, 8, 27, 10, 30), "day") == "2026-08-27"


def test_bucket_key_week():
    # 2026-08-27 为周四，所属周一为 2026-08-24。
    assert dashboard_service._bucket_key(datetime(2026, 8, 27, 10, 30), "week") == "2026-08-24"


def test_bucket_keys_day():
    keys = dashboard_service._bucket_keys(datetime(2026, 8, 25), datetime(2026, 8, 27, 23, 59), "day")
    assert keys == ["2026-08-25", "2026-08-26", "2026-08-27"]


def test_bucket_keys_week():
    keys = dashboard_service._bucket_keys(datetime(2026, 8, 25), datetime(2026, 9, 3), "week")
    assert keys == ["2026-08-24", "2026-08-31"]


def test_build_trends_aggregate_and_zero_fill():
    since = datetime(2026, 8, 25)
    now = datetime(2026, 8, 27, 23, 59)
    rows = [
        (datetime(2026, 8, 25, 9), 1, 100, 200),
        (datetime(2026, 8, 25, 10), 2, 50, 300),
        (datetime(2026, 8, 27, 9), 1, 10, 100),
        (datetime(2026, 8, 24, 9), 9, 999, 1),  # 早于窗口，应被丢弃
    ]

    token_points, access_points = dashboard_service._build_trends(rows, "day", since, now)

    assert [p["bucket"] for p in token_points] == ["2026-08-25", "2026-08-26", "2026-08-27"]
    assert token_points[0]["total_tokens"] == 150
    assert token_points[0]["avg_response_time_ms"] == 250.0
    assert token_points[1]["total_tokens"] == 0
    assert token_points[1]["avg_response_time_ms"] == 0.0
    assert token_points[2]["total_tokens"] == 10

    assert access_points[0]["access_count"] == 2
    assert access_points[0]["uv"] == 2
    assert access_points[1]["access_count"] == 0
    assert access_points[1]["uv"] == 0
    assert access_points[2]["access_count"] == 1
    assert access_points[2]["uv"] == 1


# ---- 指标聚合 ----
async def test_get_metrics(dashboard_session):
    session = dashboard_session
    session.add(KnowledgeUnit(id=1, unit_code="KU-1", title="Guide", source_file_name="guide", file_type="pdf"))
    session.add(QaAccessLog(id=1, session_id="s1", user_id=1, total_tokens=100, response_time_ms=300))
    session.add(QaAccessLog(id=2, session_id="s2", user_id=1, total_tokens=200, response_time_ms=500))
    session.add(QaAccessLog(id=3, session_id="s3", user_id=2, total_tokens=300, response_time_ms=100))
    await session.commit()

    metrics = await dashboard_service.get_metrics(session)

    assert metrics.access_count == 3
    assert metrics.uv == 2
    assert metrics.unit_count == 1
    assert metrics.total_tokens == 600
    assert metrics.avg_response_time_ms == 300.0


async def test_get_metrics_empty(dashboard_session):
    metrics = await dashboard_service.get_metrics(dashboard_session)

    assert metrics.access_count == 0
    assert metrics.uv == 0
    assert metrics.unit_count == 0
    assert metrics.total_tokens == 0
    assert metrics.avg_response_time_ms == 0.0


# ---- 榜单 ----
async def test_get_question_ranking(dashboard_session):
    session = dashboard_session
    session.add(QaAccessLog(id=1, session_id="s1", question="如何登录？"))
    session.add(QaAccessLog(id=2, session_id="s2", question="如何登录？"))
    session.add(QaAccessLog(id=3, session_id="s3", question="如何导出？"))
    await session.commit()

    items = await dashboard_service.get_question_ranking(session, 10)

    assert [(i.question, i.count) for i in items] == [("如何登录？", 2), ("如何导出？", 1)]


async def test_get_unit_ranking(dashboard_session):
    session = dashboard_session
    session.add(KnowledgeUnit(id=1, unit_code="KU-1", title="Guide", source_file_name="guide", file_type="pdf"))
    session.add(KnowledgeUnit(id=2, unit_code="KU-2", title="FAQ", source_file_name="faq", file_type="pdf"))
    session.add(QaAccessLog(id=1, session_id="s1", authorized_unit_ids_json=[1, 2]))
    session.add(QaAccessLog(id=2, session_id="s2", authorized_unit_ids_json=[1]))
    session.add(QaAccessLog(id=3, session_id="s3", authorized_unit_ids_json=None))
    await session.commit()

    items = await dashboard_service.get_unit_ranking(session, 10)

    assert [(i.unit_id, i.count) for i in items] == [(1, 2), (2, 1)]
    assert items[0].title == "Guide"
    assert items[0].source_file_name == "guide"


# ---- 趋势（按日） ----
async def test_get_token_stats(dashboard_session, monkeypatch):
    session = dashboard_session
    since = datetime(2026, 8, 25)
    now = datetime(2026, 8, 27, 23, 59)
    monkeypatch.setattr(dashboard_service, "_window", lambda days: (since, now))

    session.add(
        QaAccessLog(id=1, session_id="s1", created_at=datetime(2026, 8, 25, 9), total_tokens=100, response_time_ms=200)
    )
    session.add(
        QaAccessLog(id=2, session_id="s2", created_at=datetime(2026, 8, 25, 10), total_tokens=50, response_time_ms=300)
    )
    session.add(
        QaAccessLog(id=3, session_id="s3", created_at=datetime(2026, 8, 24, 9), total_tokens=999, response_time_ms=1)
    )
    await session.commit()

    items = await dashboard_service.get_token_stats(session, "day", 3)

    assert [p.bucket for p in items] == ["2026-08-25", "2026-08-26", "2026-08-27"]
    assert items[0].total_tokens == 150
    assert items[0].avg_response_time_ms == 250.0
    assert items[1].total_tokens == 0
    assert items[2].total_tokens == 0


async def test_get_access_stats(dashboard_session, monkeypatch):
    session = dashboard_session
    since = datetime(2026, 8, 25)
    now = datetime(2026, 8, 27, 23, 59)
    monkeypatch.setattr(dashboard_service, "_window", lambda days: (since, now))

    session.add(QaAccessLog(id=1, session_id="s1", user_id=1, created_at=datetime(2026, 8, 26, 9)))
    session.add(QaAccessLog(id=2, session_id="s2", user_id=2, created_at=datetime(2026, 8, 26, 10)))
    session.add(QaAccessLog(id=3, session_id="s3", user_id=1, created_at=datetime(2026, 8, 27, 9)))
    await session.commit()

    items = await dashboard_service.get_access_stats(session, "day", 3)

    assert [p.bucket for p in items] == ["2026-08-25", "2026-08-26", "2026-08-27"]
    assert items[0].access_count == 0
    assert items[0].uv == 0
    assert items[1].access_count == 2
    assert items[1].uv == 2
    assert items[2].access_count == 1
    assert items[2].uv == 1
