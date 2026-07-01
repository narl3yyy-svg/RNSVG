@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo Error: Python 3.11+ is required.
  exit /b 1
)

where pnpm >nul 2>&1
if errorlevel 1 (
  echo Error: pnpm is required. Install Node.js 24+ and enable corepack.
  exit /b 1
)

if not exist ".venv" (
  echo Creating Python virtual environment...
  python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install -q -U pip
pip install -q -r requirements.txt
pip install -q -e .

if not exist "meshchatx\public\index.html" (
  echo Building frontend ^(first run^)...
  if not exist "node_modules" (
    call pnpm install --frozen-lockfile
  )
  call pnpm run build-frontend
)

echo.
echo Starting RNSVG...
python -m rnsvg --headless --host 127.0.0.1 --port 8787 %*