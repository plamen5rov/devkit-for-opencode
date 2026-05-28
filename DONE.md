# DONE.md — Changelog

## Web UI Integration

- [2026-05-28] feat: add FastAPI backend and React web UI for DevKit (files modified: api/, web/, pyproject.toml, .gitignore)
  - FastAPI app with CORS, static file serving, 7 route groups (analyze, audit, score, history, migrate, config, recommendations)
  - React + Vite + TypeScript + Tailwind + shadcn/ui frontend with 7 pages
  - CodeMirror JSON editor, Recharts visualizations, React Query data fetching
  - Dark mode with toggle, responsive layout, Vite proxy to FastAPI in dev mode
