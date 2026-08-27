"""知识沉淀路由：FAQ 挖掘/审核/缓存与知识缺口。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from admin.core.deps import CurrentUser, require_permissions
from admin.core.response import ok
from admin.database import get_db
from admin.schemas.settlement import FAQReviewRequest, FAQUpdate, KnowledgeGapResolveRequest
from admin.services import settlement_service

router = APIRouter(prefix="/settlement", tags=["settlement"])


@router.post("/mine")
async def run_mine(
    _: CurrentUser = Depends(require_permissions("menu:settlement:faq", "menu:settlement:gap")),
    session: AsyncSession = Depends(get_db),
):
    """手动触发沉淀挖掘（FAQ 挖掘 + 知识缺口识别）。"""
    result = await settlement_service.mine_knowledge(session)
    return ok(result)


@router.get("/faqs/recommendations")
async def faq_recommendations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: CurrentUser = Depends(require_permissions("menu:settlement:faq")),
    session: AsyncSession = Depends(get_db),
):
    """待审核 FAQ 推荐列表。"""
    data = await settlement_service.list_faq_recommendations(session, page=page, page_size=page_size)
    return ok(data.model_dump())


@router.post("/faqs/{faq_id}/review")
async def review_faq(
    faq_id: int,
    payload: FAQReviewRequest,
    current_user: CurrentUser = Depends(require_permissions("op:settlement:faq:review")),
    session: AsyncSession = Depends(get_db),
):
    """审核 FAQ：approve 发布（可覆盖标准答案）/ reject 驳回。"""
    data = await settlement_service.review_faq(session, faq_id, current_user, payload)
    return ok(data.model_dump())


@router.get("/faqs")
async def list_faqs(
    status: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: CurrentUser = Depends(require_permissions("menu:settlement:faq")),
    session: AsyncSession = Depends(get_db),
):
    """FAQ 列表（默认全部，可按状态筛选发布态）。"""
    data = await settlement_service.list_faqs(session, status=status, keyword=keyword, page=page, page_size=page_size)
    return ok(data.model_dump())


@router.put("/faqs/{faq_id}")
async def update_faq(
    faq_id: int,
    payload: FAQUpdate,
    _: CurrentUser = Depends(require_permissions("menu:settlement:faq")),
    session: AsyncSession = Depends(get_db),
):
    """编辑 FAQ。"""
    data = await settlement_service.update_faq(session, faq_id, payload)
    return ok(data.model_dump())


@router.delete("/faqs/{faq_id}")
async def delete_faq(
    faq_id: int,
    _: CurrentUser = Depends(require_permissions("menu:settlement:faq")),
    session: AsyncSession = Depends(get_db),
):
    """删除 FAQ。"""
    await settlement_service.delete_faq(session, faq_id)
    return ok(None)


@router.get("/knowledge-gaps")
async def list_knowledge_gaps(
    status: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: CurrentUser = Depends(require_permissions("menu:settlement:gap")),
    session: AsyncSession = Depends(get_db),
):
    """知识缺口列表。"""
    data = await settlement_service.list_knowledge_gaps(
        session, status=status, keyword=keyword, page=page, page_size=page_size
    )
    return ok(data.model_dump())


@router.post("/knowledge-gaps/{gap_id}/resolve")
async def resolve_gap(
    gap_id: int,
    payload: KnowledgeGapResolveRequest,
    current_user: CurrentUser = Depends(require_permissions("menu:settlement:gap")),
    session: AsyncSession = Depends(get_db),
):
    """一键创建知识单元补全缺口。"""
    data = await settlement_service.resolve_gap(session, gap_id, current_user, payload)
    return ok(data.model_dump())


@router.patch("/knowledge-gaps/{gap_id}/ignore")
async def ignore_gap(
    gap_id: int,
    _: CurrentUser = Depends(require_permissions("menu:settlement:gap")),
    session: AsyncSession = Depends(get_db),
):
    """忽略知识缺口。"""
    await settlement_service.ignore_gap(session, gap_id)
    return ok(None)
