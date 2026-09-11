#!/usr/bin/env bash
# Vision 5D — Local startup (API + durable worker)
set -euo pipefail

# Resolve project root dynamically (works regardless of caller CWD)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Load .env (AI/provider keys) into the environment so BOTH the API and the
# worker see them. The API also self-loads .env; this covers the worker.
set -a
# shellcheck disable=SC1091
source .env 2>/dev/null || true
set +a

# Shared database/config assumptions (must match start_vision5d_local.bat).
# `pwd -W` yields the Windows-native path (C:/...) — the MSYS $PWD (/c/...)
# is NOT openable by the native sqlite3 driver.
export V5D_AUTO_CREATE_TABLES=true
export V5D_DATABASE_URL="${V5D_DATABASE_URL:-sqlite:///$(pwd -W)/vision5d.db}"

PYTHON="${V5D_PYTHON:-C:/Users/admin/AppData/Local/Programs/Python/Python311/python.exe}"

echo "Vision 5D — starting API (:8000) + durable worker"
echo "  Database:  $V5D_DATABASE_URL"
echo "  Dashboard: http://localhost:8000/apps/web/index.html"

"$PYTHON" -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
"$PYTHON" apps/worker/main.py &
WORKER_PID=$!

cleanup() {
    echo "Stopping Vision 5D (API + worker)..."
    kill "$API_PID" "$WORKER_PID" 2>/dev/null || true
    wait "$API_PID" "$WORKER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait
