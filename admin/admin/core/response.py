"""统一响应封装：`{code, message, data}` 结构与快速构造助手。"""
from typing import Any

from fastapi.responses import JSONResponse


def ok(data: Any = None, message: str = "success") -> dict[str, Any]:
    """构造成功响应体。"""
    return {"code": 200, "message": message, "data": data}


def error_response(status_code: int, code: int, message: str) -> JSONResponse:
    """构造错误响应（data 恒为 None）。"""
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": message, "data": None},
    )