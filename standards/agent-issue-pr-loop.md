# AI Agent Issue-to-PR Loop Standard

**Status**: accepted baseline
**Updated**: 2026-11-20

## Goal

This standard turns AI coding-agent discovery, improvement planning, local implementation, PR merge, and issue closure into an auditable loop. It applies to human and AI collaboration across any adopting repository or multi-repo workspace.

The loop is not meant to create process overhead. It ensures actionable work is not buried in chat, local notes, or PR prose, and it prevents AI agents from turning unowned, unaccepted, or unverified ideas directly into code.

## Standard Loop

1. **Discover or plan**: an agent finds a bug, security gap, tech debt item, documentation drift, missing test, capability gap, or executable improvement plan.
2. **Route ownership**: file the issue in the owning repository; cross-repo work gets a parent issue and per-repo child issues.
3. **Search and file**: search for an existing issue first; update or reference it when one exists, otherwise create a new issue.
4. **Freeze scope**: the issue states in-scope, out-of-scope, acceptance criteria, verification plan, risk, dependencies, and owner.
5. **Design gate**: when a change crosses repositories, alters shared contracts, or changes security boundaries, open a design/plan PR before implementation; small single-repo fixes may go directly to implementation.
6. **Claim visibly**: before editing, publish or update the managed issue claim comment defined in [multi-ai-git-workflow.md](multi-ai-git-workflow.md) (or via `scripts/agent-claim.py`).
7. **Isolated development**: follow [multi-ai-git-workflow.md](multi-ai-git-workflow.md): one task, one branch, one worktree, one owner.
8. **Implement and verify**: change only in-scope files, run the verification commands from the issue or plan, and record fresh output.
9. **Link the PR**: the PR references the closing or related issue, plan/RFC PR, dependency PRs, verification evidence, risk, and rollback.
10. **Review and merge**: merge only after required checks and owner review pass; default to squash merge.
11. **Close the issue**: close only after acceptance criteria are met, verification evidence exists, docs are synchronized, and dependencies are resolved or superseded.
12. **Sync and hand off**: after merge, return touched repos to clean latest default branches; handoff reports the PR URL, merge state, issue state, verification commands, and local checkout state.

## When an Issue Is Required

An AI agent or human must create or update a GitHub issue before handoff when they discover:

- Reproducible bugs, error paths, silent failures, data corruption, or user-visible failures.
- Security gaps, permission boundaries, secret handling, customer evidence, remote execution, or audit problems.
- Tech debt that affects primary flows, deployment, testing, migrations, contracts, or future development.
- Documentation drift that can mislead cross-repo decisions, sales, delivery, or agent tasks.
- Missing tests that leave fixed or shipped behavior without regression protection.
- Improvement plans with a clear owner, scope, acceptance criteria, and verification plan.
- Out-of-scope but actionable findings discovered during the current task.

If GitHub is unavailable, the handoff must include the target repository, proposed title, full issue body, labels, duplicate-search result, and why the issue could not be opened.

## When Not to File an Issue

Do not force an issue for:

- Early ideas from discussion that lack clear impact, owner, or acceptance criteria.
- One-off local experiments, temporary investigation notes, or unreproducible observations.
- Tiny mechanical fixes already completed within the current PR scope, fully explained in the PR body, and not needing follow-up tracking.
- Personal style preferences that do not violate existing standards.
- Problems already covered by an existing issue; update or reference the existing issue instead of duplicating it.

Avoiding an issue is not permission to hide actionable work in a final answer, PR description, or local todo.

## Issue Quality Bar

Implementation issues must include at least:

- Owning repository and discovery source.
- Background, impact, and current behavior or evidence.
- In-scope and out-of-scope.
- Proposal or proposed approach.
- Observable acceptance criteria.
- Runnable verification plan.
- Risk, dependencies, and related docs.

Improvement-plan issues must also include owner, phases, stop condition, and which parts must not be treated as GA, sales commitments, or default customer experience before validation.

## PR Quality Bar

A PR that closes or advances an issue must include:

- `Closes #N`, `Fixes #N`, or `Related #N`.
- Repository-qualified references for cross-repo issues, such as `org/service-a#12`.
- Commands actually run, not commands intended to be run later.
- Whether docs, contracts, status, and context files were synchronized.
- Risk, rollback, dependency order, and remaining follow-up.
- For AI-assisted work: agent/tool, branch owner, and worktree.

A PR creation link such as `/pull/new/...` is not an actual PR URL and must not be reported as one.

## Issue Closure Rules

Close an issue only after:

- Its acceptance criteria are satisfied, or the issue is explicitly updated as superseded.
- The closing PR is merged, or a closing comment includes auditable verification evidence.
- Required docs are updated in the correct authority location.
- Cross-repo child issues are closed, moved, or clearly marked blocked.
- Out-of-scope work was not silently absorbed.
- The handoff reports whether the local repository returned to a clean latest default branch.

When closing without implementation, use `superseded by #N`, `duplicate of #N`, or `won't do because ...`; do not close silently.

## Making Adopting Repositories Comply

Every adopting repository should expose these entry points and automation signals:

- `AGENTS.md` and `CLAUDE.md` require compliance with this standard and stay behaviorally equivalent.
- `.github/ISSUE_TEMPLATE/issue.md` and `epic.md` capture scope, acceptance criteria, verification plan, owning repository, and dependencies.
- `.github/pull_request_template.md` requires issue links, verification, risk/rollback, docs updates, and AI assistance.
- At least one CI workflow runs repository checks on the exact PR head revision.
- `Makefile` provides `agent-check` (or an equivalent local command) for agents before handoff.
- Repo-local `docs/VIBE_CODING_CONTEXT.md` and `docs/architecture/STATUS.md` describe implementation reality, primary flows, and verification entry points.

Run the bundled compliance script against any repository:

```bash
bash scripts/check-product-compliance.sh --profile L1 /path/to/your-repo
```

Or use `make product-compliance REPO=/path/to/your-repo`. This check does not replace code review, but it exposes repositories that have not wired the loop into their entry files, templates, and local checks.

## Related Standards

- Multi-human and multi-AI worktree practice & managed claims: [multi-ai-git-workflow.md](multi-ai-git-workflow.md).
- Agent context and status truth requirements: [ai-coding-context.md](ai-coding-context.md).
- Lifecycle and delivery gates: [sdlc.md](sdlc.md).
- Testing and verification rules: [testing-strategy.md](testing-strategy.md).
