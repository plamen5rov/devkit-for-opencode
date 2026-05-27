---
name: git-commit-push
description: "create git commits and push code to GitHub safely. use when the user asks to commit, create branch, push changes, or prepare a pull request-ready commit with clear scope and verification."
---

# Purpose

Safely create a git commit and push it to GitHub with explicit scope, clear commit message quality, and user confirmation gates.

# Scope

- In scope: inspect working tree, stage intended files, create commit, push to remote branch, report result.
- Out of scope: destructive history rewriting by default, force-push by default, rewriting unrelated user changes.

# Required Inputs

- Target repository path
- Branch strategy:
  - Use current branch, or
  - Create/switch to a new branch name
- Commit scope:
  - Included files/patterns
  - Excluded files/patterns
- Commit message intent (summary and rationale)
- Push target (remote + branch) if different from default

If commit scope is not explicit, infer from recent task context and present the exact file list before committing.

# Safety Rules

- Never run destructive commands such as hard reset or checkout discard unless explicitly requested.
- Never include unrelated file changes without user approval.
- Never force-push unless user explicitly asks.
- Never amend commits unless explicitly asked.
- Prefer non-interactive git commands.

# Workflow

1. Repository and branch check
- Verify current repository and branch.
- Verify remote availability.

2. Change inventory
- Show staged and unstaged files.
- Summarize change intent by file.

3. Scope confirmation gate
- Propose exact files to stage.
- Ask for confirmation when ambiguity exists.

4. Stage and validate
- Stage only approved files.
- Re-check staged diff summary.

5. Commit creation
- Generate concise commit message using this structure:
  - Subject: imperative, <= 72 chars
  - Body: what changed and why (when needed)
- Create commit.

6. DONE.md changelog (MANDATORY)
- After a successful commit, check if `DONE.md` exists at the repo root.
- If it exists, append a new changelog entry under the current phase/section.
- Entry format: `- [YYYY-MM-DD] Concise description of what changed (files modified: file1, file2, ...)`
- If no section header exists for the current phase, create one.
- Commit the DONE.md update as a separate commit: `docs: update DONE.md changelog`
- If DONE.md does not exist, create it with a `# DONE.md — Changelog` header and the first entry.

7. Push
- Push to selected remote/branch.
- If branch has no upstream, set upstream on first push.

8. Result report
- Return commit hash, branch, remote, push status, and any follow-up suggestions.

# Commit Message Policy

Use conventional-style prefixes when appropriate:

- feat: new feature
- fix: bug fix
- refactor: internal restructuring
- docs: documentation-only changes
- test: tests added or changed
- chore: maintenance or tooling changes

Example:
- feat(auth): add DCF token refresh validation

# Required Output

Provide all items:

1. Files committed
2. Commit message used
3. Commit hash
4. Branch and remote pushed to
5. Push status
6. Any skipped files and why

# Failure Handling

- If push fails due to auth: report exact git error and suggest credential check.
- If push fails due to non-fast-forward: stop, summarize divergence, propose pull/rebase strategy.
- If branch protection blocks push: report protection rule and suggest PR workflow.

# Optional PR Handoff

If requested, prepare PR-ready summary:

- Title suggestion
- Summary bullets
- Test evidence bullets
- Risk/rollback notes

# Hard Gates

- Do not commit without explicit scope.
- Do not push if commit failed.
- Do not force-push or amend without explicit user instruction.
- Stop if unexpected unrelated changes appear and ask user how to proceed.
