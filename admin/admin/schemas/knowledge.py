"""知识维护相关 Pydantic 模型：导入、知识单元与数据权限配置。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from admin.schemas.common import PageResult


class UnitPermissionItem(BaseModel):
    """数据权限实体（global=0；department/role/user=对应实体 ID）。"""

    target_type: str = Field(..., pattern="^(global|department|role|user)$")
    target_id: int = Field(0, ge=0)


class UnitPermissionsUpdate(BaseModel):
    """数据权限全量覆盖请求。"""

    permissions: list[UnitPermissionItem] = Field(default_factory=list)


class KnowledgeUnitUpdate(BaseModel):
    """知识单元编辑请求（仅更新提供的字段）。"""

    title: str | None = Field(None, min_length=1, max_length=255)
    content: str | None = None
    summary: str | None = None
    category: str | None = Field(None, max_length=128)
    status: str | None = Field(None, pattern="^(draft|published|archived)$")


class KnowledgeUnitOut(BaseModel):
    """知识单元列表/详情输出。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_code: str
    title: str
    content: str | None = None
    summary: str | None = None
    category: str | None = None
    source_file_name: str
    file_type: str
    file_size: int
    status: str
    creator_id: int | None = None


class KnowledgeUnitDetail(KnowledgeUnitOut):
    """知识单元详情（含已配置数据权限）。"""

    permissions: list[UnitPermissionItem] = Field(default_factory=list)


class BatchDeleteRequest(BaseModel):
    """批量删除请求。"""

    ids: list[int] = Field(..., min_length=1)


class ImportResult(BaseModel):
    """导入响应。"""

    task_ids: list[str] = Field(default_factory=list)


class KnowledgeUnitListResult(PageResult[KnowledgeUnitOut]):
    """知识单元分页响应。"""
