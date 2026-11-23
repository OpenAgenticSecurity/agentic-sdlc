# Multi-AI Git Workflow Standard

**Status**: accepted baseline
**Updated**: 2026-11-20

## Goal

This standard keeps `main` stable and PRs reviewable when multiple humans and AI coding tools work in the same repository or multi-repo workspace.

## Core Rules

1. `main` is an integration branch, not a development workspace.
2. One task must bind one branch, one worktree, one owner, and one explicit scope.
3. The scope must state in-scope files/modules, out-of-scope files/modules, validation commands, and dependencies.
4. One branch has one owner at a time.
5. Different AI tools must not push to the same branch.
6. PRs must be small enough to review.
7. Every PR description must include verification evidence.
8. Destructive Git commands require explicit human confirmation.
9. Workspace root folders holding multiple independent repositories must not be initialized as a meta Git repository unless intentionally designed as one.
10. New task worktrees must be based on `origin/<default>`, even when the local default checkout is clean.
11. Issue-backed implementation work must publish a managed issue claim comment before code editing starts.

## Pull Policy

Recommended product repo policy:

```bash
git config pull.rebase true
git config pull.ff only
git config branch.main.rebase false
```

Meaning:

- `main` should fast-forward only.
- feature branches may rebase onto latest `origin/main` when not shared.
- shared branches require coordination before rebase.

## Worktree Layout

Each AI tool should use its own worktree namespace:

```text
repo/
  .claude/worktrees/
  .cursor/worktrees/
  .worktrees/              # Codex or generic worktrees
```

Ignore local worktree folders through repository `.gitignore` or `.git/info/exclude`:

```gitignore
.worktrees/
worktrees/
.claude/worktrees/
.cursor/worktrees/
.codex/worktrees/
```

## Branch Naming

Recommended patterns:

```text
docs/<topic>
feat/<topic>
fix/<topic>
chore/<topic>
test/<topic>
audit/<topic>
plan/<topic>
release/<topic>
batch/<topic>
merge/<topic>
backup/<topic>-<date>
```

Shared PR branch names must describe the work, not the tool source. Do not use
`codex/`, `claude/`, or `cursor/` as normal PR branch prefixes; record
agent/tool ownership in the PR description, handoff report, task record, or
branch owner field.

`codex/`, `claude/`, and `cursor/` are allowed only as local temporary
isolation namespaces and should not be pushed or opened as PRs by default. If a
temporary branch needs to enter the shared workflow, rename it to a semantic
prefix such as `docs/`, `feat/`, or `fix/` first.

Avoid names such as `update`, `fixes`, `wip`, `test`, and `new-code`.

## Starting Work

Before an AI tool starts editing:

```bash
git fetch origin --prune
git status --short --branch
git rev-list --left-right --count HEAD...@{u}
```

If the default branch checkout is clean and only behind remote, fast-forward it first:

```bash
git merge --ff-only @{u}
```

If the default branch checkout has uncommitted changes, do not pull or reset it. Create a clean worktree from the latest remote instead:

```bash
git worktree add .worktrees/<task-name> -b <branch-name> origin/<default>
```

Inside the worktree:

```bash
git status --short --branch
git branch -vv
```

The starting state must be clean.

The same rule applies after PR merges and cross-repository syncs before starting
the next task: keep the primary default checkout clean/latest when safe, but
create the task worktree from `origin/<default>`. If local WIP or another agent
blocks the primary checkout, continue from a clean latest worktree instead of
implicitly stashing, overwriting, or resetting the primary checkout.

In a multi-repo workspace, use the bundled workspace helper:

```bash
python3 scripts/workspace-git.py audit --root /path/to/workspace --fetch
python3 scripts/workspace-git.py clean-defaults --root /path/to/workspace --no-fetch --occupied <active-repo>
python3 scripts/workspace-git.py agent-start --root /path/to/workspace --repo <repo> --task <task-name> --branch <branch-name> --create-worktree
```

`workspace-git.py clean-defaults` is a dry-run by default. Pass `--apply` only
when occupied repositories are listed and the dry-run output shows that a
checkout can be safely fast-forwarded without switching, stashing, resetting,
or touching local WIP.

## Assignment Contract

Every AI work assignment must include:

- branch name
- worktree path
- owner
- files or directories owned
- files or directories out of scope
- expected test command
- whether the AI may commit
- whether the AI may push
- dependency PRs or branches

## Issue Claim Comments

When a task is tied to a GitHub issue, the assigned human or AI agent must
publish one managed issue comment before editing code. The issue body remains
the stable scope record; dynamic coordination state belongs in comments.

