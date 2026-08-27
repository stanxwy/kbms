"""组织架构相关 Pydantic 模型：部门、用户、角色与权限。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from admin.schemas.common import PageResult


# ---- 角色 ----
class RoleBrief(BaseModel):
    """角色简要信息（列表/嵌套展示用）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    role_name: str
    role_code: str


class RoleCreate(BaseModel):
    role_name: str = Field(..., min_length=1, max_length=64)
    role_code: str = Field(..., min_length=1, max_length=64)
    description: str | None = Field(None, max_length=255)


class RoleUpdate(BaseModel):
    role_name: str | None = Field(None, min_length=1, max_length=64)
    description: str | None = Field(None, max_length=255)


class RoleOut(BaseModel):
    """角色详情输出。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    role_name: str
    role_code: str
    description: str | None = None


# ---- 角色-操作权限 ----
class PermissionItem(BaseModel):
    permission_code: str = Field(..., min_length=1, max_length=64)
    permission_type: str = Field(..., min_length=1, max_length=16)


class RolePermissionsUpdate(BaseModel):
    """角色权限全量覆盖请求。"""

    permissions: list[PermissionItem] = Field(default_factory=list)


# ---- 部门 ----
class DepartmentCreate(BaseModel):
    parent_id: int | None = None
    name: str = Field(..., min_length=1, max_length=128)
    leader_id: int | None = None
    sort_order: int = 0


class DepartmentUpdate(BaseModel):
    parent_id: int | None = None
    name: str | None = Field(None, min_length=1, max_length=128)
    leader_id: int | None = None
    sort_order: int | None = None


class DepartmentOut(BaseModel):
    """部门节点输出。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: int | None = None
    name: str
    leader_id: int | None = None
    sort_order: int = 0


class DepartmentTreeNode(DepartmentOut):
    """部门树节点（递归携带 children）。"""

    children: list[DepartmentTreeNode] = Field(default_factory=list)


# ---- 用户 ----
class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str | None = Field(None, max_length=128)
    department_id: int | None = None
    role_ids: list[int] = Field(default_factory=list)
    status: int = Field(1, ge=0, le=1)


class UserUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=128)
    department_id: int | None = None
    role_ids: list[int] | None = None


class UserOut(BaseModel):
    """用户列表/详情输出（含部门名与角色）。"""

    id: int
    username: str
    display_name: str | None = None
    department_id: int | None = None
    department_name: str | None = None
    status: int
    roles: list[RoleBrief] = Field(default_factory=list)


class ResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=6, max_length=128)


class UserStatusUpdate(BaseModel):
    status: int = Field(..., ge=0, le=1)


class UserListResult(PageResult[UserOut]):
    """用户分页响应。"""
