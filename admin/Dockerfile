# syntax=docker/dockerfile:1

# KBMS admin 后端镜像：轻量 FastAPI 进程，不含 RAG 重型模型。
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10

WORKDIR /app

# 安装 uv（沿用 app/ 服务的包管理方式）。
RUN pip install --no-cache-dir --upgrade pip uv

# 先只拷贝依赖清单，利用缓存层；uv 解析并安装第三方依赖（不安装项目本身）。
COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project

# 激活 uv 管理的虚拟环境。
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# 拷贝源码：admin 包 + alembic 迁移 + 种子脚本。
COPY admin/ /app/admin/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/alembic.ini
COPY scripts/ /app/scripts/

# 运行时目录：日志、静态资源（前端构建产物挂载点）。
RUN mkdir -p /app/logs /app/admin/static/dist

EXPOSE 8002

CMD ["uvicorn", "admin.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "1"]