This rule applies to local Codex sessions, Claude Code sessions, Cursor sessions,
and CI/automation bots. It is required even when multiple agents share the same
GitHub actor.

The managed comment must include:

- automation identity and GitHub actor
- agent/tool and session id
- repo, branch, worktree, and owned paths
- out-of-scope paths, affected contracts, and dependencies
- lease or heartbeat timestamp
- next action and linked PR or handoff state

For simple local sessions, the minimum required fields are: marker, status,
automation identity, GitHub actor, agent, session id, task id, repo, branch,
worktree when applicable, claim issue, owned paths, updated timestamp, lease
expiry for active work, current summary, and next action. PR URL,
out-of-scope paths, affected contracts, and dependencies are optional until
they exist, but the comment should show `TBD`, `none`, or `-` rather than
omitting the field silently.

Use a hidden marker so tools can update the same comment instead of adding
duplicates:

```text
<!-- agent-claim:<owner/repo#number>:<task-id> -->
```

Use a stable `task-id` for one attempt by one owner on one branch. The default
format is lowercase kebab-case `<scope>-<YYYYMMDD>`, for example
`model-route-20260625` or `api-w1-consume-route-20260625`. Keep the same
`task-id` when the same owner resumes the same branch or updates the PR. Create
a new `task-id` when ownership transfers to another agent, the branch changes,
the original branch is abandoned, or a new implementation attempt starts after
failure. In a handoff, the releasing agent should set the old claim to
`released`, `blocked`, `failed`, or `waiting_review`; the new owner publishes a
new claim comment that references the old `task-id` or PR in the summary.
Durable queue ids minted by automation may omit the date only when the queue
already guarantees uniqueness and the issue comment still records the branch
and session.

The managed comment status should move through this lifecycle:

| Status | Meaning |
|--------|---------|
| `claimed` | The owner reserved the issue scope before editing. |
| `running` | Implementation, verification, or PR update is actively in progress. |
| `waiting_review` | A PR or handoff is ready and the agent is no longer editing the branch. |
| `blocked` | Work cannot continue without a named dependency or human decision. |
| `completed` | Acceptance criteria are met and the linked PR/evidence is complete. |
| `released` | The agent intentionally released the claim without completing it. |
| `failed` | The attempt is abandoned after a concrete failure, with evidence. |

Use `heartbeat` updates for active work and `release` updates for terminal
handoffs. Expired comments may remain in the timeline, but agents should treat
them as stale and inspect the branch/worktree before taking over.

A claim is stale when the lease has expired and no PR/check/run evidence shows
current activity. Do not delete stale comments. Update the same managed comment
to `released`, `blocked`, or `failed` when the owner can still do so; otherwise
the next owner should publish a new managed comment and state why the previous
claim is stale.

Concurrent claims are resolved by scope, not by comment timestamp alone. If two
active claims name overlapping owned paths in the same repository, both agents
must stop editing until a single owner is chosen for that overlap. The agent
that has not started code changes should release its claim first. If both have
local changes, preserve both worktrees and ask the human/product owner to assign
one owner before either branch is pushed or rebased. If the claims are on the
same issue but owned paths do not overlap, both may continue only when each
comment explicitly lists its owned paths and out-of-scope paths.

If an agent exits unexpectedly and cannot release its claim, the next owner may
take over only after recording why the previous claim is stale: expired lease,
no fresh PR/check/run activity, and inspected branch or worktree state when it
is accessible. The takeover comment must use a new `task-id`, reference the old
`task-id` or PR, and set `Current summary` to the recovery reason. Do not edit,
delete, or rewrite the old comment unless the original owner or a repository
maintainer is deliberately closing the stale attempt.

Do not use the issue body for volatile owner, heartbeat, branch, PR, or
handoff state. The issue body should contain stable scope, acceptance criteria,
verification plan, dependencies, and links to canonical plans.

This repository provides a standalone reference CLI (`scripts/agent-claim.py`):

```bash
python3 scripts/agent-claim.py render \
  --issue '<owner/repo#number>' \
  --task <task-id> \
  --status running \
  --identity 'Claude Code' \
  --actor <github-handle> \
  --agent <claude-code|codex|cursor> \
  --session <session-id> \
  --repo <repo> \
  --branch <branch> \
  --worktree .claude/worktrees/<task> \
  --lease-expires 2026-11-20T18:00:00Z \
  --owned-path <path> \
  --output claim.md

python3 scripts/agent-claim.py check-overlap claim.md other-claim.md
python3 scripts/agent-claim.py publish claim.md
```

Equivalent comments follow this canonical shape (see `profiles/L1-team/issue-claim.example.md`):

