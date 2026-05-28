# DONE.md — Changelog

## Web UI Integration

- [2026-05-28] refactor(analyze): remove path option, paste/upload only (files modified: api/routes/analyze.py, api/routes/config.py, api/schemas.py, web/src/lib/api.ts, web/src/pages/Analyze.tsx)
  - Remove filesystem path access from analyze endpoint (security improvement)
  - Analyze page now has 2 tabs: Paste JSON and Upload File
  - Backend accepts config_content only, no config_path
  - Upload returns raw content instead of temp file path
  - Simplified API client and schemas

- [2026-05-28] feat: add FastAPI backend and React web UI for DevKit (files modified: api/, web/, pyproject.toml, .gitignore)
  - FastAPI app with CORS, static file serving, 7 route groups (analyze, audit, score, history, migrate, config, recommendations)
  - React + Vite + TypeScript + Tailwind + shadcn/ui frontend with 7 pages
  - CodeMirror JSON editor, Recharts visualizations, React Query data fetching
  - Dark mode with toggle, responsive layout, Vite proxy to FastAPI in dev mode
