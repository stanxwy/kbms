"""认证相关 Pydantic 模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from admin.schemas.org import RoleBrief


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class UserInfo(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    department_id: int | None = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    user_info: UserInfo
    permissions: list[str]


class RefreshResponse(BaseModel):
    access_token: str


class MeResponse(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    department_id: int | None = None
    department_name: str | None = None
    roles: list[RoleBrief] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
