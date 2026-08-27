"""KBMS admin 后端入口：装配 FastAPI 应用、中间件、日志与路由。"""

import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from admin.api.v1 import api_router
from admin.config import get_settings
from admin.core.exceptions import AppError
from admin.core.response import error_response

settings = get_settings()

# ---- 日志（loguru：控制台 + 滚动文件） ----
_LOG_DIR = Path("logs")
_LOG_DIR.mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stderr, level=settings.LOG_LEVEL, enqueue=True)
logger.add(
    _LOG_DIR / "kbms_admin.log",
    level=settings.LOG_LEVEL,
    rotation="1 day",
    retention="30 days",
    encoding="utf-8",
    enqueue=True,
)

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_PREFIX)


# ---- 全局异常处理：统一为 {code, message, data} ----
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(422, 422, "validation error")


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.opt(exception=exc).error("unhandled error on {}", request.url.path)
    return error_response(500, 500, "internal server error")
