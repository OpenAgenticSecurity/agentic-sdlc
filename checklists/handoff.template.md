# Session / Cross-Layer Handoff Template

Use this template when:
- Handing a task off to a fresh session before hitting the 60-message context cliff,
- Switching between backend, frontend, infra, or sibling repositories after changing a shared contract, or
- Pausing work so another engineer or agent can resume without re-reading the entire transcript.

Keep this file in task scratch (or attach to the tracking issue/PR) — do not commit temporary handoffs to `main`.

```markdown
# Handoff: <short task title>

- **Updated (UTC)**: `<YYYY-MM-DDTHH:MM:SSZ>`
- **Repository & Branch**: `<owner/repo>` @ `<feat|fix|chore/topic>`
- **Base Commit / HEAD SHA**: `<40-char base SHA>` -> `<40-char HEAD SHA>`
- **Worktree**: `<repo-relative worktree path or none>`
- **Tracking Issue / PR**: `<#N or none>`

## 1. Goal & Current State

- **Goal**: <one-sentence objective>
- **Done**:
  - <completed item with exact file:line or commit>
- **Remaining**:
  - <concrete next step>
- **Blockers / Decisions Needed**:
  - <none | exact question for owner>

## 2. Shared Contract Changes (For Downstream Consumers)

- **API / Route Changes**:
  - `<none | METHOD /path — request/response field diff>`
- **Schema / DB / Migration Changes**:
  - `<none | table/schema change + migration status>`
- **Config / Feature Flag / Default Changes (3-Layer Check)**:
  - `<none | code default vs shipped template vs deployed env>`
- **Required Consumer Actions**:
  - [ ] <e.g., update frontend client types & add disabled-feature 3-layer test>

## 3. Fresh Verification Evidence

- Command(s) run on current HEAD:
  - `<exact command>` -> exit `<code >` (`<summary>`)
- Explicit `NOT_RUN` / `does_not_prove`:
  - <what has not been verified yet>
```
