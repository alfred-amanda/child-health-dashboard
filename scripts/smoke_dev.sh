#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
LOG_DIR="$ROOT/reports/smoke"
mkdir -p "$LOG_DIR"

# Guard: the dev server must never be pre-bundled in production mode, or React's
# jsx-dev-runtime resolves to the production stub (jsxDEV = undefined) and the
# whole app renders blank. See ALF-289.
if [[ "${NODE_ENV:-}" == "production" ]]; then
  echo "refusing to run dev smoke with NODE_ENV=production (would poison the JSX dev runtime)" >&2
  exit 1
fi

./.venv/bin/uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8008 >"$LOG_DIR/api.log" 2>&1 &
API_PID=$!
(cd apps/web && npm run dev >"$LOG_DIR/web.log" 2>&1) &
WEB_PID=$!
cleanup() { kill "$API_PID" "$WEB_PID" >/dev/null 2>&1 || true; }
trap cleanup EXIT

up=""
for _ in {1..60}; do
  if curl -fsS http://127.0.0.1:8008/api/health >/dev/null 2>&1 && curl -fsS http://127.0.0.1:5173 >/dev/null 2>&1; then
    up=1
    break
  fi
  sleep 1
done
if [[ -z "$up" ]]; then
  echo "make dev smoke failed: FastAPI 8008 or Vite 5173 not reachable" >&2
  exit 1
fi

# Force Vite to pre-bundle the entry graph, then verify the dev JSX runtime is the
# development build (a real jsxDEV), not the production stub that blanks the page.
curl -fsS http://127.0.0.1:5173/src/main.tsx >/dev/null 2>&1 || true
sleep 2
DEP="apps/web/node_modules/.vite/deps/react_jsx-dev-runtime.js"
if [[ -f "$DEP" ]] && grep -qE 'jsxDEV[[:space:]]*[:=][[:space:]]*void 0' "$DEP"; then
  echo "make dev smoke failed: dev JSX runtime is the production stub (jsxDEV undefined); blank-page regression" >&2
  exit 1
fi

echo "make dev smoke passed: FastAPI 8008 + Vite 5173 reachable and dev JSX runtime is live"
exit 0