```markdown
<!-- agent-claim:org/service#42:auth-guard-20261120 -->

### Agent Claim

- Status: `running`
- Automation identity: `Claude Code`
- GitHub actor: `alice`
- Agent: `claude-code`
- Session: `claude-20261120-a`
- Task: `auth-guard-20261120`
- Repo: `service`
- Branch: `fix/auth-guard`
- Worktree: `.claude/worktrees/auth-guard`
- Claim issue: `org/service#42`
- PR: `none`
- Lease expires: `2026-11-20T18:00:00Z`
- Updated: `2026-11-20T16:00:00Z`

Owned paths:
- `src/auth/guard.py`
- `tests/test_auth_guard.py`

Out of scope:
- `frontend/`

Dependencies:
- `none`

Current summary:
Implementing fail-closed token audience check with negative mutation tests.

Next action:
Run make agent-check and open PR linked to org/service#42.
```

To update an existing claim comment directly via `gh api` without using `scripts/agent-claim.py`, find the comment containing the marker and `PATCH` it instead of posting a duplicate:

```bash
ISSUE_REPO="org/service"
ISSUE_NUMBER="42"
TASK_ID="auth-guard-20261120"
MARKER="<!-- agent-claim:${ISSUE_REPO}#${ISSUE_NUMBER}:${TASK_ID} -->"
BODY_FILE="claim.md"

COMMENT_ID="$(
  MARKER="$MARKER" gh api "repos/${ISSUE_REPO}/issues/${ISSUE_NUMBER}/comments" |
    python3 -c 'import json, os, sys
marker = os.environ["MARKER"]
comments = json.load(sys.stdin)
print(next((str(c["id"]) for c in comments if marker in (c.get("body") or "")), ""))'
)"

if [ -n "$COMMENT_ID" ]; then
  gh api "repos/${ISSUE_REPO}/issues/comments/${COMMENT_ID}" \
    --method PATCH \
    -f "body=$(cat "$BODY_FILE")"
else
  gh issue comment "$ISSUE_NUMBER" --repo "$ISSUE_REPO" --body-file "$BODY_FILE"
fi
```

Rollout rule: new issue-backed implementation work must publish the managed
comment before editing. Existing open work should add or refresh the managed
comment at the next heartbeat, PR update, review response, or handoff. Do not
block an otherwise ready old PR only because it predates this rule; do require
a claim comment before new edits continue when active ownership is unclear.

## Development Checkpoints

During development, run:

```bash
git status --short
git diff --stat
git diff --check
```

Before committing, inspect:

```bash
git diff --name-only
git diff --cached --name-only
```

Do not commit generated caches, local license archives, local worktree folders, debug-only compose overrides, or unrelated roadmap/status edits.

If unrelated changes are discovered, split them into another branch or stash them with a clear message. Do not use stash to hide review noise in the final PR.

## Handling Uncommitted Changes

Before syncing, resetting, deleting a worktree, or switching ownership, inspect:

```bash
git status --short
git diff --stat
git diff --name-only
```

If changes are valuable but not ready:

```bash
git stash push -u -m "wip/<scope>-before-sync-<date>"
```

If changes may belong to another AI tool, stop and identify the owner first:

```bash
git worktree list
git branch -vv
```

If the same file was edited by multiple agents, choose a single owner before continuing.

## Diverged Main SOP

Use this process when local `main` and `origin/main` have diverged, or when `origin/main` moves during integration:

1. Diagnose:

```bash
git fetch origin --prune
git status --short --branch
git rev-list --left-right --count main...origin/main
git log --oneline origin/main..main
git log --oneline main..origin/main
```

2. Create an isolated integration worktree:

```bash
git worktree add .worktrees/<task-name> -b merge/<task-name> origin/main
```

3. Merge the target branch without committing immediately:

```bash
git merge --no-ff --no-commit <feature-branch>
```

4. Resolve only relevant conflicts.

5. Verify:

```bash
git diff --check
```

Run the targeted product tests for the change.

6. If `origin/main` moves again, reset the integration worktree to latest `origin/main`, replay the merge, and rerun verification.

7. Preserve old local state when needed:

```bash
git branch backup/main-before-sync-<date> <old-main-sha>
```

8. Push only after verification and human approval.

Default: no force push. Use force only as an explicit, reviewed history-repair operation.

## PR Requirements

Every PR should include:

```markdown
## Summary
- what changed

## Dependency
- dependency PRs, branches, or versions

## Test Plan
- [x] command actually run

