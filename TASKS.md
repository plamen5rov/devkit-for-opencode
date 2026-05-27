# TASKS.md

## Purpose

This file defines all active, planned, and completed tasks for the DevKit for OpenCode system.

Tasks are the smallest executable units in the system.

---

## Task Format (STRICT)

Each task must include:

- id
- name
- type
- status
- input
- output
- success_criteria
- dependencies
- result (optional, filled after execution)
- notes (optional, agent-generated)

---

## Phase 1: Project Scaffolding & Infrastructure

```yaml
id: 1.1
name: Initialize Python Package
type: feature
status: done
input: None
output: pyproject.toml, main.py, .env.example, .gitignore
success_criteria:
  - pip install -e . succeeds
  - python main.py runs without errors
  - .env.example documents required environment variables
dependencies: []
result: Created pyproject.toml with CrewAI + dev dependencies, main.py entry point with CLI args, .env.example, and .gitignore. pip install -e ".[dev]" succeeds, pytest passes 2 tests, python main.py --help works.
```

```yaml
id: 1.2
name: Directory Structure
type: feature
status: done
input: None
output: agents/, tasks/, tools/, configs/, memory/, output/ directories with __init__.py
success_criteria:
  - All directories exist with proper __init__.py files
  - main.py imports from the new package structure without errors
dependencies:
  - 1.1
result: Created all package directories with __init__.py files. Added configs/crew_config.yaml. All imports work without errors.
```

```yaml
id: 1.3
name: Test Infrastructure
type: feature
status: done
input: None
output: tests/conftest.py, placeholder tests, pytest configuration
success_criteria:
  - pytest runs and passes with at least one test
  - Test output is clean and deterministic
dependencies:
  - 1.2
result: Installed pytest + pytest-cov, created tests/conftest.py with shared fixtures, wrote 2 placeholder tests. pytest runs and passes cleanly. Configured in pyproject.toml.
```

---

## Phase 2: Core OpenCode Tools

```yaml
id: 2.1
name: Config Reader Tool
type: tool
status: done
input: Path to opencode.json or opencode.jsonc
output: Parsed config dict with validation warnings
success_criteria:
  - Tool reads a valid opencode.json and returns parsed config
  - Tool returns clear error for invalid JSON or missing file
  - Unit tests cover valid, invalid, and missing file cases
dependencies:
  - 1.3
result: Created devkit/tools/config_reader.py with JSON/JSONC parsing, schema validation, auto-detection of config paths, and warning flags for common issues. 9 unit tests pass.
```

```yaml
id: 2.2
name: Permission Analyzer Tool
type: tool
status: done
input: OpenCode config with permission rules
output: Structured permission matrix with issue detection
success_criteria:
  - Given a config, correctly resolves permission for any tool
  - Handles wildcards, last-match-wins, and agent overrides
  - Tests verify at least 5 permission resolution scenarios
dependencies:
  - 2.1
result: Created devkit/tools/permission_analyzer.py with permission precedence resolution, effective permission matrix for 16 tools, and issue detection. 12 unit tests pass.
```

```yaml
id: 2.3
name: Agent Config Analyzer Tool
type: tool
status: done
input: OpenCode config with agent definitions
output: Agent analysis with dependency graph and validation
success_criteria:
  - Lists all agents with their effective configuration
  - Identifies misconfigurations (missing models, invalid modes)
  - Tests cover JSON and markdown agent definitions
dependencies:
  - 2.1
result: Created devkit/tools/agent_analyzer.py with agent parsing, mode/model/permission extraction, dependency graph, and validation. 16 unit tests pass.
```

```yaml
id: 2.4
name: Skill Discovery & Analyzer Tool
type: tool
status: done
input: OpenCode config and filesystem paths
output: List of discovered skills with validation results
success_criteria:
  - Discovers all valid skills in configured paths
  - Flags invalid frontmatter or name mismatches
  - Tests cover valid, invalid, and missing skill scenarios
dependencies:
  - 2.1
result: Created devkit/tools/skill_analyzer.py with skill discovery across project/global paths, YAML frontmatter parsing, name/description validation, duplicate detection. 15 unit tests pass.
```

