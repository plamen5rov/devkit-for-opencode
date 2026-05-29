# FEATURES.md — Potential New Features

> Brainstorm of new capabilities that could be added to DevKit for OpenCode.
> None are committed to — this is a wishlist for future prioritization.

---

## Current State

All 9 planned phases are complete (290 tests passing):

| Phase | What It Covers |
|-------|---------------|
| 1 | Python scaffolding, test infrastructure |
| 2 | 6 analyzer tools (config, permissions, agents, skills, MCP, commands) |
| 3 | 3 agent wrappers (orchestrator, auditor, advisor) |
| 4 | 4 workflow tasks (audit, security, token, migration) |
| 5 | 3 TypeScript tools for OpenCode runtime |
| 6 | SQLite memory layer (history + recommendations) |
| 7 | CLI (5 commands) + FastAPI + React web UI (7 pages) |
| 8 | Documentation, examples, AGENTS.md |
| 9 | Multi-agent orchestration, auto-remediation, plugin system |

---

## High-Impact Features

Features with the most user-facing value.

### Config Diff / Comparison

Compare two configs or before/after optimization to see exactly what changed.

- Split-view diff in the web UI
- CLI: `devkit diff --from config-v1.json --to config-v2.json`
- Could reuse the migration assistant's diff logic as a starting point
- Show health/risk score deltas between versions

### `devkit init` — Config Scaffolding

Interactive wizard that asks questions and generates an optimized `opencode.json`.

- CLI: `devkit init` launches interactive prompts
- Questions: preferred model, small model, agent needs, MCP servers, share preference
- Generates a valid, well-structured config with best practices baked in
- Optional: project-type templates (Python dev, Node.js dev, polyglot, etc.)
- Lower barrier to entry for new OpenCode users

### GitHub CI/CD Integration

GitHub Action that runs analysis on PRs and enforces config quality gates.

- Block merges on critical security issues
- Comment health score delta on PRs
- Auto-generate migration patches for deprecated fields
- Config validation check in CI with pass/fail thresholds
- Badge integration (health score shield in README)

### Dependency Graph Visualization

Interactive force-directed graph in the web UI showing system relationships.

- Agent-to-agent invocation graph
- Skill permission mappings per agent
- MCP server connections and token costs
- Command dependency chains
- Data is already present; needs D3.js or vis-network rendering

---

## Medium-Impact Features

Broader coverage and polish.

### Batch / Workspace Analysis

Analyze all configs in a team repo or directory at once.

- CLI: `devkit analyze --workspace /path/to/team/repos`
- Aggregate health scores across a team
- Cross-project comparison table
- Team trend reports over time
- API: `POST /api/workspace/analyze` with glob patterns

### Config Backup & Rollback

Automatic backups before applying fixes, with timeline of snapshots.

- Auto-backup before `--fix` operations
- `devkit backup --list` / `devkit backup --restore <timestamp>`
- SQLite-backed snapshot store with metadata (health score, reason)
- One-click restore in web UI
- Integration with auto-remediation pipeline

### Export as PDF

Generate downloadable PDF reports from the web UI or CLI.

- CLI: `devkit analyze --format pdf`
- API: `POST /api/export/pdf` with analysis data
- Web UI: download button on each results page
- Styled report with header, charts, findings table, recommendations
- Use WeasyPrint or similar Python library

### Real-Time File Watcher

Monitor config file for changes and re-run analysis automatically.

- CLI: `devkit watch --config-path ~/.config/opencode/opencode.json`
- Uses inotify / watchdog for file change detection
- Running health score display that updates live
- Optional: desktop notification when score drops below threshold
- Could also surface in web UI via WebSocket

### Config Validation Web Service

Hosted version where users paste a config URL and get analysis without installing.

- Simple landing page with paste/upload
- Runs same analysis pipeline behind the scenes
- Sharable report URLs with unique slugs
- Rate-limited anonymous access
- Optional authenticated access for history tracking

---

## Low-Impact Features

Niceties and polish.

### Badge Generation

Embeddable SVG shields for GitHub READMEs and project docs.

- `![Health Score](https://devkit.example.com/badge/health/user/repo)`
- `![Security Grade](https://devkit.example.com/badge/security/user/repo)`
- Dynamically updated based on latest analysis run
- Self-hostable badge server as part of the web API
- Cache with configurable TTL

### Accessibility Improvements

Web UI improvements for keyboard navigation and screen reader support.

- ARIA labels on all interactive elements
- Keyboard shortcuts for common actions (analyze, toggle tabs, clear data)
- Focus trap management for modals
- Screen reader announcements for async state changes
- Color contrast audit for all severity badges and chart elements

### Plugin Discovery / Marketplace

Central registry for community analyzer plugins with one-click install.

- `devkit plugin search <query>`
- `devkit plugin install <name>`
- Plugin metadata: name, version, description, author, test coverage
- Version pinning and update management
- Web UI: plugin catalog with descriptions and install buttons

---

## Engineering Quality

Infrastructure and reliability improvements.

### E2E & Integration Tests

End-to-end tests for the full stack.

- API endpoint integration tests with real HTTP requests (httpx or TestClient)
- Web UI tests with Playwright or Selenium
- CLI integration tests running real subprocess calls
- Snapshot tests for report output formats
- CI matrix across Python 3.10, 3.11, 3.12

### Performance Optimizations

Speed and resource improvements.

- Caching layer for repeated analyses (hash-based cache key on config content)
- Incremental analysis — only re-analyze changed sections
- Background workers for long-running batch analyses
- Lazy loading for report generation (stream JSON output)
- SQLite WAL mode and connection pooling for concurrent reads

### Observability

Logging, metrics, and debugging tools.

- Structured logging with levels (DEBUG, INFO, WARN, ERROR)
- Analysis duration metrics per tool and task
- Error tracking with stack traces and config context
- Health check endpoints for API liveness/readiness
- Admin panel for viewing logs, metrics, and database stats

---

## Selection Criteria

When choosing what to build next, consider:

1. **User impact** — Does this solve a real pain point?
2. **Implementation effort** — Days vs weeks of work?
3. **Existing foundation** — Can it reuse current code heavily?
4. **Documentation burden** — How much README/AGENTS updates needed?
5. **Testability** — Can it be tested deterministically?

Top candidates by these criteria:

| Feature | Impact | Effort | Reuse | Docs | Testable |
|--------|--------|--------|-------|------|----------|
| Config Diff/Comparison | High | Medium | High (migration diff) | Low | High |
| `devkit init` | High | Medium | Low | Medium | High |
| Dependency Graph Viz | High | Medium | High (existing data) | Low | Medium |
| E2E/Integration Tests | Medium | Medium | High | Low | High |
| Config Backup & Rollback | Medium | Low | Medium | Low | High |
| Batch/Workspace Analysis | Medium | Medium | High | Medium | High |
| GitHub CI/CD | High | Low-Medium | Medium | Medium | Medium |
| Export as PDF | Medium | Low | Low | Low | Medium |
| Real-Time Watcher | Medium | Low | Low | Low | High |
| Badge Generation | Low | Low | Medium | Low | High |
| Accessibility | Low | Medium | None | Low | Medium |
| Plugin Marketplace | Low | High | Low | High | Medium |
| Config Validation Service | Medium | High | Medium | High | Medium |
| Performance | Medium | Medium | None | Low | Medium |
| Observability | Medium | Medium | None | Low | High |