## Risk / Rollback
- risk and rollback path
```

Before opening a PR:

```bash
git fetch origin --prune
git log --oneline origin/main..HEAD
git diff --name-only origin/main...HEAD
git diff --check
```

## Agent Compliance Model

The process should be enforced in five layers so humans and AI agents follow it by default instead of relying on memory:

1. **Repository entrypoint**: when both `AGENTS.md` and `CLAUDE.md` exist, they must be behavior-equivalent and aligned with this standard, including start sequence, Git rules, verification gate, and post-merge sync rule. One file must not be stricter while the other weakens the workflow.
2. **Repository hygiene**: `.gitignore` ignores local worktree namespaces and generated local state so accidental review noise is visible before PR time.
3. **PR contract**: PR templates and branch protection require summary, dependency, validation evidence, risk/rollback, and passing checks before merge.
4. **Automation checks**: CI or local `make check` style commands should verify docs links, required metadata, and product tests; agents must quote the exact commands they ran.
5. **Workspace preflight**: in multi-repo workspaces, run `scripts/workspace-git.py audit --root /path/to/workspace` before cross-repo work and `scripts/workspace-git.py agent-start` before editing a repository. Occupied repositories must be passed to cleanup commands with `--occupied`.

When a task spans multiple repositories, the agent should create or update PRs in dependency order, wait for required checks, merge through protected branches, then return every touched repository to its clean latest default branch before reporting completion. If a default checkout cannot be safely synced because of local-only WIP, the agent should create or point to a clean latest worktree based on `origin/<default>` and clearly report why the original checkout was not returned to default. Handoff reports must state real PR URLs, merge/local-sync status, and whether each touched repo ended on its clean latest default branch so owners do not need to ask whether the PR exists, whether it merged, or whether the local checkout is current.

## Cross-Repository and Submodule Rules

Cross-repository work must merge in dependency order:

1. dependency repository PRs
2. product repository integration PRs
3. documentation index or release notes
4. cleanup branches

For submodule pointer changes:

1. commit inside the submodule
2. push the submodule branch
3. open and merge the submodule PR
4. preserve the referenced commit SHA
5. update the parent repository pointer
6. open and merge the parent repository PR

Before merging a parent PR that changes a submodule pointer:

```bash
git submodule status <submodule-path>
git -C <submodule-path> rev-parse HEAD
git ls-tree HEAD <submodule-path>
```

Do not squash a dependency PR if the parent repository points to a commit that would become unreachable or confusing after squash.

## Cleanup After Merge

After a task completes or a PR merges, the default habit is to return the repo to its clean latest default branch:

```bash
git fetch --prune origin
git switch main
git status --short --branch
git rev-list --left-right --count main...origin/main
git merge --ff-only origin/main
git status --short --branch
git branch --merged main
git worktree list
```

Use `master` and `origin/master` for repositories whose default branch is `master`. If there is uncommitted local work, use a named stash only when the changes are owned by the current agent and are small and mechanical; otherwise, keep the original checkout intact and continue from a clean latest worktree based on `origin/<default>`.

Delete local branches only when:

- the PR is merged or intentionally abandoned
- the branch has no valuable unmerged commits
- no worktree still uses the branch

Do not delete backup branches until their contents are confirmed obsolete.

## AI Session Exit Worktree Policy

If an AI tool asks whether to delete a worktree when a session ends, default to keeping it unless the task is complete and preserved.

Before deleting a worktree, verify:

```bash
git status --short
git branch -vv
git worktree list
gh pr list --state open --head <branch-name>
git log --oneline origin/main..<branch-name>
```

It is safe to delete the worktree only when all of these are true:

- the worktree is clean
- valuable commits are pushed, merged, or intentionally abandoned
- no open PR needs changes from that worktree
- no human or AI tool is actively using it
- dependency branches or submodule work are merged or preserved elsewhere

When uncertain, keep the worktree. Preserving review context is more important than local disk cleanup.

## AI Tool Safety Checklist

Before an AI tool edits:

- [ ] it is in a dedicated worktree
- [ ] it is not on `main`
- [ ] its branch is based on the intended base branch
- [ ] it knows which files it owns
- [ ] it knows which files are out of scope
- [ ] the worktree is clean

Before an AI tool commits:

- [ ] `git diff --name-only` contains only intended files
- [ ] `git diff --check` passes
- [ ] relevant tests or docs checks have run
- [ ] the commit message describes one logical change

Before an AI tool opens a PR:

- [ ] `git log origin/main..HEAD` shows only intended commits
- [ ] PR body includes dependencies and verification evidence
- [ ] no customer-unsafe debug defaults are introduced
- [ ] submodule pointers reference pushed commits
