---
name: bootstrap-agentic-sdlc
description: Use when a repository has no AGENTS.md, STATUS.md, pull request template or CI gate for coding agents, or when asked to set up, adopt or bootstrap OpenAgenticSecurity agentic-sdlc (profile L0, L1 or L2) in an existing repository.
---

# Bootstrap Agentic SDLC into a Repository (Standalone Skill)

> **Non-Authoritative Projection**: This skill scaffolds ergonomic governance
> files and templates. It cannot waive tests, weaken branch protection, or
> authorize merges. Real enforcement lives outside the prompt window (local Git
> hooks, `deps`, and protected GitHub Rulesets).

## Procedure

1. **Choose target profile** (`L0` solo baseline, `L1` team workflow, or `L2`
   governed + `deps` carrier). Default to `L0` unless requested otherwise.
2. **Check Git safety first**: Run `git status --short --branch`. Work on a
   clean topic branch or isolated worktree based on `origin/<default>`. Never
   commit directly on `main` or overwrite unowned local changes.
3. **Inspect the repository's REAL stack first**:
   - Read `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Makefile`,
     `.github/`, and any existing `AGENTS.md`, `CLAUDE.md`, `STATUS.md`, or
     `.gitignore`.
   - Record ONLY real, runnable lint, typecheck, test, and security-scan
     commands — zero invented commands or placeholders.
4. **Scaffold safely (NEVER silently overwrite existing files — propose a
   minimal merge if a file already exists)**:

### L0 — Solo Baseline (Always Included)

- **`.gitignore`** (append idempotently if missing):
  ```gitignore
  # Agentic SDLC multi-tool worktree namespaces
  .worktrees/
  worktrees/
  .claude/worktrees/
  .cursor/worktrees/
  .codex/worktrees/
  ```
- **`AGENTS.md`**: Session start (`docs/VIBE_CODING_CONTEXT.md`,
  `docs/architecture/STATUS.md`, `git fetch --prune origin`), worktree isolation
  rule, scope declaration, Secure-by-Default Coding Rules (fail-closed auth/
  tenant isolation, parameterized queries, no `shell=True`/SSRF/path-traversal/
  ReDoS, zero hardcoded fallback secrets, anti-slopsquatting, negative security
  test required on security diffs), and exact real verification command(s). If
  the repository has no single check command yet, add a `make agent-check`
  target that wraps the real lint, typecheck and test commands (propose a diff
  rather than rewriting an existing `Makefile`).
- **`CLAUDE.md`**: Explicit behavior-equivalent mirror pointing to `AGENTS.md`
  with the same quick checklist (never weaker than `AGENTS.md`).
- **`docs/architecture/STATUS.md`**: Module Reality Table populated ONLY from
  verified source files using statuses `Verified` / `Partial` / `Deleted` /
  `Design` / `Planned` / `Gap`.
- **`docs/VIBE_CODING_CONTEXT.md`**: 2-minute working memory (what this repo
  does, protected primary flows, real tech stack, verification entrypoint, UI
  out-of-scope default).
- **`.github/pull_request_template.md`**: Summary, In/Out/UI Scope, Issue Links
  (`Closes/Fixes/Related`), Security & Negative-Test Check, Exact Verification
  Commands Actually Run (plus unverified/`NOT_RUN`), Risk & Rollback, and AI
  Assistance (tool, branch owner, worktree).

### L1 — Team Workflow (Additive over L0)

- **`.github/ISSUE_TEMPLATE/{config.yml,issue.md,epic.md}`**: Require Owning
  Repository (filled with this repo's real `<owner>/<repo>`), Scope (in/out),
  Acceptance Criteria, Runnable Verification Plan, Risk & Rollback, and
  Dependencies.
- **`.github/workflows/candidate-gates.yml`**: Pin Actions to 40-char commit
  SHAs, set `permissions: contents: read` and `persist-credentials: false`,
  check out `${{ github.event.pull_request.head.sha || github.sha }}`, assert
  exact SHA, set up the real language runtime, label the job explicitly
  `candidate/advisory` and `not self-attesting`, and run `make agent-check`.
- **`Makefile`**: Confirm the single `agent-check` target runs `git diff --check`
  plus the real lint/type/test suite (missing tools must exit non-zero, never
  green skip), because the L1 workflow calls it.

### L2 — Governed Engineering (Additive over L1)

- **`.github/CODEOWNERS`**: Protect `*`, `.github/`, `Makefile`, `AGENTS.md`,
  `CLAUDE.md`, `scripts/`, and security-critical paths using verified team or
  maintainer handles (warn the user if a GitHub org team does not yet have write
  access).
- **GitHub Branch Ruleset on `main`**: Require PRs (`>=2` approvals on
  enforcement surfaces), code-owner review, `dismiss_stale_reviews_on_push`,
  `require_last_push_approval`, exact `required_status_checks`, and zero
  unconditional (`always` / `exempt`) bypass actors.
- **Optional local carrier (`deps`)**: If the `deps` CLI is installed, offer to
  run `deps aac init .`, `deps agent-hook install . --host claude --host-version
  "$(claude --version)" --enforce` (Codex: `--host codex --with-mcp`),
  `deps security-audit .`, and `deps agent-verify . --receipt .deps/receipt.json`.
  For sensitive datasets, offer `sealed-data seal` if `sealed-data` is installed.

## Mandatory 4-Point Post-Bootstrap Verification

1. Execute the real verification command written in `AGENTS.md` and report exact
   command + exit code (confirm no `0 tests collected` or green `skip`).
2. Confirm every `Verified` entry in `docs/architecture/STATUS.md` exists in
   actual source code.
3. Confirm `AGENTS.md` and `CLAUDE.md` are behaviorally aligned.
4. Confirm `.gitignore` excludes all multi-tool worktree namespaces.

*Optional full templates & reference scripts*: `https://github.com/OpenAgenticSecurity/agentic-sdlc` (`BOOTSTRAP.md`, `profiles/`, `scripts/bootstrap.sh`).
