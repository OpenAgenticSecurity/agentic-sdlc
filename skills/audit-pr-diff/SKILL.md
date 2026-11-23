---
name: audit-pr-diff
description: Use when asked to review, audit or sanity-check a branch diff or pull request before merge, especially AI-generated changes to frontend, backend, database, worker, auth or CI code.
---

# Audit PR Diff with Empirical & Security Checklists (Standalone Skill)

> **Non-Authoritative Projection**: Findings start as **candidate findings**
> until verified against exact source, callers, git history, and tests.

## Step 1 — Ground on Exact Diff & Full Context

1. Run `git status --short --branch` and inspect changed files via
   `git diff --name-only origin/<default>...HEAD` (or `git diff --name-only` for
   uncommitted work).
2. Read the full surrounding files, callers, and related tests for every
   suspect line — never judge from a diff hunk alone.

## Step 2 — Audit Across Applicable Zones

### Zone A — Vibe Coding Seven Sins (Always Check)
- **Ghost modules**: Every newly created helper/endpoint/setting has a real
  production caller/reader ("wire it or delete it").
- **Fake data / silent placeholders**: No hardcoded demo fixtures, `// TODO`
  stubs, or `?? 0` / `|| []` turning read errors into plausible values.
- **Cross-session drift**: New code matches repo patterns (e.g. no sync DB
  inside `async def`, no 2nd copy of a local workaround instead of fixing the
  shared layer).
- **Dormant flags / big-bang rewrites**: Temporary flags have expiry & removal
  issue; refactors are bounded and reversible.

### Zone B — Secure Vibe Coding (Any Auth / Data / I/O / Deps / CI / LLM Diff)
- **Fail-closed auth & tenant isolation**: Missing/invalid tokens, unknown
  roles, or errors return `401`/`403`; every DB query filters by server-side
  authenticated tenant/owner (anti-IDOR); no bare `except Exception: pass`.
- **Safe sinks**: Parameterized SQL only; `subprocess` with arg lists
  (`shell=False`); canonical `Path.resolve()` containment rejecting `..` and
  escaping symlinks; SSRF defense (`https`, block private/loopback/metadata
  `169.254.169.254`, no implicit redirects, timeouts + size cap); no `pickle` /
  unsafe `yaml.load` / raw HTML injection; linear-time regexes + length caps.
- **Secrets & crypto**: Zero hardcoded fallback secrets
  (`os.getenv("SECRET", "dev")`); no secrets in logs/errors/DB/prompts; no
  custom crypto, static IVs, `random` for tokens, or `verify=False`; use AEAD
  and constant-time comparison (`hmac.compare_digest`).
- **Supply chain**: Verify any newly added package exists (anti-slopsquatting)
  and pin versions/hashes; pin GitHub Actions to 40-char SHAs.
- **Mandatory negative security test**: Verify at least one test proves an
  invalid/malicious input is rejected (`401`/`403`/`ValueError`).

### Zone C — Frontend 454-Bug Patterns (If Touching UI/TS/React)
- **Plausible fake values**: Distinguish `loading`, `error`, and `actually empty`
  (never share `[]`); one authoritative field per displayed meaning; no silent
  truncation of long security/log content.
- **Unasserted cross-layer edge**: Disabled features hidden in UI, blocked on
  direct route, AND rejected (`403`/`404`) by backend; single bad record must
  not crash whole view.
- **Off-happy-path state**: Session/auth switch clears cache; cancel/stop/
  disconnect/reconnect tested; non-idempotent POST never auto-retried.
- **Shared layer & scale**: Fix 2nd occurrence in shared HTTP client/layout
  (do not mock `FormData`/transport layer under test); stable `computeItemKey`
  on virtual lists; no O(n²) streaming Markdown re-parses or nested scroll traps.

### Zone D — Backend 8-Class Performance Traps (If Touching Backend/DB/Workers)
- **DB & pool**: Paginated lists + FK/composite indexes; no N+1 (disable implicit
  lazy loading such as `lazy="raise"` or enforce a query-budget test); connection
  pool ledger across processes; rollback before writing failure state; 64-bit
  `duration_ms`.
- **Event loop & blocking I/O**: Never call synchronous DB/cache/file I/O on an
  async event loop (e.g., sync DB session inside `async def` or blocking calls on
  Node/Tokio event loops) or hold a DB connection across remote/LLM awaits; test
  locks on the real production DB engine.
- **Timeouts, idle & Agent loops**: `soft < hard < visibility_timeout`; never
  swallow soft-timeout signals (e.g. `SoftTimeLimitExceeded` / context cancel);
  `<60s` periodic tasks use a lightweight `EXISTS` probe and skip result-store
  writes; hard caps on turns/tokens/wall-clock + loop breaker on
  `(tool, canonical_args_hash)`.
- **3-layer config defaults**: Never judge a setting from code defaults alone —
  verify code default, shipped deployment template (`.env.example`/Helm/Compose),
  and live deployed value.

### Zone E — Enforcement Surfaces, Reward Hacking & IaC Safety (Non-Self-Attesting)
- If diff touches `.github/`, `Makefile`, `AGENTS.md`, `CLAUDE.md`, `.claude/`,
  `.cursor/`, `.vscode/`, `.mcp.json`, `CODEOWNERS`, schemas, checkers, or
  tests: flag that candidate CI is **not self-attesting** and requires
  independent mechanism review + planted-violation check (`0 tests collected`
  or `skip` != pass).
- **Anti-Reward-Hacking**: Verify the diff did not delete/weaken failing test
  assertions, insert `# noqa`/`eslint-disable`/`@ts-ignore`/`.skip` to silence
  gates, write tautological tests that cannot fail, or hardcode test-specific
  outputs.
- **Instruction/CI/IaC poisoning**: Check instruction files for hidden Unicode
  or endpoint overrides, CI workflows for untrusted `pull_request_target` /
  `title`/`body` interpolation, and shared IaC modules (`terraform/modules/`)
  for missing `prevent_destroy` or 0-minute staging bypasses.

## Step 3 — Optional Local Tools & Grounded Report

- When available in the repo, run `python3 -S scripts/audit-pr-diff.py --base origin/main --head HEAD` and `python3 -S scripts/audit-repo.py .` as deterministic pre-checks.
- Report every finding with exact `file:line`, separating **Fact confidence**
  (verified code) from **Impact confidence** (reachability under real controls),
  and explicitly list what was `NOT_RUN` / `does_not_prove`.

*Optional full checklists*: `https://github.com/OpenAgenticSecurity/agentic-sdlc/tree/main/checklists`.
