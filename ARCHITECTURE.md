# ARCHITECTURE.md

## System Overview

DevKit for OpenCode is a modular toolkit for analyzing, auditing, and optimizing OpenCode configurations.

It provides stateless analyzer tools that return structured results, coordinated by thin agent wrappers that orchestrate the analysis pipeline.

---

## Core Design Principle

The system is built around stateless analyzers with no internal state:

- **Tools** → reusable analysis functions (config reader, permission analyzer, etc.)
- **Agents** → thin wrappers that coordinate multiple tools (orchestrator, auditor, advisor)
- **Tasks** → workflow compositions of agents (full audit, security scan, token optimization, migration)

Everything else is derived from these three.

---

## High-Level Architecture

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

---

## Component Responsibilities

### 1. Tools (Capability Layer)

- Stateless functions that analyze one aspect of the config
- Return structured results (dataclasses with to_dict())
- Reusable across agents and tasks
- Must not contain orchestration logic

### 2. Agents (Orchestration Layer)

- Coordinate multiple tools into a unified result
- Calculate scores, build summaries
- No LLM calls — purely programmatic

### 3. Tasks (Workflow Layer)

- Compose agents into end-to-end pipelines
- Generate reports (JSON, Markdown, HTML)
- Support multiple output formats

---

## Context Flow Rules

- Tools receive only what they need (config dict, project root)
- Results are structured dataclasses, not free text
- Agents aggregate tool results into unified reports
- Tasks compose agents and generate output

---

## Task Execution Model

1. Task receives config path
2. Task calls agent wrappers (orchestrator, auditor, advisor)
3. Each agent runs its tool pipeline
4. Results are aggregated into a report
5. Report is returned in requested format (JSON/Markdown/HTML)

---

## Constraints

- No tool should depend on hidden global state
- No circular dependencies between agents
- Tools must remain deterministic
- No LLM calls required — all analysis is programmatic

---

## Future Extensions

Planned extensions for this architecture:

- Task dependency graph
- Agent specialization system
- Tool registry with semantic search
- Memory compression layer
  