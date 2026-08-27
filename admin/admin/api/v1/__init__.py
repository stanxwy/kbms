"""API v1 路由集合（挂载于 /api 前缀）。"""

from fastapi import APIRouter

from admin.api.v1.auth import router as auth_router
from admin.api.v1.health import router as health_router
from admin.api.v1.knowledge import router as knowledge_router
from admin.api.v1.org import router as org_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(org_router)
api_router.include_router(knowledge_router)
api_router.include_router(health_router)

__all__ = ["api_router"]
