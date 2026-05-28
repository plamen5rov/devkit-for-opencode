# DONE.md — Changelog

## Fixes & Improvements

- [2026-05-28] fix: persist analysis history and analyze state, add start script (files modified: api/routes/analyze.py, api/routes/history.py, web/src/pages/Analyze.tsx, Makefile, start.sh)
  - Save analysis results to SQLite history DB after each analyze run (fixes Dashboard "No analysis data")
  - Fix route ordering: /trend before /{record_id} to prevent FastAPI 422 on Dashboard requests
  - Persist Analyze page state via sessionStorage (configText, activeTab, result) — survives tab switches
  - Move Issues/Warnings/Fix-Generate sections to bottom of page
  - Add start.sh and Makefile: `make start` or `./start.sh` launches API + Vite in one terminal
  - Makefile also has format, lint, test targets
  - 288 tests passing

## Core Refactoring

- [2026-05-28] refactor: remove unused CrewAI dependency and dead code (files modified: pyproject.toml, devkit/agents/*, devkit/tasks/full_audit.py, README.md, AGENTS.md, ARCHITECTURE.md, tests/*)
  - Remove crewai and crewai-tools from dependencies
  - Strip CrewAI imports from all agent wrappers (orchestrator, auditor, advisor, multi_agent)
  - Remove create_crew_audit from full_audit.py (was never called)
  - Update all documentation to remove CrewAI references
  - Remove tests for deleted CrewAI agent/task creation functions
  - All analysis is purely programmatic — no LLM calls required
  - 288 tests passing

## Web UI Integration

- [2026-05-28] style(analyze): color-code Analysis Details cards (files modified: web/src/pages/Analyze.tsx)
  - Permissions: blue, Agents: violet, Skills: emerald, MCP Servers: amber, Commands: cyan
  - Each card has matching colored border, subtle tinted background, and colored dot icon

- [2026-05-28] feat(analyze): colored issue/warning cards with checkboxes and fix generation (files modified: web/src/pages/Analyze.tsx, web/src/components/ui/checkbox.tsx, web/package.json)
  - Red-tinted cards for Issues, yellow-tinted for Warnings with colored borders
  - Checkbox next to each fixable issue for selective fixing
  - Fix All / Deselect All toggle button
  - Generate Fixed Config button outputs corrected JSON in CodeMirror editor
  - Copy button with visual feedback for quick clipboard paste
  - Detects 8 fix types: catch-all, bash, edit, small_model, schema, share, model prefix, disabled MCP servers

- [2026-05-28] fix(analyze): show issues/warnings details, replace raw JSON with structured cards (files modified: web/src/pages/Analyze.tsx)
  - Add Issues section displaying orchestrator.issues with full descriptions
  - Add Warnings section displaying orchestrator.warnings with full descriptions
  - Rename Findings to Audit Findings, show message + suggestion columns
  - Add Recommendations table with priority badges
  - Replace raw JSON blob with structured analysis detail cards (permissions, agents, skills, MCP, commands)
  - No config content leaked — only summary metrics shown

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
