@echo off
setlocal
REM KBMS Admin backend one-click start: migrate + idempotent seed + Uvicorn(:8002)
REM Prereq: PostgreSQL (kbms-postgres:5432) running; RAG(:8000) optional (needed for knowledge import / AI chat)
cd /d "%~dp0"

if not exist .env (
  echo [run] .env not found, copying from .env.example
  copy .env.example .env >nul
)

echo [run] running database migration: alembic upgrade head
uv run alembic upgrade head
if errorlevel 1 (
  echo [error] database migration failed, check PostgreSQL is running
  pause
  exit /b 1
)

echo [run] running idempotent seed: init_seed.py
uv run python scripts/init_seed.py
if errorlevel 1 (
  echo [error] seed data initialization failed
  pause
  exit /b 1
)

echo [run] starting admin backend at http://localhost:8002
REM Standard port 8002. If bind fails with WinError 10013 on this host (Windows excluded
REM port range), run via docker-compose or free the range with netsh instead of changing the port.
uv run uvicorn admin.main:app --host 0.0.0.0 --port 8002 --reload

pause
endlocal