# AGENTS.md — DevKit for OpenCode

> Quick-start instructions for OpenCode sessions working on this repo.

---

## Project State

This is a **fully implemented Python toolkit** with 300 passing tests across all 9 phases.

All core components are implemented:
- 6 analyzer tools (config, permissions, agents, skills, MCP, commands)
- 3 agent wrappers (orchestrator, auditor, advisor) + multi-agent orchestration
- 4 workflow tasks (audit, security, token, migration) + auto-remediation
- Memory layer with SQLite-backed history and recommendation tracking
- CLI with 5 commands and report generator (JSON/Markdown/HTML)
- 3 TypeScript tools for OpenCode runtime integration
- Plugin system with AnalyzerPlugin base class and error isolation

---

## Core Primitives

The system is built around stateless analyzer tools coordinated by agent wrappers:

| Component | Location | Purpose |
|-----------|----------|---------|
| Tools | `devkit/tools/` | 6 analyzers for config, permissions, agents, skills, MCP, commands |
| Agents | `devkit/agents/` | Orchestrator, Config Auditor, Optimization Advisor |
| Tasks | `devkit/tasks/` | Full audit, security scan, token optimization, migration assistant |

Additional components:
| Component | Location | Purpose |
|-----------|----------|---------|
| CLI | `devkit/cli.py` | Entry point with 5 subcommands |
| Memory | `devkit/memory/` | SQLite history store and recommendation tracker |
| Output | `devkit/output/` | Report generator (JSON, Markdown, HTML) |

---

## How to Work in This Repo

### 1. Always start with TODO.md

Read `TODO.md` first. Select the next pending task with satisfied dependencies. Execute one task at a time.

### 2. Follow the Task Execution Protocol

The full protocol is in `AGENT.md`. Key rules:
- Change status to `in_progress` before starting
- Change to `done` or `blocked` after completion
- Add a short result summary to the task entry
- Never delete tasks — only update status

### 3. Run Tests After Every Change

```bash
source .venv/bin/activate && pytest
```

All 300 tests must pass. Add new tests for any new functionality.

### 4. Use knowledge/ as Reference Only

The `knowledge/` directory contains OpenCode documentation snapshots. These are **read-only reference material** — do not modify them.

### 5. Commit, Log, and Update Docs After Every Change

After every meaningful change, always:

1. **Git commit & push** to the repository
2. **Update DONE.md** with a changelog entry (date, description, files modified)
3. **Update README.md** when the change affects user-facing instructions (new commands, changed workflows, new features)

---

## Project Structure

```
devkit-for-opencode/
├── devkit/
│   ├── agents/          # Agent wrappers (orchestrator, auditor, advisor)
│   ├── cli.py           # CLI entry point with argparse subcommands
│   ├── configs/         # Configuration files
│   ├── memory/          # SQLite-backed history store and recommendation tracker
│   ├── output/          # Report generator (JSON, Markdown, HTML)
│   ├── tasks/           # Workflow tasks (audit, security, token, migration)
│   ├── tools/           # Core analyzer tools (6 total)
│   └── __init__.py
├── tests/               # 300 unit tests
├── examples/            # Example OpenCode configs (good, bad, minimal)
├── .opencode/tools/     # TypeScript tools for OpenCode runtime
├── knowledge/           # OpenCode reference docs (read-only)
├── output/              # Generated reports
├── main.py              # Legacy entry point (use `devkit` CLI instead)
├── pyproject.toml       # Python package config
├── README.md            # Project documentation
├── AGENTS.md            # This file
├── ARCHITECTURE.md      # System design
├── TODO.md              # Phased implementation roadmap
└── TASKS.md             # Task tracker
```

---

## CLI Usage

```bash
# Run full analysis
devkit analyze --config-path ~/.config/opencode/opencode.json

# Security audit
devkit audit --format markdown

# Health score
devkit score --detailed

# View history
devkit history --limit 5

# Migration assistant
devkit migrate --diff
```

---

## Development Principles

- **Atomic tasks** — each task must be independently executable
- **Stateless tools** — tools should not maintain internal state
- **Explicit communication** — agent-to-agent data flow must be structured (JSON/YAML)
- **Minimal context** — pass only what's needed between tasks
- **No overengineering** — start minimal, add complexity only when required

---

## Key Files to Read

| File | When to Read |
|------|-------------|
| `TODO.md` | Always first — find your work |
| `ARCHITECTURE.md` | When designing new components |
| `knowledge/*.md` | When you need OpenCode API/config details |

---

## What Not to Do

- Do not modify files in `knowledge/`
- Do not create agents, tasks, or tools that overlap with existing ones
- Do not add dependencies without noting why in the commit message
- Do not skip the TODO.md workflow — all work must be tracked

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)