```yaml
id: 2.5
name: MCP Server Analyzer Tool
type: tool
status: done
input: OpenCode config with MCP server definitions
output: MCP server analysis with token cost estimation
success_criteria:
  - Lists all MCP servers with their status and tool counts
  - Flags disabled servers, missing auth, high-token-cost servers
  - Tests cover local, remote, and OAuth-configured servers
dependencies:
  - 2.1
result: Created devkit/tools/mcp_analyzer.py with MCP server parsing, OAuth detection, token cost estimation, hardcoded secret detection. 16 unit tests pass.
```

```yaml
id: 2.6
name: Command Analyzer Tool
type: tool
status: done
input: OpenCode config and filesystem paths
output: List of discovered commands with validation
success_criteria:
  - Lists all custom commands with their configuration
  - Validates command templates for syntax errors
  - Tests cover valid commands and malformed templates
dependencies:
  - 2.1
result: Created devkit/tools/command_analyzer.py with command discovery, frontmatter parsing, placeholder extraction, dangerous shell command detection. 15 unit tests pass.
```

---

## Phase 3: Core Agents

```yaml
id: 3.1
name: DevKit Orchestrator Agent
type: feature
status: done
input: Path to OpenCode config
output: Structured analysis report with health score
success_criteria:
  - Agent initializes with all Phase 2 tools
  - Can run a full analysis pipeline on a sample OpenCode config
  - Output is structured JSON with all analysis sections
dependencies:
  - 2.6
result: Created devkit/agents/orchestrator.py with CrewAI agent creation, unified orchestration pipeline, summary generation, and health score calculation. 13 unit tests pass.
```

```yaml
id: 3.2
name: Config Audit Agent
type: feature
status: done
input: Path to OpenCode config
output: Audit report with severity-level findings
success_criteria:
  - Detects common misconfigurations (invalid schema, missing required fields)
  - Flags security issues (secrets in config, overly permissive rules)
  - Produces human-readable audit report
dependencies:
  - 3.1
result: Created devkit/agents/config_auditor.py with CrewAI auditor agent, full config audit pipeline, hardcoded secret detection, severity-categorized findings. 14 unit tests pass.
```

```yaml
id: 3.3
name: Optimization Advisor Agent
type: feature
status: done
input: Analysis results from orchestrator
output: Prioritized recommendations with before/after comparisons
success_criteria:
  - Suggests at least 3 actionable improvements per config
  - Recommendations are ranked by impact
  - Each recommendation includes before/after comparison
dependencies:
  - 3.1
result: Created devkit/agents/optimization_advisor.py with CrewAI advisor agent, optimization analysis for permissions/agents/MCP/skills/models. Prioritized recommendations with before/after. 16 unit tests pass.
```

---

## Phase 4: Tasks & Workflows

```yaml
id: 4.1
name: Full Config Audit Task
type: feature
status: done
input: Path to OpenCode config
output: Comprehensive JSON + Markdown audit report
success_criteria:
  - Runs all analyzers in sequence
  - Produces unified report with all sections
  - Handles missing files gracefully with partial reports
dependencies:
  - 3.2
result: Created devkit/tasks/full_audit.py with end-to-end audit pipeline, comprehensive JSON + Markdown reports, health score, findings table, prioritized recommendations. 13 unit tests pass.
```

```yaml
id: 4.2
name: Security Scan Task
type: feature
status: done
input: Path to OpenCode config
output: Security findings with severity and remediation steps
success_criteria:
  - Detects at least 8 security anti-patterns
  - Each finding includes file path, line, severity, and fix
  - Tests verify detection of known bad configs
dependencies:
  - 3.2
result: Created devkit/tasks/security_scan.py with 8 security checks, risk score, Markdown report with findings table. 19 unit tests pass.
```

