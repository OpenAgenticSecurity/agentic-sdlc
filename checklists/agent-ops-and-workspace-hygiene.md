# Agent Operations, Shared Environments & Workspace Hygiene Checklist

**Status**: accepted baseline
**Updated**: 2026-11-20
**Chinese**: [agent-ops-and-workspace-hygiene.zh.md](agent-ops-and-workspace-hygiene.zh.md)
**Companion Helper**: [`scripts/link-shared-node-deps.mjs`](../scripts/link-shared-node-deps.mjs)

> **Why This Exists**: Multi-worktree AI development fails quietly in
> operational layers nobody writes into feature specs — 10 worktrees cloning
> gigabytes of `.venv` and `node_modules`, forked subagents burning hundreds of
> millions of tokens in an hour, debug commands echoing live secrets, and
> squash-merged base branches silently closing stacked PRs. Every rule below
> comes from a real production or multi-repo incident.

---

## 1. Shared Dependencies Across Git Worktrees (Avoid Disk Bloat)

Running `uv sync`, `pip install`, or `npm install` inside every isolated task
worktree quickly wastes tens of gigabytes and slows every agent session.

### Recommended Setup

- **Python (`uv`)**: Point all worktrees at one shared environment outside the
  worktree directories:
  ```bash
  export UV_PROJECT_ENVIRONMENT="$HOME/workspace/.venv"
  ```
  Run `uv sync` once from the primary repo root; never install per-worktree `.venv/`.
- **Node / Frontend (`Vite`, `tsc`, `ESLint`)**: **`NODE_PATH` does NOT work**
  for Vite, `tsc`, or ESLint — they only resolve packages from local
  `node_modules/`. Use a **lockfile-keyed external store** via
  [`scripts/link-shared-node-deps.mjs`](../scripts/link-shared-node-deps.mjs):
  ```bash
  node /path/to/agentic-sdlc/scripts/link-shared-node-deps.mjs --project-dir ./frontend
  ```
  - Hashes `package-lock.json` + dependency fields + OS/arch/Node ABI into an
    external store (`~/.cache/shared-node-deps/<hash>/`), installs once atomically
    with `npm ci`, and creates a real `node_modules/` in each worktree whose
    package entries symlink to the store.
  - **Copies** `.package-lock.json` instead of symlinking it (prevents `npm`
    from mutating the shared store in place).
  - Keeps tool caches (`.vite`, `.cache`, `.tmp`, `.turbo`, `.next`) local per
    worktree and leaves existing real `node_modules/` installs untouched.
  - **Shared-cache trust boundary**: Share stores ONLY across same-trust-domain
    local worktrees. Never mount a writable shared store across mutually
    untrusted tasks or between candidate agent execution and a protected
    verifier; pass `--read-only-store` and `--ignore-scripts` when hardening
    untrusted lockfiles.

### Three Real Shared-Environment Traps to Guard Against

- [ ] **Trap 1 — Silent wrong-checkout execution**: Inside a new worktree, bare
  `uv run pytest` can fall back to system Python whose `sys.path` points to the
  **primary checkout**, silently testing unedited code! Verify with:
  ```bash
  python -c "import your_pkg; print(your_pkg.__file__)"
  ```
  Confirm the printed path is inside your **current worktree**, not the main checkout.
- [ ] **Trap 2 — Cross-repo package downgrades & ghost type stubs**: Installing
  Repo A's hash-pinned requirements into a multi-repo shared `.venv` can silently
  downgrade `pytest`/`packaging` for Repo B or inject extraneous `types-*` stubs
  that cause false `mypy` errors. Prefer isolated per-lockfile stores (or
  targeted single-package installs) and never mask typing regressions.
- [ ] **Trap 3 — Local `.env` leaking into unit tests**: Local dev flags inside
  `.env` (e.g. background-worker toggles) get loaded via `load_dotenv`, causing
  local-only test failures while CI passes. Isolate test runs with explicit env
  overrides (`env -u VAR` / `FLAG=0`).

---

## 2. Workspace Runtime Scratch (`tmp/`) & Safe Disk Reclamation

Keep agent-generated logs, long command captures, and intermediate reports
**outside repository Git histories** (for example,
`<workspace>/.agent-scratch/{logs,tasks}/`) so repos stay clean and scratch is
never accidentally committed.

- [ ] **Never write secrets, credentials, customer data, or `.env` values into scratch**.
- [ ] **Use a shallow two-level task shelf (`tasks/<type>/<scope>/<task>/`) and leave a 1-line-first `SUMMARY.md`** in any reusable scratch task folder
  (outcome, files/PRs touched, verification command run) so future sessions can
  index it without opening dozens of files.
