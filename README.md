# DevKit for OpenCode

> A modular AI-assisted development layer for analyzing, auditing, and optimizing OpenCode configurations.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests: 337 passing](https://img.shields.io/badge/tests-337%20passing-brightgreen.svg)]()

## Overview

DevKit provides deep analysis of OpenCode configuration files (`opencode.json`). It detects security issues, anti-patterns, token inefficiencies, and migration needs — then generates actionable recommendations with health and risk scores.

**What it does:**
- Analyzes permissions, agents, skills, MCP servers, commands, and config structure
- Calculates health scores (0–100) and risk scores (0–100)
- Detects hardcoded secrets, overly permissive rules, and deprecated config fields
- Tracks analysis history with SQLite-backed persistence
- Generates JSON, Markdown, Table, and HTML (via API) reports
- Runs as a standalone CLI, web UI (FastAPI + React), or inside OpenCode via TypeScript tools
- Web UI features: paste/upload configs, fix generation, health score trends, session persistence with "Clear All Data"

**Who it's for:**
- OpenCode users who want to validate their configuration
- Teams managing multiple OpenCode projects with consistent standards
- Developers building on top of OpenCode's agent/tool/skill ecosystem

## Table of Contents

- [Quickstart](#quickstart)
- [CLI Usage](#cli-usage)
- [OpenCode Integration](#opencode-integration)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)

## Quickstart

### Prerequisites

- Python 3.10 or higher
- `pip` or `uv` for package management

### Installation

```bash
# Clone the repository
git clone https://github.com/plamen5rov/devkit-for-opencode.git
cd devkit-for-opencode

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"
```

### Minimal Example

```bash
# Run a full analysis on your OpenCode config
devkit analyze --config-path ~/.config/opencode/opencode.json

# Or use auto-detection (checks .opencode/ and ~/.config/opencode/)
devkit analyze
```

### Web UI

DevKit includes a FastAPI + React web interface with:
- **Analyze** — paste or upload configs, view health scores, get fix suggestions with copy-paste output
- **Security Audit** — scan for hardcoded secrets, dangerous permissions, and anti-patterns
- **Health Score** — detailed factor breakdown with charts and trends
- **Config Diff** — compare two configs side by side, grouped by section with added/removed/changed counts
- **Migration Assistant** — detect deprecated fields and generate migrated configs
- **History & Recommendations** — track analysis trends and manage suggestions
- **Session persistence** — all tab state survives navigation; shared config input across tabs
- **Clear All Data** — one-click reset in the header clears all session state

```bash
# Start both servers with one command
make start
# or
./start.sh

# Web UI:    http://localhost:5173
# API docs:  http://localhost:8000/docs
```

## CLI Usage

DevKit provides six commands via the `devkit` CLI:

### `devkit analyze`

Run the full analysis pipeline — config reader, permission analyzer, agent/skill/MCP/command analyzers, and optimization advisor.

```bash
# JSON output (default)
devkit analyze --config-path ~/.config/opencode/opencode.json

# Markdown report
devkit analyze --format markdown

# Table view
devkit analyze --format table
```

### `devkit audit`

Run a security-focused scan — detects hardcoded secrets, dangerous bash permissions, exposed directories, disabled doom_loop protection, and more.

```bash
devkit audit --config-path ~/.config/opencode/opencode.json --format markdown
```

### `devkit score`

Calculate the project health score (0–100) based on config validity, permission safety, agent coverage, tool utilization, and documentation.

```bash
# Quick score
devkit score --config-path ~/.config/opencode/opencode.json

# Detailed breakdown
devkit score --detailed --format table
```

### `devkit history`

View analysis history stored in the SQLite database.

```bash
# Show latest 10 records as a table
devkit history

# Filter by config path, JSON output
devkit history --config-path ~/.config/opencode/opencode.json --format json --limit 5

# Custom database path
devkit history --db-path /custom/path/history.db
```

### `devkit migrate`

Detect and fix deprecated config fields — legacy `tools` → `permission`, boolean `share` → string, `@latest` plugins, legacy model formats.

```bash
devkit migrate --config-path ~/.config/opencode/opencode.json --diff
```

### `devkit diff`

Compare two OpenCode configs to see exactly what changed — field by field, with added/removed/changed grouping.

```bash
# Compare two config files
devkit diff --from ~/.config/opencode/opencode.json --to examples/good-config.json

# JSON output
devkit diff --from config-v1.json --to config-v2.json --format json
```

### Common Flags

| Flag | Applies To | Description |
|------|------------|-------------|
| `--config-path PATH` | all | Path to `opencode.json` (auto-detects if omitted) |
| `--format json\|markdown\|table` | analyze, audit, score, history, diff | Output format |
| `--verbose` | analyze, audit, score, migrate | Enable verbose output |
| `--fix` | audit | Generate fixed config |
| `--detailed` | score | Show factor breakdown |
| `--diff` | migrate | Show config diff |
| `--limit N` | history | Max records to show |
| `--db-path PATH` | history | Path to history database |

### Report Generator

Generate formatted reports saved to the `output/` directory:

```python
from devkit.output.report_generator import ReportGenerator

gen = ReportGenerator()
gen.generate_json(analysis_data)
gen.generate_markdown(analysis_data)
gen.generate_html(analysis_data)
```

Reports include summary, findings by severity, recommendations, score trends, and raw data.

## OpenCode Integration

DevKit includes TypeScript tools that run inside OpenCode itself. Place these in your project's `.opencode/tools/` directory:

| Tool | Purpose |
|------|---------|
| `devkit-analyze.ts` | Run full analysis pipeline from OpenCode |
| `config-lint.ts` | Security audit with `--fix` support |
| `health-score.ts` | Calculate health score with detailed breakdown |

These tools are auto-discovered by OpenCode at startup — just place them in the directory and restart OpenCode. No config declaration needed.

## Architecture

DevKit is built around a pipeline of stateless analyzer tools that return structured results:

| Component | Count | Purpose |
|-----------|-------|---------|
| **Tools** | 7 | Config reader, permission analyzer, agent/skill/MCP/command analyzers, config diff |
| **Agents** | 3 | Orchestrator, Config Auditor, Optimization Advisor (coordinate analyzers) |
| **Tasks** | 4 | Full audit, security scan, token optimization, migration assistant |

### Analysis Pipeline

```
Config File → Config Reader → Permission Analyzer → Agent Analyzer
                                    ↓
                              Skill Analyzer → MCP Analyzer → Command Analyzer
                                    ↓
                              Orchestrator → Summary + Health Score
                                    ↓
                              Config Auditor → Security Findings
                                    ↓
                              Optimization Advisor → Recommendations
```

### Memory Layer

- **AnalysisHistoryStore** — SQLite-backed persistence for analysis results with trend analysis
- **RecommendationTracker** — Tracks recommendation lifecycle (open → applied/dismissed) with diff reports

### Scoring

**Health Score (0–100):** Based on issues, warnings, MCP token estimates, agent count, and permission catch-all presence.

**Risk Score (0–100):** Deducts based on severity-weighted security findings (hardcoded secrets, dangerous permissions, exposed directories, disabled protections).

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
├── api/                 # FastAPI backend with 7 route groups
├── web/                 # React + Vite + TypeScript + Tailwind frontend
├── tests/               # 337 unit tests
├── examples/            # Example OpenCode configs (good, bad, minimal)
├── .opencode/tools/     # TypeScript tools for OpenCode runtime
├── knowledge/           # OpenCode reference docs (read-only)
├── output/              # Generated reports
├── main.py              # Legacy entry point (use `devkit` CLI instead)
├── pyproject.toml       # Python package config
├── Makefile             # start, format, lint, test targets
├── start.sh             # One-command API + Vite launcher
├── AGENTS.md            # Agent quick-start guide
├── ARCHITECTURE.md      # System design
├── TODO.md              # Phased implementation roadmap
└── TASKS.md             # Task tracker
```

## Configuration

### Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| (none) | DevKit runs purely as a local analyzer — no LLM API keys needed | No |

### Python Package

```toml
[project]
name = "devkit-for-opencode"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0",
    "jsonschema>=4.20.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "python-multipart>=0.0.9",
    "pydantic>=2.0.0",
]
```

## Contributing

### Development Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
make test

# Type-check + lint
make lint

# Auto-format
make format

# Start both servers
make start
```

### Adding New Tools

1. Create a new file in `devkit/tools/`
2. Implement a class or function that returns structured output
3. Add unit tests in `tests/`
4. Register the tool in the orchestrator agent

### Code Style

- Follow PEP 8 conventions
- Use type hints on all public functions
- Keep tools stateless — no internal state between calls
- Write tests before implementation

### Running the Full Pipeline

```bash
# Analyze your own config
devkit analyze --config-path ~/.config/opencode/opencode.json --verbose

# Generate a Markdown report
devkit analyze --format markdown > report.md

# Run security audit
devkit audit --format markdown
```

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 1. Infrastructure | ✅ Done | Python scaffolding, test infrastructure |
| 2. Core Tools | ✅ Done | 7 analyzers (config, permissions, agents, skills, MCP, commands, diff) with 130 tests |
| 3. Agent Wrappers | ✅ Done | 3 agent wrappers (orchestrator, auditor, advisor) with 37 tests |
| 4. Tasks & Workflows | ✅ Done | 4 workflow tasks with 59 tests |
| 5. OpenCode Tools | ✅ Done | 3 TypeScript tools |
| 6. Memory & Persistence | ✅ Done | SQLite history + recommendation tracker (26 tests) |
| 7. CLI & UI | ✅ Done | CLI with 6 commands + FastAPI + React web UI (8 pages, 42 tests) |
| 8. Documentation | 🚧 In Progress | README, examples, AGENTS.md update |
| 9. Advanced Features | ✅ Done | Multi-agent orchestration, auto-remediation, plugin system |

## License

MIT — see [LICENSE](LICENSE) for details.

## Credits

Built on [OpenCode](https://opencode.ai) for configuration analysis.
