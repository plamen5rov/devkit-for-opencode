#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="/tmp/devkit-servers.pid"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

cleanup() {
    echo ""
    echo "Shutting down..."
    if [ -f "$PID_FILE" ]; then
        while read -r pid; do
            kill "$pid" 2>/dev/null
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

echo "=== Starting DevKit servers ==="

# API server
echo "[api] Starting on http://localhost:8000"
cd "$PROJECT_ROOT"
"$VENV_PYTHON" -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!
echo "$API_PID" >> "$PID_FILE"

# Vite dev server
echo "[web] Starting on http://localhost:5173"
cd "$PROJECT_ROOT/web"
npx vite --host &
WEB_PID=$!
echo "$WEB_PID" >> "$PID_FILE"

cd "$PROJECT_ROOT"
echo ""
echo "Ready. API: http://localhost:8000 | Web: http://localhost:5173"
echo "Press Ctrl+C to stop both servers."
echo ""

wait
