@echo off
setlocal
REM KBMS admin-frontend one-click start: install deps (if missing) + Vite dev(:5173)
REM Prereq: admin backend running (:8002); open http://localhost:5173 default account admin / admin123
cd /d "%~dp0"

if not exist node_modules (
  echo [run] first start, installing dependencies: pnpm install
  call pnpm install
  if errorlevel 1 (
    echo [error] dependency install failed
    pause
    exit /b 1
  )
)

echo [run] starting frontend dev server at http://localhost:5173
REM Vite proxies /api to http://127.0.0.1:8002
call pnpm dev

pause
endlocal