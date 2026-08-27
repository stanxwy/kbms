"""数据看板服务：聚合指标、榜单归约与时间桶趋势格式化。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from admin.repositories import dashboard_repository, knowledge_repository
from admin.schemas.dashboard import (
    AccessTrendPoint,
    DashboardMetrics,
    QuestionRankItem,
    TokenTrendPoint,
    UnitRankItem,
)


def _window(days: int) -> tuple[datetime, datetime]:
    """计算统计窗口：``(since, now)``，均取 UTC 感知时间。"""
    now = datetime.now(UTC)
    return now - timedelta(days=days), now


def _bucket_key(created_at: datetime, granularity: str) -> str:
    """将单条事实的 created_at 归到时间桶键：日 → ``YYYY-MM-DD``，周 → 所属周一日期。"""
    day = created_at.date()
    if granularity == "week":
        day = day - timedelta(days=day.weekday())
    return day.isoformat()


def _bucket_keys(since: datetime, now: datetime, granularity: str) -> list[str]:
    """生成 ``since`` 到 ``now`` 的连续空桶序列（用于趋势零填充，保证前端曲线连续）。"""
    if granularity == "week":
        cursor = since.date() - timedelta(days=since.date().weekday())
        step = timedelta(days=7)
    else:
        cursor = since.date()
        step = timedelta(days=1)

    keys: list[str] = []
    while cursor <= now.date():
        keys.append(cursor.isoformat())
        cursor += step
    return keys


def _build_trends(
    rows: list[tuple[datetime, int | None, int, int]],
    granularity: str,
    since: datetime,
    now: datetime,
) -> tuple[list[dict], list[dict]]:
    """将原始时序行归约为 (token 趋势点, 访问趋势点)，含连续桶零填充。

    入参 ``rows`` 元素为 ``(created_at, user_id, total_tokens, response_time_ms)``；
    超出窗口范围（早于 since 或晚于 now）的行会被丢弃。
    """
    bucket_keys = _bucket_keys(since, now, granularity)
    token_acc = {b: {"tokens": 0, "resp_sum": 0, "resp_count": 0} for b in bucket_keys}
    access_acc = {b: {"count": 0, "users": set()} for b in bucket_keys}

    for created_at, user_id, total_tokens, response_time_ms in rows:
        key = _bucket_key(created_at, granularity)
        if key not in token_acc:
            continue
        bucket = token_acc[key]
        bucket["tokens"] += total_tokens or 0
        bucket["resp_sum"] += response_time_ms or 0
        bucket["resp_count"] += 1

        access = access_acc[key]
        access["count"] += 1
        if user_id is not None:
            access["users"].add(user_id)

    token_points: list[dict] = []
    access_points: list[dict] = []
    for bucket in bucket_keys:
        t = token_acc[bucket]
        avg_resp = round(t["resp_sum"] / t["resp_count"], 1) if t["resp_count"] else 0.0
        token_points.append({"bucket": bucket, "total_tokens": t["tokens"], "avg_response_time_ms": avg_resp})
        access_points.append(
            {"bucket": bucket, "access_count": access_acc[bucket]["count"], "uv": len(access_acc[bucket]["users"])}
        )
    return token_points, access_points


async def get_metrics(session: AsyncSession) -> DashboardMetrics:
    """核心运营指标。"""
    data = await dashboard_repository.get_metrics(session)
    data["avg_response_time_ms"] = round(data["avg_response_time_ms"], 1)
    return DashboardMetrics(**data)


async def get_question_ranking(session: AsyncSession, limit: int) -> list[QuestionRankItem]:
    """高频问题 TOP 榜。"""
    rows = await dashboard_repository.get_question_ranking(session, limit)
    return [QuestionRankItem(question=question, count=count) for question, count in rows]


async def get_unit_ranking(session: AsyncSession, limit: int) -> list[UnitRankItem]:
    """最常访问知识单元 TOP 榜（归约 authorized_unit_ids_json 频次后回填元数据）。"""
    counter: dict[int, int] = {}
    for unit_ids in await dashboard_repository.get_authorized_unit_ids(session):
        for unit_id in unit_ids:
            counter[unit_id] = counter.get(unit_id, 0) + 1

    top = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    if not top:
        return []

    units = {u.id: u for u in await knowledge_repository.get_units_by_ids(session, [uid for uid, _ in top])}
    return [
        UnitRankItem(
            unit_id=unit_id,
            title=units[unit_id].title if unit_id in units else None,
            source_file_name=units[unit_id].source_file_name if unit_id in units else None,
            count=count,
        )
        for unit_id, count in top
    ]


async def get_token_stats(session: AsyncSession, granularity: str, days: int) -> list[TokenTrendPoint]:
    """Token 消耗与响应时间趋势（按日/周）。"""
    since, now = _window(days)
    rows = await dashboard_repository.fetch_access_series(session, since)
    token_points, _ = _build_trends(rows, granularity, since, now)
    return [TokenTrendPoint(**point) for point in token_points]


async def get_access_stats(session: AsyncSession, granularity: str, days: int) -> list[AccessTrendPoint]:
    """访问趋势（按日/周）。"""
    since, now = _window(days)
    rows = await dashboard_repository.fetch_access_series(session, since)
    _, access_points = _build_trends(rows, granularity, since, now)
    return [AccessTrendPoint(**point) for point in access_points]
