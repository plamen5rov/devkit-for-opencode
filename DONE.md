# DONE.md — Changelog

## Fixes & Improvements

- [2026-05-31] fix: skills and commands analysis now derived from config content when no filesystem access — no server-side scanning (files modified: devkit/tools/skill_analyzer.py, devkit/tools/command_analyzer.py, devkit/agents/orchestrator.py, devkit/tasks/full_audit.py, devkit/cli.py, tests/test_skill_analyzer.py, tests/test_command_analyzer.py, README.md, DONE.md)
  - `discover_skills` / `discover_commands` no longer fall back to `Path.cwd()` when `project_root` is `None` — global paths also skipped
  - `analyze_skills` extracts skill names from `config["permission"]["skill"]` when no filesystem skills found
  - `analyze_commands` extracts commands from `config["command"]` when no filesystem commands found (new `config` param)
  - CLI now derives `project_root` from config path to preserve filesystem scanning for local users
  - 9 new tests (372 total)

- [2026-05-29] feat: add Dependency Graph Visualization — interactive force-directed graph of config relationships (files modified: devkit/tools/graph_builder.py (new), api/routes/graph.py (new), api/schemas.py, api/main.py, devkit/cli.py, web/src/pages/Graph.tsx (new), web/src/lib/api.ts, web/src/App.tsx, web/src/components/Layout.tsx, tests/test_graph_builder.py (new), README.md, DONE.md, web/package.json (vis-network dep))
  - `devkit/tools/graph_builder.py` — extracts nodes (config, model, agent, mcp, plugin, permission, instruction) and edges (uses_model, has_permission, connects_to, loads_plugin, includes, peer) from parsed config
  - `devkit graph --config-path PATH` — CLI command with JSON output and `--output` file option
  - `POST /api/graph` — API endpoint returning `{nodes, edges}` for vis-network rendering
  - Web UI Graph page with CodeMirror input, force-directed vis-network renderer (forceAtlas2Based physics), stats bar, legend table, and edge summary table
  - Demo config pre-loaded so users can see the graph without pasting anything
  - 20 new tests pass; full suite at 363 tests (+20)

- [2026-05-29] fix: Config Diff now handles JSONC trailing commas and surfaces parse errors (files modified: devkit/tools/config_diff.py, tests/test_config_diff.py)
  - `_parse_jsonc` now strips trailing commas before parsing (common JSONC pattern)
  - Returns parse errors instead of silently falling back to empty dicts
  - Web UI shows red error card when config fails to parse
  - Safe URL handling: `//` in `https://` URLs no longer stripped
  - 6 new tests (53 total for diff, 343 overall)

- [2026-05-29] feat: add Config Diff feature — compare two OpenCode configs (files modified: devkit/tools/config_diff.py (new), api/routes/diff.py (new), api/schemas.py, api/main.py, devkit/cli.py, web/src/pages/Diff.tsx (new), web/src/lib/api.ts, web/src/App.tsx, web/src/components/Layout.tsx, tests/test_config_diff.py (new), README.md, DONE.md)
  - `devkit/tools/config_diff.py` — deep recursive JSON diff engine with section-grouped output
  - `devkit diff --from PATH --to PATH` — CLI command with JSON and Markdown output
  - `POST /api/diff` — compare two configs as inline JSON or file paths
  - `POST /api/diff/compare` — compare config against a historical analysis record
  - Web UI Diff page with split-view paste/upload panels, summary cards, and section-grouped changes table
  - 47 new tests pass; full suite at 337 tests (+47)

- [2026-05-29] docs: add FEATURES.md with 15 potential new feature ideas across impact tiers (files modified: FEATURES.md - new file)
  - Covers high-impact (config diff, `devkit init`, GitHub CI/CD, dependency graph viz)
  - Medium-impact (batch analysis, backup/rollback, PDF export, file watcher, config service)
  - Low-impact (badge generation, accessibility, plugin marketplace)
  - Engineering quality (E2E tests, performance, observability)
  - Includes selection criteria table for prioritizing what to build next

- [2026-05-28] fix: "Clear All Data" now clears Recommendations table (files modified: devkit/memory/recommendations.py, api/routes/history.py, tests/test_memory.py, README.md)
  - Added `clear_all()` method to `RecommendationTracker` (DELETE FROM recommendations)
  - `DELETE /api/history/all` now calls `RecommendationTracker.clear_all()` alongside `AnalysisHistoryStore.clear_all()`
  - Added 2 new tests: `test_clear_all_recommendations`, `test_clear_all_empty_recommendations`
  - Updated test count to 290 in README.md