```yaml
id: 4.3
name: Token Optimization Task
type: feature
status: done
input: Path to OpenCode config
output: Token usage report with optimization recommendations
success_criteria:
  - Estimates total token cost per session
  - Identifies top 3 token consumers
  - Provides concrete reduction strategies with estimated savings
dependencies:
  - 3.3
result: Created devkit/tasks/token_optimization.py with token usage analysis across MCP servers, agents, skills, and commands. Breakdown with per-item estimates, prioritized recommendations. 14 unit tests pass.
```

```yaml
id: 4.4
name: Migration Assistant Task
type: feature
status: done
input: Path to OpenCode config
output: Migration report with migrated config and diff
success_criteria:
  - Detects all known deprecated fields
  - Generates valid updated config
  - Tests cover at least 3 migration scenarios
dependencies:
  - 3.2
result: Created devkit/tasks/migration_assistant.py with migration detection for legacy tools, boolean tools, legacy model formats, boolean share, @latest plugins. Generates migrated config and Markdown report. 14 unit tests pass.
```

---

## Phase 5: Custom OpenCode Tools

```yaml
id: 5.1
name: DevKit Analysis Tool (TypeScript)
type: tool
status: done
input: Config path, mode, verbose flag
output: Analysis results from Python pipeline
success_criteria:
  - Runs Python analysis from inside OpenCode
  - Supports all analysis modes
  - Falls back gracefully from venv to system python
dependencies:
  - 4.1
result: Created .opencode/tools/devkit-analyze.ts — TypeScript tool that runs the Python analysis pipeline from inside OpenCode. Supports config path, mode selection, verbose output.
```

```yaml
id: 5.2
name: Config Lint Tool (TypeScript)
type: tool
status: done
input: Config path, fix flag
output: Structured lint results with severity levels
success_criteria:
  - Returns structured lint results
  - Supports --fix flag for generating corrected config
  - Integrates with OpenCode tool system
dependencies:
  - 5.1
result: Created .opencode/tools/config-lint.ts — TypeScript tool that runs security audit mode. Returns structured lint results with severity levels and fix suggestions.
```

```yaml
id: 5.3
name: Project Health Score Tool (TypeScript)
type: tool
status: done
input: Config path, detailed flag
output: Health score (0-100) with factor breakdown
success_criteria:
  - Score is deterministic for same input
  - Breakdown shows contribution of each factor
  - Tests verify scoring for known-good and known-bad configs
dependencies:
  - 5.1
result: Created .opencode/tools/health-score.ts — TypeScript tool that calculates project health score. Supports --detailed flag for factor breakdown.
```

---

## Phase 6: Memory & Persistence

```yaml
id: 6.1
name: Analysis History Store
type: feature
status: done
input: Analysis results
output: Persistent SQLite-backed history store
success_criteria:
  - Stores and retrieves analysis results
  - Supports at least 3 query patterns
  - Tests verify CRUD operations
dependencies:
  - 1.3
result: Created devkit/memory/history.py — SQLite-backed store with schema for analysis records. Supports querying by date range, config path, severity. Health score trend API. 14 unit tests pass.
```

```yaml
id: 6.2
name: Recommendation Tracker
type: feature
status: done
input: Analysis records and recommendations
output: Recommendation lifecycle tracking with diff reports
success_criteria:
  - Tracks recommendation status over time
  - Generates diff reports between analysis runs
  - Tests verify status transitions and reporting
dependencies:
  - 6.1
result: Created devkit/memory/recommendations.py — SQLite-backed tracker linking recommendations to analysis runs. Supports status lifecycle, notes, diff report generation. 12 unit tests pass.
```

---

## Phase 7: CLI & User Interface

```yaml
id: 7.1
name: CLI Entry Point
type: feature
status: done
input: Command-line arguments
output: CLI with analyze, audit, score, history, migrate commands
success_criteria:
  - devkit analyze --config-path runs full analysis
  - Output formats work correctly
  - --help shows all commands and options
dependencies:
  - 4.1
result: Created devkit/cli.py with argparse subcommands, auto-detect config, table formatter, history integration. Entry point registered as 'devkit' in pyproject.toml. 29 unit tests pass.
```

