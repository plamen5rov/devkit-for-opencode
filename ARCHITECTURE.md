# ARCHITECTURE.md

## System Overview

DevKit for OpenCode is a modular AI-assisted development layer designed to structure how agents, tasks, and tools are composed and executed inside OpenCode.

It does not replace the runtime environment. It defines how intelligence is organized.

---

## Core Design Principle

The system is built around three primitives:

- **Agents** → decision-making units (defined in AGENT.md)
- **Tasks** → atomic units of execution
- **Tools** → reusable functional capabilities

Everything else is derived from these three.

---

## High-Level Architecture

User Request
↓
OpenCode Runtime
↓
Agent Layer (AGENT.md)
↓
Task Planner (TASKS.md)
↓
Tool Execution Layer
↓
Structured Output

---

## Component Responsibilities

### 1. Agents (Behavior Layer)

- Interpret intent
- Break down goals into tasks
- Decide execution strategy
- Enforce constraints from AGENT.md

---

### 2. Tasks (Execution Layer)

- Atomic and independent units of work
- Must have:
  - clear input
  - clear output
  - success criteria
- No hidden logic or implicit behavior

---

### 3. Tools (Capability Layer)

- Stateless functions where possible
- Reusable across tasks and agents
- Must not contain orchestration logic

---

## Context Flow Rules

- Context must always be **minimal and task-relevant**
- No global memory unless explicitly required
- Long outputs must be summarized before passing forward
- Prefer structured formats (JSON/YAML) over natural language

---

## Task Execution Model

1. Agent receives request
2. Agent decomposes into tasks
3. Tasks are executed independently
4. Results are aggregated
5. Final output is structured and validated

---

## Scalability Model

The system is designed to evolve in layers:

- Phase 1: Static tasks + manual execution
- Phase 2: Agent-driven task orchestration
- Phase 3: Tool auto-discovery and reuse
- Phase 4: Multi-agent collaboration graph

---

## Constraints

- No task should depend on hidden global state
- No circular dependencies between agents
- Tools must remain deterministic
- Architecture must remain framework-agnostic

---

## Future Extensions

Planned extensions for this architecture:

- Task dependency graph
- Agent specialization system
- Tool registry with semantic search
- Memory compression layer
  