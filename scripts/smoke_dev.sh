#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
LOG_DIR="$ROOT/reports/smoke"
mkdir -p "$LOG_DIR"
./.venv/bin/uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8008 >"$LOG_DIR/api.log" 2>&1 &
API_PID=$!
(cd apps/web && npm run dev -- --host 127.0.0.1 --port 5173 >"$LOG_DIR/web.log" 2>&1) &
WEB_PID=$!
cleanup() { kill "$API_PID" "$WEB_PID" >/dev/null 2>&1 || true; }
trap cleanup EXIT
for _ in {1..60}; do
  if curl -fsS http://127.0.0.1:8008/api/health >/dev/null 2>&1 && curl -fsS http://127.0.0.1:5173 >/dev/null 2>&1; then
    echo "make dev smoke passed: FastAPI 8008 and Vite 5173 reachable"
    exit 0
  fi
  sleep 1
done
echo "make dev smoke failed" >&2
exit 1