```yaml
id: 7.2
name: Report Generator
type: feature
status: done
input: Analysis data dictionary
output: Formatted reports in JSON, Markdown, HTML
success_criteria:
  - Generates valid output in each format
  - Reports include all analysis sections
  - Files are saved with correct naming convention
dependencies:
  - 7.1
result: Created devkit/output/report_generator.py — generates formatted reports in JSON, Markdown, and HTML. Saves to output/ directory with timestamped filenames. 13 unit tests pass.
```

---

## Phase 8: Documentation & Polish

```yaml
id: 8.1
name: README.md
type: feature
status: done
input: Project structure, CLI usage, architecture
output: Comprehensive README.md
success_criteria:
  - README covers all major use cases
  - Includes copy-pasteable examples
  - Links to relevant knowledge files
dependencies:
  - 7.2
result: Created README.md with overview, quickstart, CLI usage, OpenCode integration, architecture, project structure, configuration, contributing, roadmap, and license sections.
```

```yaml
id: 8.2
name: Example Configs
type: feature
status: done
input: None
output: examples/ directory with good, bad, and minimal configs
success_criteria:
  - All example configs are valid JSON
  - Bad config triggers expected audit findings
  - Tests reference example configs
dependencies:
  - 8.1
result: Created examples/good-config.json (well-configured), examples/bad-config.json (intentionally misconfigured), examples/minimal-config.json (bare minimum).
```

```yaml
id: 8.3
name: AGENTS.md Update
type: feature
status: done
input: Current project state
output: Updated AGENTS.md reflecting implemented state
success_criteria:
  - AGENTS.md accurately describes the project
  - Includes all implemented features
  - Workflow instructions are current
dependencies:
  - 8.1
result: Updated AGENTS.md to reflect fully implemented state with 256 tests, CLI usage instructions, updated project structure, and development principles.
```

```yaml
id: 8.4
name: TASKS.md Migration
type: refactor
status: done
input: TODO.md with all completed tasks
output: TASKS.md in strict YAML format
success_criteria:
  - All tasks follow the strict YAML schema
  - Completed tasks have status: done and result field
  - No information lost in migration
dependencies:
  - 8.3
result: Migrated all 24 tasks from TODO.md to strict YAML format with id, name, type, status, input, output, success_criteria, dependencies, and result fields.
```

---

## Phase 9: Advanced Features (Future)

```yaml
id: 9.1
name: Multi-Agent Orchestration
type: feature
status: done
input: CrewAI crew configuration
output: Agents executing in parallel with aggregated results
success_criteria:
  - Agents execute in parallel where possible
  - Results are correctly aggregated
  - No duplicate work between agents
dependencies:
  - 3.3
  - 4.4
result: Created devkit/agents/multi_agent.py — CrewAI crew with 3 agents (Orchestrator, Config Auditor, Optimization Advisor) supporting sequential and hierarchical processes. Aggregates findings and recommendations with deduplication. Multi-agent health and risk score calculation. 12 unit tests pass.
```

```yaml
id: 9.2
name: Auto-Remediation
type: feature
status: done
input: Security findings and recommendations
output: Config patches for common issues
success_criteria:
  - Generates valid patches for at least 5 issue types
  - Dry-run mode shows changes without applying
  - Applied patches produce valid configs
dependencies:
  - 9.1
result: Created devkit/tasks/auto_fix.py — generates patches for 5 issue types: permission tightening, deprecated fields, model optimization, MCP cleanup, agent fixes. Supports dry-run, category filtering, severity ordering, and file application. 20 unit tests pass.
```

```yaml
id: 9.3
name: Plugin System
type: feature
status: done
input: Plugin interface definition
output: Plugin discovery, registration, and configuration
success_criteria:
  - Plugins can add new analysis types
  - Plugin output integrates with main report
  - Plugin errors don't crash the system
dependencies:
  - 9.1
result: Created devkit/plugins/__init__.py — AnalyzerPlugin base class, PluginRegistry, discover_plugins(), run_plugin_analysis(), merge_plugin_results(). Error isolation for failing plugins. 12 unit tests pass.
```
