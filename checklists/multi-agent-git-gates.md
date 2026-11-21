# Multi-Agent Git & Worktree Three-Gate Checklist

**Status**: accepted baseline
**Updated**: 2026-11-20
**Chinese**: [multi-agent-git-gates.zh.md](multi-agent-git-gates.zh.md)
**Sources**: [Multi-Agent Git Workflow](https://fz.cool/Multi-Agent-Git-Workflow/) & [Agentic Assurance Engineering](https://fz.cool/agentic-software-engineering-real-sdlc/)
**Authoritative Standards & CLI**: [standards/multi-ai-git-workflow.md](../standards/multi-ai-git-workflow.md), [`scripts/workspace-git.py`](../scripts/workspace-git.py), [`scripts/agent-claim.py`](../scripts/agent-claim.py)

> **Core Rule**: The faster AI writes code, the slower destructive Git actions
> must become, and the sharper ownership boundaries must be. One task = one
> branch + one worktree + one active writer + one explicit scope.

---

## 1. Split "Owner" into Four Distinct Questions

| Question | Engineering Carrier |
|---|---|
| Who defines the goal, shared truth, and priority? | Authority docs, ADR, Task Issue owner |
| Who approves this class of change? | `CODEOWNERS`, branch/ruleset protection, reviewer allowlist |
| Who may write this branch/path right now? | Active Managed Issue Claim, lease, branch, isolated worktree |
| Who actually executed the action? | Automation identity, GitHub actor, agent/session ID, provenance |

## 2. Minimum Task Assignment Contract (Before Launching Any Agent)

| Field | Example |
|---|---|
| `branch` | `fix/auth-rotate-key` |
| `owned_paths` | `src/auth/`, `tests/auth/` |
| `out_of_scope` | `src/billing/`, `migrations/` |
| `test_command` | `pytest tests/auth -x` |
| `can_commit` / `can_push` | `yes` / `no` |
| `dependencies` | `#1024` (must merge before starting) |

- [ ] Verify parallel agents have **strictly disjoint** `owned_paths` (`python3 scripts/agent-claim.py check-overlap ...`).
- [ ] Remember: `git worktree` isolates Git index/branch/WIP, **not** OS permissions, network, env vars, or secrets.

## 3. Three Mandatory Gates

### Gate 1 — Pre-Edit (Never Develop on `main` or Dirty Default Checkout)

```bash
git fetch origin --prune
git status --short --branch
git branch -vv
git rev-list --left-right --count HEAD...origin/main
git worktree add .worktrees/<task-name> -b <type>/<topic> origin/main
```

- [ ] Local safety defaults configured: `pull.rebase=true`, `pull.ff=only`, `branch.main.rebase=false`.
- [ ] Worktree paths excluded via `.git/info/exclude` (`.worktrees/`, `.claude/worktrees/`, `.cursor/worktrees/`, `.codex/worktrees/`).
- [ ] Reading order completed: `AGENTS.md` / `CLAUDE.md` → `STATUS.md` → `VIBE_CODING_CONTEXT.md` → cross-repo authority → Issue + claim → remote Git state.

### Gate 2 — Pre-Commit (Scope & Cleanliness Proof)

```bash
git status --short
git diff --stat
git diff --check
git diff --name-only
git diff --cached --name-only
```

- [ ] Every staged file is inside `owned_paths` (zero drive-by refactors outside scope).
- [ ] Zero whitespace errors (`git diff --check` clean), zero secrets, zero host-specific paths.

### Gate 3 — Pre-PR (Small Enough for a Human Reviewer to Finish Reading)

```bash
git fetch origin --prune
git log --oneline origin/main..HEAD
git diff --name-only origin/main...HEAD
git diff --check
```

- [ ] PR summary includes exact changed scope, dependency PRs/order, **commands actually run** with fresh results, agent/tool identity, branch owner, and rollback path.
- [ ] Cross-repo changes follow explicit merge topology: shared contracts → backward-compatible producer/consumer → integration replay → docs/cleanup.

## 4. Slow-Motion Brakes for Destructive Git Actions

| Action | Risk | Mandatory Brake Before Running |
|---|---|---|
| `git stash` | Hides another engineer's or agent's uncommitted WIP | Inspect `git status --short`, `git diff --stat`, `git worktree list`; confirm 100% ownership first |
| `git reset --hard` | Permanently destroys uncommitted local changes | Create `backup/<topic>-<date>` branch or verified stash first; require explicit human approval |
| `git push --force` | Overwrites upstream review history or peer commits | Confirm branch owner, preserve backup branch/tag, require explicit human approval |
| Delete branch | Loses PR review context or unmerged commits | Verify no open PR depends on it and all needed commits are merged |
| Remove worktree | Loses unpushed local work | Pass all 5 checks below — **when unsure, keep the worktree** |

## 5. Five-Point Safe Worktree Cleanup Checklist

Only remove a task worktree when **all five** checks pass:

```bash
git status --short                              # 1. Working tree is clean
git branch -vv                                  # 2. Zero unpushed commits
git worktree list                               # 3. No active session/agent uses it
gh pr list --state open --head <branch-name>    # 4. No open PR depends on it
git log --oneline origin/main..<branch-name>    # 5. Valuable commits are pushed or merged
```
