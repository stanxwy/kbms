"""通用 Pydantic 模型：分页参数与分页响应。"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageParams(BaseModel):
    """列表类接口通用分页查询参数。"""

    page: int = Field(1, ge=1, description="页码（从 1 开始）")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


class PageResult(BaseModel, Generic[T]):
    """列表类接口统一分页响应。"""

    items: list[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
