"""pytest 共享夹具：内存 SQLite 会话与知识单元构造助手。

仅创建 P2 涉及的 knowledge_units / unit_permissions 两表（未引入含 JSONB 的
log/settlement 表，以保证 aiosqlite 下可运行）；外键虽指向 users，但 SQLite
默认不启用外键约束，故测试可直写 creator_id / unit_id 等整型列。
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from admin.models.base import Base
from admin.models.knowledge import KnowledgeUnit, UnitPermission

_TABLES = [KnowledgeUnit.__table__, UnitPermission.__table__]


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """每个用例一个独立的内存库，测试间互不影响。"""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=_TABLES)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as s:
        yield s

    await engine.dispose()


@pytest_asyncio.fixture
def make_unit() -> object:
    """返回构造 KnowledgeUnit 的工厂函数（便于用最少字段量产测试数据）。"""

    def _make(
        unit_code: str,
        title: str,
        source_file_name: str,
        *,
        file_type: str = "pdf",
        **kwargs: object,
    ) -> KnowledgeUnit:
        return KnowledgeUnit(
            unit_code=unit_code,
            title=title,
            source_file_name=source_file_name,
            file_type=file_type,
            **kwargs,
        )

    return _make
