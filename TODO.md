# TODO.md — DevKit for OpenCode

> Phased implementation roadmap. Execute one task at a time, following the Task Execution Protocol in `AGENT.md`.

---

## Phase 1: Project Scaffolding & Infrastructure

> **Goal:** Establish the runnable Python project structure with CrewAI, configs, and CI.

### 1.1 Initialize Python Package
- **Status:** done
- **Result:** Created `pyproject.toml` with CrewAI + dev dependencies, `main.py` entry point with CLI args, `.env.example`, and `.gitignore`. `pip install -e ".[dev]"` succeeds, `pytest` passes 2 tests, `python main.py --help` works.
- **Tasks:**
  - Create `pyproject.toml` with project metadata, Python version, and dependencies (crewai, crewai-tools, python-dotenv)
  - Create `main.py` entry point with basic CrewAI crew setup
  - Create `.env.example` with placeholder API keys
  - Add `.gitignore` entries for `.env`, `__pycache__`, `.venv`, `*.pyc`
- **Success Criteria:**
  - `pip install -e .` succeeds
  - `python main.py` runs without errors (even if no-op)
  - `.env.example` documents required environment variables

### 1.2 Directory Structure
- **Status:** done
- **Result:** Created `agents/`, `tasks/`, `tools/`, `configs/`, `memory/`, `output/` directories with `__init__.py` files. Added `configs/crew_config.yaml`. All imports work without errors.
- **Dependencies:** 1.1
- **Tasks:**
  - Create `agents/`, `tasks/`, `tools/`, `configs/`, `memory/`, `tests/`, `output/` directories
  - Add `__init__.py` to each Python package directory
  - Create `configs/crew_config.yaml` for crew-level configuration
- **Success Criteria:**
  - All directories exist with proper `__init__.py` files
  - `main.py` imports from the new package structure without errors

### 1.3 Test Infrastructure
- **Status:** done
- **Result:** Installed pytest + pytest-cov, created `tests/conftest.py` with shared fixtures, wrote 2 placeholder tests. `pytest` runs and passes cleanly. Configured in `pyproject.toml`.
- **Dependencies:** 1.2
- **Tasks:**
  - Install `pytest` as dev dependency
  - Create `tests/__init__.py` and `tests/conftest.py`
  - Write one placeholder test to verify pytest runs
  - Add `pytest` command to `pyproject.toml`
- **Success Criteria:**
  - `pytest` runs and passes with at least one test
  - Test output is clean and deterministic

---

## Phase 2: Core OpenCode Tools

> **Goal:** Implement CrewAI tools that wrap OpenCode's built-in capabilities.

### 2.1 Config Reader Tool
- **Status:** done
- **Result:** Created `devkit/tools/config_reader.py` with JSON/JSONC parsing, schema validation, auto-detection of config paths, and warning flags for common issues (missing catch-all permission, disabled MCPs/agents). 9 unit tests pass covering valid, invalid, missing files, and warning scenarios.
- **Dependencies:** 1.3
- **Tasks:**
  - Create `tools/config_reader.py` — reads and parses `opencode.json` / `opencode.jsonc`
  - Validate against OpenCode config schema
  - Support both global (`~/.config/opencode/`) and project (`.opencode/`) paths
  - Return structured JSON output
- **Success Criteria:**
  - Tool reads a valid `opencode.json` and returns parsed config
  - Tool returns clear error for invalid JSON or missing file
  - Unit tests cover valid, invalid, and missing file cases

### 2.2 Permission Analyzer Tool
- **Status:** done
- **Result:** Created `devkit/tools/permission_analyzer.py` with permission precedence resolution (global → agent → granular), effective permission matrix for all 16 known tools, and issue detection (dangerous bash commands, missing doom_loop/external_directory, agent override weakening, deny warnings). 12 unit tests pass.
- **Dependencies:** 2.1
- **Tasks:**
  - Create `tools/permission_analyzer.py` — analyzes permission rules
  - Evaluate permission precedence (global → agent → granular)
  - Report effective permissions for a given tool/action
  - Output structured permission matrix
- **Success Criteria:**
  - Given a config, correctly resolves permission for any tool
  - Handles wildcards, last-match-wins, and agent overrides
  - Tests verify at least 5 permission resolution scenarios

### 2.3 Agent Config Analyzer Tool
- **Status:** done
- **Result:** Created `devkit/tools/agent_analyzer.py` with agent parsing, mode/model/permission extraction, dependency graph from task permissions, and validation (invalid modes, bad temperature/top_p, missing descriptions, deprecated tools, circular dependencies, disabled subagents, builtin overrides). 16 unit tests pass.
- **Dependencies:** 2.1
- **Tasks:**
  - Create `tools/agent_analyzer.py` — analyzes agent definitions
  - Extract agent modes, models, prompts, permissions
  - Detect conflicts (e.g., disabled agent with active references)
  - Report agent dependency graph (who invokes whom)
