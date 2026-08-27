"""数据看板路由：指标、榜单与趋势查询。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from admin.core.deps import CurrentUser, require_permissions
from admin.core.response import ok
from admin.database import get_db
from admin.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/metrics")
async def get_metrics(
    _: CurrentUser = Depends(require_permissions("menu:dashboard")),
    session: AsyncSession = Depends(get_db),
):
    data = await dashboard_service.get_metrics(session)
    return ok(data.model_dump())


@router.get("/rankings/questions")
async def get_question_ranking(
    limit: int = Query(10, ge=1, le=50),
    _: CurrentUser = Depends(require_permissions("menu:dashboard")),
    session: AsyncSession = Depends(get_db),
):
    items = await dashboard_service.get_question_ranking(session, limit)
    return ok([item.model_dump() for item in items])


@router.get("/rankings/units")
async def get_unit_ranking(
    limit: int = Query(10, ge=1, le=50),
    _: CurrentUser = Depends(require_permissions("menu:dashboard")),
    session: AsyncSession = Depends(get_db),
):
    items = await dashboard_service.get_unit_ranking(session, limit)
    return ok([item.model_dump() for item in items])


@router.get("/stats/tokens")
async def get_token_stats(
    granularity: str = Query("day", pattern="^(day|week)$"),
    days: int = Query(30, ge=1, le=366),
    _: CurrentUser = Depends(require_permissions("menu:dashboard")),
    session: AsyncSession = Depends(get_db),
):
    items = await dashboard_service.get_token_stats(session, granularity, days)
    return ok([item.model_dump() for item in items])


@router.get("/stats/access")
async def get_access_stats(
    granularity: str = Query("day", pattern="^(day|week)$"),
    days: int = Query(30, ge=1, le=366),
    _: CurrentUser = Depends(require_permissions("menu:dashboard")),
    session: AsyncSession = Depends(get_db),
):
    items = await dashboard_service.get_access_stats(session, granularity, days)
    return ok([item.model_dump() for item in items])
