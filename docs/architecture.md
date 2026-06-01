# Architecture

- Backend: FastAPI + SQLModel + SQLite, deterministic rule services, local filesystem storage.
- Frontend: Vite + React + TypeScript + Tailwind CSS tokens + Recharts.
- PHI boundary: external services default off; tests monkeypatch sockets to prove extraction, predictions, and alerts do not attempt egress.
- Clinical rules: deterministic, source-driven from Thomas's discharge/AVS text with source snippets.
- A5 recommendations: one shared backend schema and frontend component.
