---
name: multi-agent-git-flow
description: Use when starting work in a Git repository that other people or coding agents also edit, before creating a branch or worktree, claiming an issue, opening a pull request, or running stash, reset, force-push or worktree cleanup.
---

# Multi-Agent Git, Context & Issue-to-PR Flow (Standalone Skill)

> **Non-Authoritative Projection**: Git worktrees isolate checkout, index, and
> branch state — not OS permissions, network, or secrets.

## 1. Context Grounding (Before Any Edit)

1. Read in order: `docs/VIBE_CODING_CONTEXT.md` → `docs/architecture/STATUS.md`
   → `AGENTS.md` / `CLAUDE.md`.
2. Treat `STATUS.md` (verified against real source files) as implementation
   truth over older design docs. Never assume a `Deleted` or `Design` module
   exists; update `STATUS.md` when adding, wiring, or deleting modules.
3. Keep `AGENTS.md` and `CLAUDE.md` behaviorally equivalent.

## 2. Fresh Remote Baseline & Worktree Isolation

1. Fetch fresh remote refs before reading, planning, or editing:
   ```bash
   git fetch --prune origin
   git status --short --branch
   git symbolic-ref --short refs/remotes/origin/HEAD
   ```
   If `git fetch` fails, **stop and report the failure** — never treat a stale
   local `HEAD` as fresh remote code.
2. **Protect the primary checkout**:
   - Clean, on default branch, no local commits, only behind:
     `git merge --ff-only origin/<default>`.
   - Dirty, occupied, detached, ahead, diverged, or on a feature branch:
     **leave completely untouched** — never stash, reset, switch, or pull it.
3. **Create an isolated task worktree from `origin/<default>`**:
   ```bash
   git worktree add .worktrees/<task> -b <feat|fix|docs|chore|test>/<topic> origin/<default>
   test "$(git -C .worktrees/<task> rev-parse HEAD)" = "$(git rev-parse origin/<default>)"
   ```
   Never use `claude/`, `cursor/`, or `codex/` as shared PR branch prefixes.
4. **Shared worktree dependencies**: Avoid duplicating `.venv`/`node_modules`
   per worktree (`UV_PROJECT_ENVIRONMENT` for Python, lockfile-keyed external
   store for Node), and verify `python -c "import pkg; print(pkg.__file__)"`
   resolves inside the **current worktree** (not the main checkout).

## 3. Issue-to-PR Loop & Managed Issue Claims

1. **Deduplicate first**: Search existing open issues before filing a new one.
   Keep stable scope, acceptance criteria, verification plan, risk, and
   dependencies in the issue body — never volatile heartbeats.
2. **Publish or update one Managed Issue Claim before editing** (marker on the
   first non-empty line so updates `PATCH` the same comment):
   ```markdown
   <!-- agent-claim:<owner/repo#number>:<task-id> -->

   ### Agent Claim

   - Status: `running`
   - Automation identity: `<Claude Code | Cursor | Codex>`
   - GitHub actor: `<github-handle>`
   - Agent: `<claude-code | cursor | codex>`
   - Session: `<session-id>`
   - Task: `<scope-YYYYMMDD>`
   - Repo: `<repo-name>`
   - Branch: `<feat|fix|docs|chore>/<topic>`
   - Worktree: `<.claude/worktrees/... | .worktrees/...>`
   - Claim issue: `<owner/repo#number>`
   - PR: `none`
   - Lease expires: `<YYYY-MM-DDTHH:MM:SSZ>`
   - Updated: `<YYYY-MM-DDTHH:MM:SSZ>`

   Owned paths:
   - `<repo-relative/path>`

   Out of scope:
   - `<path-or-none>`

   Dependencies:
   - `<issue-or-none>`

   Current summary:
   <one-line current step>

   Next action:
   <next concrete verification or PR step>
   ```
   Allowed statuses: `claimed`, `running`, `waiting_review`, `blocked`,
   `completed`, `released`, `failed`.
3. **Stop on overlapping `Owned paths`**: If two active claims declare identical
   or nested paths on the same repo, stop editing until a single owner is
   assigned.
4. **Link evidence & close cleanly**: Include `Closes #N` / `Related #N`, exact
   commands run, exit codes, and risk/rollback in the PR; update the claim
   comment to `waiting_review`, `completed`, `released`, or `failed` on handoff
   or merge.
5. **Avoid GitHub stacked PR base branches** under squash-merge auto-delete:
   always base every PR on `main`; sequence dependent PRs by fetching and
   cherry-picking/rebasing onto fresh `origin/main` after the prior PR merges.
6. **Cross-repo & cross-session handoffs**: Update multi-repo changes in
   dependency order (shared protocol/library -> consumers -> platform docs).
   When switching between backend/frontend sessions or approaching the 60-message
   context cliff, emit a concise handoff note recording goal, done, remaining,
   API/schema/config contract changes, consumer actions, and fresh verification
   commands (`checklists/handoff.template.md`).

## 4. Slow-Motion Brakes & 5-Point Safe Worktree Cleanup

- Before `git stash`, `git reset --hard`, or `git push --force`: inspect
  ownership (`git status --short`, `git worktree list`), create a
  `backup/<topic>-<date>` branch if needed, and require explicit human approval.
- Before commit/PR: verify `git diff --name-only`, `git diff --check`, and
  `git log --oneline origin/<default>..HEAD` contain only owned scope.
- **5-point safe worktree cleanup** (when unsure, keep the worktree): remove a
  task worktree ONLY when (1) `git status --short` is clean, (2) zero unpushed
  commits, (3) no active agent/session uses it, (4) no open PR depends on it,
  and (5) valuable commits are pushed, merged, or intentionally abandoned.

*Optional helper scripts*: `https://github.com/OpenAgenticSecurity/agentic-sdlc/tree/main/scripts` (`workspace-git.py`, `agent-claim.py`, `link-shared-node-deps.mjs`).