- **Success Criteria:**
  - Lists all agents with their effective configuration
  - Identifies misconfigurations (missing models, invalid modes)
  - Tests cover JSON and markdown agent definitions

### 2.4 Skill Discovery & Analyzer Tool
- **Status:** done
- **Result:** Created `devkit/tools/skill_analyzer.py` with skill discovery across project/global paths, YAML frontmatter parsing, name/description validation, duplicate detection, and permission resolution per agent. 15 unit tests pass.
- **Dependencies:** 2.1
- **Tasks:**
  - Create `tools/skill_analyzer.py` — discovers and validates skills
  - Scan `.opencode/skills/`, `~/.config/opencode/skills/`, `.agents/skills/`
  - Validate frontmatter (name, description, license, compatibility)
  - Report skill availability and permission status per agent
- **Success Criteria:**
  - Discovers all valid skills in configured paths
  - Flags invalid frontmatter or name mismatches
  - Tests cover valid, invalid, and missing skill scenarios

### 2.5 MCP Server Analyzer Tool
- **Status:** done
- **Result:** Created `devkit/tools/mcp_analyzer.py` with MCP server parsing (local/remote), OAuth detection, token cost estimation, hardcoded secret detection, duplicate command warnings, and high token cost alerts. 16 unit tests pass.
- **Dependencies:** 2.1
- **Tasks:**
  - Create `tools/mcp_analyzer.py` — analyzes MCP server configurations
  - Enumerate local and remote MCP servers
  - Check OAuth status, enabled/disabled state
  - Report tool count and estimated token cost per server
- **Success Criteria:**
  - Lists all MCP servers with their status and tool counts
  - Flags disabled servers, missing auth, high-token-cost servers
  - Tests cover local, remote, and OAuth-configured servers

### 2.6 Command Analyzer Tool
- **Status:** done
- **Result:** Created `devkit/tools/command_analyzer.py` with command discovery, frontmatter parsing, placeholder extraction ($ARGUMENTS, $N, !`shell`, @file), dangerous shell command detection, and validation (missing descriptions, bad model format, subtask+agent double invocation). 15 unit tests pass.

