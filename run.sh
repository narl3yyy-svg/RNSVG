#!/usr/bin/env bash
# RNSVG — run from source (Arch / Ubuntu / macOS)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required (>= 3.11)" >&2
  exit 1
fi

if ! command -v pnpm >/dev/null 2>&1; then
  echo "Error: pnpm is required. Install Node.js 24+ and: corepack enable && corepack prepare pnpm@11.1.2 --activate" >&2
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install -q -U pip
pip install -q -r requirements.txt
pip install -q -e .

if [ ! -f "meshchatx/public/index.html" ]; then
  echo "Building frontend (first run)..."
  if [ ! -d "node_modules" ]; then
    corepack enable 2>/dev/null || true
    pnpm install --frozen-lockfile
  fi
  pnpm run build-frontend
fi

echo ""
echo "Starting RNSVG..."
exec python -m rnsvg --headless --host 127.0.0.1 --port 8787 "$@"