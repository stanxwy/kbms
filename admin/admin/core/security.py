"""鉴权与安全：JWT 签发/校验、密码散列。

密码散列采用 bcrypt、JWT 采用 python-jose（依赖已在 pyproject.toml 声明）。
"""
from __future__ import annotations

import time

import bcrypt
from jose import JWTError, jwt

from admin.config import get_settings
from admin.core.exceptions import UnauthorizedError


def hash_password(plain: str) -> str:
    """对明文密码做 bcrypt 散列，返回可直接落库的字符串。"""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与散列是否匹配（常量时间比较）。"""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _encode(subject: str, token_type: str, ttl_seconds: int) -> str:
    """签发 JWT：sub 为用户 id 字符串、type 区分 access/refresh。"""
    settings = get_settings()
    now = int(time.time())
    payload = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int) -> str:
    """签发 access token（短时效，随请求携带）。"""
    settings = get_settings()
    return _encode(str(user_id), "access", settings.JWT_ACCESS_TTL_MIN * 60)


def create_refresh_token(user_id: int) -> str:
    """签发 refresh token（长时效，用于换取新 access token）。"""
    settings = get_settings()
    return _encode(str(user_id), "refresh", settings.JWT_REFRESH_TTL_DAY * 24 * 3600)


def decode_token(token: str, expected_type: str) -> dict:
    """校验并解包 JWT，返回 payload；类型不符或无效/过期则拒绝。"""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise UnauthorizedError("token 无效或已过期") from exc
    if payload.get("type") != expected_type:
        raise UnauthorizedError("token 类型错误")
    return payload
