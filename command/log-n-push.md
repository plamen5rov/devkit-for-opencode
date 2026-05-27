---
description: Update DONE.md changelog, commit all changes, and push to remote.
---

# Log & Push

Update the project's DONE.md changelog, then commit and push all staged/unstaged changes to the remote.

## Workflow

1. **Check working tree**
   - Run `git status` and `git diff --stat` to see current changes
   - Run `git log --oneline -3` for recent commit context

2. **Update DONE.md**
   - Read existing DONE.md and find the current phase header
   - Generate a concise bullet describing the changes
   - Add it under the correct phase (or create a new phase if none matches)

3. **Stage and commit**
   - Stage all changed files with `git add -A`
   - Write a conventional commit message describing the changes

4. **Push**
   - Run `git push` to push to remote

## Commit message style

Use conventional prefixes:
- `feat:` new feature
- `fix:` bug fix
- `refactor:` internal restructuring
- `docs:` documentation-only changes
- `test:` tests added or changed
- `chore:` maintenance or tooling changes

## DONE.md entry format

```
- [YYYY-MM-DD] Description of change (files modified: file1, file2, ...)
```