- [2026-05-28] docs: add README audit step to AGENTS.md commit workflow (files modified: AGENTS.md, README.md)
  - AGENTS.md section 5 now lists "Audit README.md" as step #1 before commit & push
  - Fixed stale test counts in AGENTS.md (300→288) to match current state
  - Added missing `examples/` directory to README project structure tree

- [2026-05-28] docs: audit and correct README.md for accuracy (files modified: README.md)
  - Fixed `--verbose` applies to: changed "all" → "analyze, audit, score, migrate" (history unsupported)
  - Fixed `--format` applies to: added "history" (supports json/table)
  - Fixed "Clear All Data" description: removes "history data" (only clears session state, not SQLite)
  - Fixed roadmap test counts: Phase 3 43→37, Phase 4 60→59 (verified against actual test file counts)
  - Verified all CLI commands, flags, make targets, and structure tree entries exist and work

- [2026-05-28] fix: remove misleading tool config example from README — custom tools are auto-discovered (files modified: README.md, .opencode/opencode.json)
  - Removed incorrect `"tool"` config JSON block from README OpenCode Integration section
  - Removed invalid `"tool"` key from project's .opencode/opencode.json that caused schema error

- [2026-05-28] fix: Clear All Data button now clears CodeMirror editors on all tabs (files modified: web/src/pages/Analyze.tsx, web/src/pages/Audit.tsx, web/src/pages/Score.tsx, web/src/pages/Migrate.tsx)
  - Added reverse sync useEffect (configContent → configText) so session context resets propagate to local editor state
  - Also added allow rules for source venv, make, bun, pytest to OpenCode global bash permissions

- [2026-05-28] fix: improve Migration Assistant UX with empty states and auto-scroll (files modified: web/src/pages/Migrate.tsx)
  - Blue info card when no config loaded, guiding users to paste JSON or run Analyze tab first
  - Green check card when modern config has no deprecated fields
  - Auto-scroll to results section after migration analysis completes

- [2026-05-28] fix: recommendations tab was empty — analysis pipeline now populates recommendations SQLite table (files modified: api/routes/analyze.py)
  - Root cause: Dashboard read recommendations from analysis_records JSON column, but Recommendations tab queried separate recommendations table which was never written
  - Added RecommendationTracker.add_recommendations() call after each analysis run
  - Backfilled 3 orphaned recommendations from existing analysis records

- [2026-05-28] feat: add config context, severity breakdown, and recommendations to Dashboard (files modified: web/src/pages/Dashboard.tsx)
  - Breadcrumb bar showing current config path and last analysis timestamp
  - Severity breakdown row with colored chips (Critical/High/Medium/Low/Info counts)
  - Recommendations card with priority dots (red/yellow/gray), effort badges, category labels, and timestamp metadata

- [2026-05-28] fix: improve Health Score metric readability on wide screens (files modified: web/src/pages/Score.tsx)
  - Added max-w-2xl to constrain metric card width
  - Dotted leader lines between label and value spans for visual tracking
  - Dashed row separators with shrink-0 on label/value wraps

- [2026-05-28] docs: fix README.md CLI flag table and report format accuracy (files modified: README.md)
  - Added "Applies To" column to Common Flags table showing which commands each flag supports
  - Added missing --limit and --db-path flags
  - Corrected "HTML reports" to "Table, and HTML (via API)"

- [2026-05-28] feat: global session persistence with Clear All Data button (files modified: web/src/lib/SessionContext.tsx, web/src/components/Layout.tsx, web/src/main.tsx, web/src/pages/Analyze.tsx, web/src/pages/Audit.tsx, web/src/pages/Score.tsx, web/src/pages/Migrate.tsx, web/src/lib/api.ts, api/routes/audit.py, api/routes/score.py, api/routes/migrate.py, api/schemas.py, api/utils.py)
  - Add SessionContext with localStorage persistence for configContent + per-tab results
  - All analysis tabs now survive navigation via global context
  - Config content is shared: paste JSON once, run on any tab
  - Audit, Score, and Migrate pages now have paste/upload tabs like Analyze
  - Backend audit/score/migrate endpoints accept config_content (inline JSON) via new resolve_config_from_request utility
  - Add "Clear All Data" trash button in header to reset all state
  - 288 tests passing, TypeScript clean, Vite build clean

- [2026-05-28] fix: persist analysis history and analyze state, add start script (files modified: api/routes/analyze.py, api/routes/history.py, web/src/pages/Analyze.tsx, Makefile, start.sh)
  - Save analysis results to SQLite history DB after each analyze run (fixes Dashboard "No analysis data")
  - Fix route ordering: /trend before /{record_id} to prevent FastAPI 422 on Dashboard requests
  - Persist Analyze page state via sessionStorage (configText, activeTab, result) — survives tab switches
  - Add start.sh and Makefile: `make start` or `./start.sh` launches API + Vite in one terminal
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
