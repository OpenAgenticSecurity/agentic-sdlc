# AI Coding Context Standard

**Status**: accepted baseline
**Updated**: 2026-11-20

## Decision

Every adopting repository should provide a small set of AI-coding context files so Claude Code, Codex, Cursor, Gemini CLI, and future coding agents start from the same project truth.

Shared standards define the structure; each repository owns its concrete content.

## Required Product-Local Files

| File | Required | Purpose |
|------|----------|---------|
| `AGENTS.md` | recommended single canonical root guide | Tool-neutral agent instructions and repository boundaries (read natively by Cursor, Codex, and modern agents) |
| `CLAUDE.md` | thin `@AGENTS.md` pointer (behavior-equivalent to `AGENTS.md`) | Claude Code entrypoint forwarding to `AGENTS.md` without duplicating rules |
| `docs/VIBE_CODING_CONTEXT.md` | required for active product repos | Two-minute working memory: what exists, what is deleted, current sprint, stack, code patterns |
| `docs/architecture/STATUS.md` | required for active product repos | Single source of truth for implemented, partial, deleted, design-only, and planned modules |
| `docs/todo/TECH_DEBT_TRACKER.md` | recommended | Current debt inventory and owner-visible status |
| `docs/todo/VIBE_CODING_DEBT_PROTOCOL.md` | recommended | Mistake-prevention rules learned from prior AI coding sessions |
| `.cursor/rules/*.mdc` | optional (path-scoped `globs:` only) | Avoid `alwaysApply: true` duplicates of `AGENTS.md`; use only for file-pattern-scoped rules if needed |

## Session Start Sequence

AI coding sessions should read product-local context in this order:

1. `docs/VIBE_CODING_CONTEXT.md`
2. `docs/architecture/STATUS.md`
3. `CLAUDE.md` or `AGENTS.md`
4. `docs/todo/TECH_DEBT_TRACKER.md` when the task touches known debt
5. `docs/todo/VIBE_CODING_DEBT_PROTOCOL.md` when present
6. relevant shared architecture or contract docs when the task crosses repositories

If `STATUS.md` and another document disagree, trust `STATUS.md` for implementation reality.

## Product Context File Template

`docs/VIBE_CODING_CONTEXT.md` should answer:

- What is this product?
- What actually exists in code?
- What was deleted and must not be assumed?
- What is design-only?
- What is the exact tech stack?
- What is the current sprint or release boundary?
- Where should new code go?
- Which files must agents read before editing?
- What checks must run before claiming completion?
- What primary flow must be protected?
- Which product boundaries does this task affect?
- Is UI scope in-scope or out-of-scope?

## Status File Requirements

`docs/architecture/STATUS.md` should include:

| Symbol | Meaning |
|--------|---------|
| `Verified` | Source exists and is wired into runtime |
| `Partial` | Source exists but is incomplete, disabled, or not wired |
| `Deleted` | Previously existed, now removed |
| `Design` | Design document only, no implementation |
| `Planned` | Intended work, not current behavior |
| `Gap` | Documentation claims more than code reality |

Every product-local coding session that creates, deletes, restores, or meaningfully changes a module should update `STATUS.md`.

## CLAUDE.md / AGENTS.md Requirements

Agent instruction files should include:

- mandatory workflow for non-trivial tasks
- session start reading order
- quick commands
- architecture entrypoints
- repository role and boundaries
- code conventions
- banned patterns
- verification gate
- Git and PR rules
- links to platform docs when cross-product work is involved
- stability-first, product-boundary, and UI-scope rules

When `CLAUDE.md` and `AGENTS.md` both exist, they must be behavior-equivalent:

- workflow, Git rules, verification gates, safety rules, and cross-product boundaries must match.
- tool-specific command mappings or usage hints may be added.
- one file must not require stronger protection of user changes, verification, or worktree usage while the other weakens or omits those requirements.
- when a behavior rule changes in one file, update the other file too, or make one file an explicit mirror that points to the canonical file.

Do not place secrets, customer data, or long historical changelogs in agent instruction files.

Agent instruction files should also make the workflow executable, not merely descriptive. Include a short required checklist:

1. read this repo's agent context and relevant shared standards
2. run `git status --short --branch` before editing
3. use a topic branch/worktree for non-trivial work, with owner and scope declared
4. scope must state the protected primary flow, affected product boundaries, and UI scope
5. protect primary flows by default; do not trade stability for unrequested feature expansion
6. unless UI is explicitly in-scope, do not change UI while fixing backend, queue, deployment, MCP, provider, data-model, or test issues
7. run targeted verification before claiming completion, and state the stability evidence
8. use PRs for protected branches and wait for required checks
9. after task completion or PR merge, return to the local default branch; if it is clean, fetch/prune and fast-forward it to `origin/<default>`
10. if the default checkout has local-only WIP, default to a clean latest worktree based on `origin/<default>` instead of implicitly overwriting, resetting, or broadly stashing
11. report any remaining local-only WIP and whether the repo ended on a clean latest default branch instead of hiding it

For stronger automation, product repos should add PR templates and branch protection that require validation evidence. Repositories with local `make` targets should expose a small `make check` or `make agent-check` command that agents can run before opening PRs.

### Where a rule must live to hold

Agents reliably re-read only the instruction file that the tool loads on every session. Linked guides, long design docs, and earlier conversation are often dropped after context compaction. A rule that must hold every time therefore lives in one of two places:

- a short, direct line in `CLAUDE.md` / `AGENTS.md`, or
- a lint rule, type check, or test that fails when the rule is broken.

Prefer the second whenever the rule can be checked mechanically; prose loses to a deadline. Where registration is required (routes, feature flags, UI surfaces, API clients), prefer a registry plus a positive assertion over it, or a scaffold that generates the registration, over asking each new file to remember a manual step.

## Cross-Repository Reference Rule

When a repository participates in multi-repository work, its `CLAUDE.md` or
`AGENTS.md` should link to the organization's shared architecture/contract
docs and relevant Agentic SDLC standards (`sdlc.md`,
`vibe-coding-collaboration.md`, `multi-ai-git-workflow.md`, and
`testing-strategy.md`).

## Debt Learning Loop

When an AI coding session discovers or fixes debt:

1. Record or update the debt item in the product repo.
2. Extract the prevention rule if the mistake can recur.
3. Add the prevention rule to the product-local debt protocol.
4. Promote the rule to your shared engineering standards only if it applies across multiple repositories.

## Batch-remediation learning and entrypoint hygiene

Keep mandatory guidance short in one canonical AGENTS/CLAUDE file; an explicit
pointer is preferable to two drifting copies. Load frontend layout/interaction rules
for UI work and execution/transaction/compatibility rules for backend work. Editor
rules use those same sources, not a second hard-coded module inventory.

Record failure → root cause → applicability → prevention rule → regression test →
current status. Product-specific details stay in product guides; promote only
cross-product rules into these standards. Prefer an executable check for a stable
invariant. Existing standards should be extended before creating duplicate guides.
Source/test observations that contradict STATUS are documentation defects to
reconcile; stale prose does not override fresh implementation evidence.

**Projection-driven doc sync**: Before asking a coding agent to update `STATUS.md`
or architecture/API docs on a large repo, extract a deterministic projection first
(`git diff --name-status`, OpenAPI JSON, AST summary, or schema export) and pair
it with `scripts/check-change-sync.py` rather than having the agent blindly scan
the entire repository and trigger `auto-compact` drift.
