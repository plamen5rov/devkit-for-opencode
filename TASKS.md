# TASKS.md

## Purpose

This file defines all active, planned, and completed tasks for the DevKit for OpenCode system.

Tasks are the smallest executable units in the system.

---

## Task Format

Each task must follow this structure:

```yaml
id: unique-task-id
name: short descriptive title
type: feature | tool | refactor | experiment
status: pending | in_progress | done | blocked

input:
  description: what the task receives

output:
  description: expected result

success_criteria:
  - measurable condition 1
  - measurable condition 2

dependencies:
  - optional task ids
  
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