- [ ] **Safe derived-artifact cleanup rules** (before running any `rm -rf` on
  `.venv` / `node_modules` / `__pycache__` / `build` / `dist`):
  1. **Never descend into a `.git` repository clone** — a repo's build/dist or
     working tree may hold unpushed work.
  2. **Skip directories touched within the last 24 hours** so cleanup cannot
     yank dependencies out from under an active agent session.
  3. **Audit buried Git clones read-only first**: classify each clone as `RISKY`
     (uncommitted changes, unpushed commits, stashes, mid-merge/rebase, or no
     remote) vs `SAFE` before deleting anything.
  4. **Triage by contents, never by directory name**: a `mktemp`-looking folder
     may hold the only copy of real deliverables or credentials.

---

## 3. Periodic Audit Archives (`audit/` + `EVIDENCE.md`)

Separate **periodic audit conclusions** (durable, comparable assets under
`<workspace>/audit/<YYYY-MM-DD>-<topic>/`) from **audit process artifacts**
(disposable raw logs and traces in scratch).

- [ ] **Never freeze full repository copies into an audit directory**: Anchor
  every finding with `file:line` + exact 40-char `commit SHA`. Real comparison:
  anchoring by commit kept a 5-repo audit at **240 KB**, whereas freezing 6 repo
  copies consumed **7.8 GB** (~30,000x larger) with zero extra traceability.
- [ ] **Require `EVIDENCE.md` in every audit folder**: Record scope, exact
  commit baseline, reproducible commands to re-verify findings, known gaps, and
  next-round pickup items. Once `EVIDENCE.md` is solid, gigabytes of raw process
  scratch can be deleted safely.
- [ ] **Compare round-over-round**: Every new audit round reads the prior
  round's `EVIDENCE.md` and classifies findings as **Closed**, **Persisting**,
  or **New** — an audit that cannot be compared to the last round is a first
  audit every time.

---

## 4. Subagent Token Budgets & Concurrency Guardrails

Nested forked subagents that inherit full parent transcripts can burn hundreds
of millions of tokens in a single hour (observed incident: ~260M tokens in one
hour from repeatedly copying a 14 MB transcript 8+ times) and trigger API relay
`499` / concurrency rejections.

- [ ] **Never spawn `fork`-style subagents** that copy full conversation history.
  Pass a minimal, self-contained prompt: absolute worktree path, branch, exact
  file list, verification command, done criteria, and prohibitions.
- [ ] **Forbid nested subagents**: Explicitly state *"do not spawn subagents"*
  in every worker prompt.
- [ ] **Cap parallel workers (`<=3`)** and do not split work one agent can finish
  serially; keep subagent reports brief and structured.
- [ ] **Handoff instead of dragging a bloated session**: When context grows
  large or when switching across frontend/backend/sibling repos, write a
  concise `HANDOFF.md` using [`handoff.template.md`](handoff.template.md)
  (goal, done, remaining, API/schema/config contract changes, verification
  commands) and continue in a fresh session.
- [ ] **Update cross-repo changes in dependency order**: Land shared protocols
  and libraries first, consumer services second, and shared platform standards
  last so downstream verification runs against real merged contracts.

---

## 5. Six Hard-Won Debugging, Git & Governance Traps

- [ ] **Never echo secret values while debugging**: Test for existence ONLY
  (`[ -n "${API_TOKEN:-}" ] && echo present` or `env | cut -d= -f1`). Never run
  `echo "$API_TOKEN"` or `env | grep TOKEN` — printing a live token to terminal
  forces immediate revocation. Use `env -u VAR` to isolate failing tests.
- [ ] **Prevent exception messages from leaking sealed data**: When scripts run
  against restricted/sealed datasets, a parsing error (such as `urlsplit
  ValueError`) can echo raw input snippets to stdout. Print **aggregate counts
  and exception class names only** to agent-visible stdout; test with synthetic
  fixtures.
- [ ] **Avoid GitHub stacked PR base branches under squash-merge**: When PR #1
  is squash-merged with automatic branch deletion, GitHub **auto-closes**
  stacked PR #2 and refuses `gh pr edit --base main` on closed PRs. Always base
  every PR on `main`; after PR #1 merges, `git fetch` and `cherry-pick`/rebase
  PR #2 onto fresh `origin/main`.
- [ ] **Verify committed Git objects, not just the working tree**: Running
  `git add` *before* regenerating a digest/bundle makes local `make check` pass
  against uncommitted working-tree bytes while CI fails on the stale committed
  object. Verify attested artifacts against `git show HEAD:<path>` and a clean
  `git status`.
- [ ] **Never trust compressed/filtered CLI wrappers for factual counts**:
  Token-saving wrappers that truncate output (e.g. turning 2,113 commits into 50
  lines in `git log | wc -l`) silently corrupt audit counts. Always use exact
  unfiltered primitives (`git rev-list --count HEAD`, raw commands) for facts.
- [ ] **Asymmetric gate rule & cursor safety**:
  - **Never admin-bypass a PR that loosens a security/validation gate**, and
    never admin-merge an approval-gated plan whose rules retire the plan on
    unapproved merge (causing an endless regeneration treadmill).
  - In poll/monitor loops, **advance the dedup cursor ONLY after downstream side
    effects succeed** — never on parse-success alone (prefer retryable
    at-least-once over silent event loss).
