#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
trap 'jobs -p | xargs -r kill' EXIT
./.venv/bin/uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8008 &
(cd apps/web && npm run dev) &
wait
