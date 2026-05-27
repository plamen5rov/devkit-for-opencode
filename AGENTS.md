# AGENTS.md — DevKit for OpenCode

> Quick-start instructions for OpenCode sessions working on this repo.

---

## Project State

This is a **CrewAI-based toolkit** in early scaffolding phase. There is **no executable code yet** — only planning documents and reference knowledge.

Do not attempt to run `pytest`, `python main.py`, or any build commands. Nothing exists to execute.

---

## Core Primitives

The system is built around three CrewAI concepts:

| Primitive | Location | Purpose |
|-----------|----------|---------|
| Agents | `agents/` (planned) | Decision-making units |
| Tasks | `tasks/` (planned) | Atomic work units |
| Tools | `tools/` (planned) | Reusable capabilities |

---

## How to Work in This Repo

### 1. Always start with TASKS.md

Read `TASKS.md` first. Select the next pending task with satisfied dependencies. Execute one task at a time.

### 2. Follow the Task Execution Protocol

The full protocol is in `AGENT.md`. Key rules:
- Change status to `in_progress` before starting
- Change to `done` or `blocked` after completion
- Add a short result summary to the task entry
- Never delete tasks — only update status

### 3. Use knowledge/ as Reference Only

The `knowledge/` directory contains OpenCode documentation snapshots. These are **read-only reference material** — do not modify them. Use them to understand OpenCode's APIs, agents, tools, and config patterns when building the toolkit.

---

## Expected Project Structure

When implementation begins, follow this layout:

```
devkit-for-opencode/
├── agents/          # CrewAI agent definitions
├── tasks/           # Task definitions
├── tools/           # Reusable tool implementations
├── configs/         # Configuration files
├── memory/          # State/persistence layer
├── tests/           # Test suite
├── output/          # Generated outputs
├── knowledge/       # OpenCode docs (reference only)
├── main.py          # Entry point
├── pyproject.toml   # Python package config
├── AGENT.md         # Role definition + TEP
├── ARCHITECTURE.md  # System design
└── TASKS.md         # Task tracker
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
| `TASKS.md` | Always first — find your work |
| `AGENT.md` | Before starting any task — understand role and protocol |
| `ARCHITECTURE.md` | When designing new components |
| `knowledge/*.md` | When you need OpenCode API/config details |

---

## What Not to Do

- Do not modify files in `knowledge/`
- Do not create agents, tasks, or tools that overlap with existing ones
- Do not add dependencies without noting why in the commit message
- Do not skip the TASKS.md workflow — all work must be tracked

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)