**Phase 2 Complete:** All 6 core tools implemented with 82 total tests passing.
- **Dependencies:** 2.1
- **Tasks:**
  - Create `tools/command_analyzer.py` — analyzes custom slash commands
  - Scan `.opencode/commands/`, `~/.config/opencode/commands/`
  - Parse frontmatter (description, agent, model, subtask)
  - Validate placeholders (`$ARGUMENTS`, `!`shell`, `@file`)
- **Success Criteria:**
  - Lists all custom commands with their configuration
  - Validates command templates for syntax errors
  - Tests cover valid commands and malformed templates

---

## Phase 3: Core Agents

> **Goal:** Define the primary CrewAI agents that drive the toolkit.

### 3.1 DevKit Orchestrator Agent
- **Status:** pending
- **Dependencies:** 2.6
- **Tasks:**
  - Create `agents/orchestrator.py` — primary agent that coordinates all analysis
  - Define role: "OpenCode Configuration Orchestrator"
  - Assign tools from Phase 2
  - Define system prompt with workflow instructions
  - Configure model, temperature, and permissions
- **Success Criteria:**
  - Agent initializes with all Phase 2 tools
  - Can run a full analysis pipeline on a sample OpenCode config
  - Output is structured JSON with all analysis sections

### 3.2 Config Audit Agent
- **Status:** pending
- **Dependencies:** 3.1
- **Tasks:**
  - Create `agents/config_auditor.py` — specialized config validation agent
  - Role: validate OpenCode configs for errors, anti-patterns, security issues
  - Tools: config reader, permission analyzer, agent analyzer
  - Output: audit report with severity levels (error, warning, info)
- **Success Criteria:**
  - Detects common misconfigurations (invalid schema, missing required fields)
  - Flags security issues (secrets in config, overly permissive rules)
  - Produces human-readable audit report

### 3.3 Optimization Advisor Agent
- **Status:** pending
- **Dependencies:** 3.1
- **Tasks:**
  - Create `agents/optimization_advisor.py` — suggests improvements
  - Role: analyze config and suggest optimizations (token reduction, model selection, permission tightening)
  - Tools: all Phase 2 tools + MCP analyzer
  - Output: prioritized recommendations with rationale
- **Success Criteria:**
  - Suggests at least 3 actionable improvements per config
  - Recommendations are ranked by impact
  - Each recommendation includes before/after comparison

---

## Phase 4: Tasks & Workflows

> **Goal:** Define reusable CrewAI tasks that compose agents and tools into workflows.

### 4.1 Full Config Audit Task
- **Status:** pending
- **Dependencies:** 3.2
- **Tasks:**
  - Create `tasks/full_audit.py` — end-to-end config analysis
  - Input: path to OpenCode config (global or project)
  - Steps: read config → analyze permissions → analyze agents → analyze skills → analyze MCPs → analyze commands → generate report
  - Output: comprehensive audit report (JSON + Markdown)
- **Success Criteria:**
  - Runs all analyzers in sequence
  - Produces unified report with all sections
  - Handles missing files gracefully with partial reports

### 4.2 Security Scan Task
- **Status:** pending
- **Dependencies:** 3.2
- **Tasks:**
  - Create `tasks/security_scan.py` — security-focused analysis
  - Check for: secrets in config, overly permissive bash rules, exposed external directories, disabled doom_loop protection
  - Output: security findings with severity and remediation steps
- **Success Criteria:**
  - Detects at least 8 security anti-patterns
  - Each finding includes file path, line, severity, and fix
  - Tests verify detection of known bad configs

### 4.3 Token Optimization Task
- **Status:** pending
- **Dependencies:** 3.3
- **Tasks:**
  - Create `tasks/token_optimization.py` — analyze and reduce token usage
  - Analyze: MCP server token costs, agent model selection, skill description length, command template size
  - Suggest: model downgrades for simple tasks, skill deduplication, command consolidation
  - Output: token usage report with optimization recommendations
- **Success Criteria:**
  - Estimates total token cost per session
  - Identifies top 3 token consumers
  - Provides concrete reduction strategies with estimated savings

### 4.4 Migration Assistant Task
- **Status:** pending
- **Dependencies:** 3.2
- **Tasks:**
  - Create `tasks/migration_assistant.py` — help migrate between OpenCode versions
  - Detect deprecated config fields (e.g., `tools` boolean → `permission`)
  - Suggest updated config syntax
  - Generate migration diff
- **Success Criteria:**
  - Detects all known deprecated fields
  - Generates valid updated config
  - Tests cover at least 3 migration scenarios

---

## Phase 5: Custom OpenCode Tools

> **Goal:** Build TypeScript tools that run inside OpenCode itself (`.opencode/tools/`).

### 5.1 DevKit Analysis Tool (TypeScript)
- **Status:** pending
- **Dependencies:** 4.1
- **Tasks:**
  - Create `.opencode/tools/devkit-analyze.ts` — runs the Python analysis from inside OpenCode
  - Use `tool()` helper from `@opencode-ai/plugin`
  - Execute `python main.py --analyze` via Bun.$
  - Return structured analysis results
- **Success Criteria:**
  - Tool is discoverable in OpenCode's tool list
  - Returns valid JSON analysis results
  - Handles Python subprocess errors gracefully

### 5.2 Config Lint Tool (TypeScript)
- **Status:** pending
- **Dependencies:** 5.1
- **Tasks:**
  - Create `.opencode/tools/config-lint.ts` — lint OpenCode configs
  - Validate JSON schema, check for deprecated fields, flag anti-patterns
  - Return lint results with file paths, line numbers, and severity
- **Success Criteria:**
  - Catches schema violations
  - Reports warnings for anti-patterns
  - Output is parseable by OpenCode's tool system

### 5.3 Project Health Score Tool (TypeScript)
- **Status:** pending
- **Dependencies:** 5.1
- **Tasks:**
  - Create `.opencode/tools/health-score.ts` — calculate project health score
  - Factors: config validity, permission safety, agent coverage, tool utilization, documentation completeness
  - Return score (0-100) with breakdown
- **Success Criteria:**
  - Score is deterministic for same input
  - Breakdown shows contribution of each factor
  - Tests verify scoring for known-good and known-bad configs

---

## Phase 6: Memory & Persistence

> **Goal:** Add stateful memory layer for tracking analysis history and recommendations.

### 6.1 Analysis History Store
- **Status:** pending
- **Dependencies:** 1.3
- **Tasks:**
  - Create `memory/history.py` — stores analysis results over time
  - Use SQLite or JSON file storage
  - Record: timestamp, config path, findings, scores
  - Support querying by date range, severity, config path
- **Success Criteria:**
  - Stores and retrieves analysis results
  - Supports at least 3 query patterns
  - Tests verify CRUD operations

### 6.2 Recommendation Tracker
- **Status:** pending
- **Dependencies:** 6.1
- **Tasks:**
  - Create `memory/recommendations.py` — track recommendation lifecycle
  - Record: recommendation, status (open, applied, dismissed), date applied
  - Link recommendations to analysis runs
  - Generate "what changed since last analysis" report
- **Success Criteria:**
  - Tracks recommendation status over time
  - Generates diff reports between analysis runs
  - Tests verify status transitions and reporting

---

## Phase 7: CLI & User Interface

> **Goal:** Provide CLI commands for running analysis outside OpenCode.

### 7.1 CLI Entry Point
- **Status:** pending
- **Dependencies:** 4.1
- **Tasks:**
  - Create CLI with `argparse` or `click`
  - Commands: `analyze`, `audit`, `score`, `history`, `migrate`
  - Support `--config-path`, `--output-format` (json, markdown, table), `--verbose`
  - Add CLI entry to `pyproject.toml` scripts
- **Success Criteria:**
  - `devkit analyze --config-path ~/.config/opencode/opencode.json` runs full analysis
  - Output formats work correctly
  - `--help` shows all commands and options

### 7.2 Report Generator
- **Status:** pending
- **Dependencies:** 7.1
- **Tasks:**
  - Create `output/report_generator.py` — generate formatted reports
  - Support: JSON, Markdown, HTML (optional)
  - Include: summary, findings by severity, recommendations, score trends
  - Save to `output/` directory with timestamped filenames
- **Success Criteria:**
  - Generates valid output in each format
  - Reports include all analysis sections
  - Files are saved with correct naming convention

---

## Phase 8: Documentation & Polish

> **Goal:** Complete documentation, examples, and project readiness.

### 8.1 README.md
- **Status:** pending
- **Dependencies:** 7.2
- **Tasks:**
  - Write comprehensive README with:
    - Project overview and architecture diagram
    - Quick start guide
    - CLI usage examples
    - OpenCode integration instructions
    - Contributing guidelines
- **Success Criteria:**
  - README covers all major use cases
  - Includes copy-pasteable examples
  - Links to relevant knowledge files

### 8.2 Example Configs
- **Status:** pending
- **Dependencies:** 8.1
- **Tasks:**
  - Create `examples/` directory with:
    - `good-config.json` — well-configured OpenCode project
    - `bad-config.json` — intentionally misconfigured for testing
    - `minimal-config.json` — bare minimum working config
  - Add test cases that use example configs
- **Success Criteria:**
  - All example configs are valid JSON
  - Bad config triggers expected audit findings
  - Tests reference example configs

### 8.3 AGENTS.md Update
- **Status:** pending
- **Dependencies:** 8.1
- **Tasks:**
  - Update `AGENTS.md` to reflect implemented state
  - Remove "no executable code yet" warning
  - Add CLI usage instructions
  - Update project structure to match actual layout
- **Success Criteria:**
  - AGENTS.md accurately describes the project
  - Includes all implemented features
  - Workflow instructions are current

### 8.4 TASKS.md Migration
- **Status:** pending
- **Dependencies:** 8.3
- **Tasks:**
  - Convert `TASKS.md` to strict YAML format defined in the file
  - Migrate all completed tasks from this TODO.md
  - Add remaining/future tasks in YAML format
- **Success Criteria:**
  - All tasks follow the strict YAML schema
  - Completed tasks have `status: done` and `result` field
  - No information lost in migration

---

## Phase 9: Advanced Features (Future)

> **Goal:** Multi-agent collaboration, auto-remediation, and extensibility.

### 9.1 Multi-Agent Orchestration
- **Status:** pending
- **Dependencies:** 3.3, 4.4
- **Tasks:**
  - Implement CrewAI crew with agent delegation
  - Orchestrator delegates to Config Audit and Optimization Advisor
  - Aggregate results into unified report
- **Success Criteria:**
  - Agents execute in parallel where possible
  - Results are correctly aggregated
  - No duplicate work between agents

### 9.2 Auto-Remediation
- **Status:** pending
- **Dependencies:** 9.1
- **Tasks:**
  - Create `tasks/auto_fix.py` — generate config patches for common issues
  - Support: permission tightening, deprecated field updates, model optimization
  - Output: diff/patch files that can be applied
  - Safety: preview mode, dry-run, user confirmation required
- **Success Criteria:**
  - Generates valid patches for at least 5 issue types
  - Dry-run mode shows changes without applying
  - Applied patches produce valid configs

### 9.3 Plugin System
- **Status:** pending
- **Dependencies:** 9.1
- **Tasks:**
  - Design plugin interface for custom analyzers
  - Support: Python plugins, external tool integration
  - Plugin discovery and registration
  - Plugin configuration in `configs/plugins.yaml`
- **Success Criteria:**
  - Plugins can add new analysis types
  - Plugin output integrates with main report
  - Plugin errors don't crash the system

---

## Execution Order Summary

```
Phase 1 (Infrastructure) → Phase 2 (Tools) → Phase 3 (Agents) → Phase 4 (Tasks)
    ↓
Phase 5 (OpenCode Tools) → Phase 6 (Memory) → Phase 7 (CLI) → Phase 8 (Docs)
    ↓
Phase 9 (Advanced - Future)
```

**Start with:** Phase 1, Task 1.1 — Initialize Python Package
