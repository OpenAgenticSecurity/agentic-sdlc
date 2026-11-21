# How Agentic SDLC Fits Into a Modern AI Coding Workflow

**Status**: adoption architecture guide
**Updated**: 2026-11-21
**Chinese**: [workflow-integration.zh.md](workflow-integration.zh.md)

`OpenAgenticSecurity/agentic-sdlc` does **not** ask you to replace Claude Code,
Cursor, Codex, `superpowers`, your linter, or GitHub Actions. It sits around
your existing inner-loop tools as the **outer verification & safety boundary**.

---

## 1. The 4-Layer AI Coding Toolchain & Pain-Point Map

| Toolchain Layer | Common Tools Today | Recurring Failure Mode Without Outer Guardrails | How `agentic-sdlc` Solves It |
|---|---|---|---|
| **1. Spec & Context** | GitHub Issues, Linear, Plan Mode, `superpowers`, Spec-Kit | Cross-session drift; agents build on deleted modules or ignore repo commands; large edits skip planning | Unified root `AGENTS.md` (with non-trivial task gate & stack slots) + thin `@AGENTS.md` `CLAUDE.md` + `STATUS.md` + `handoff.template.md` |
| **2. Inner Coding Loop** | Claude Code, Cursor, Codex, Windsurf, MCP | Parallel agents commit directly to `main`; agents ship `except: pass`, hardcoded fallback secrets, SSRF, or hallucinated packages | `multi-agent-git-flow` + `secure-vibe-coding` Skills; deterministic local Git hooks (`workspace-git.py`); optional L2 Rust hooks via `deps` & `sealed-data` |
| **3. Local Verification** | `ruff`, `eslint`, `tsc`, `pytest`, `vitest`, `go test`, `cargo test`, Playwright | Agents test only at P50; `0 tests collected` or `--passWithNoTests` exits green; CI/unit tests miss 93% of frontend bugs & 95% of backend perf bugs | `done-claim-verify` & `audit-pr-diff` Skills; zero-dep polyglot `audit-repo.py`; starter Playwright & backend contract gates (`examples/`) |
| **4. PR, CI & Production Gate** | GitHub PRs, GitHub Actions, AI Review Bots, GitHub Rulesets | Self-attesting PRs weaken their own tests/CI; Rulesets allow post-approval pushes or spoofable `integration_id: null` checks; demo-grade systems ship as "production" | Fail-closed CI templates (Python/TS/Rust/Go/Java), Reusable `action.yml`, `CODEOWNERS`, `github-ruleset.import.json`, `observe-github-ruleset.py`, and 5-dimension `audit-production-readiness` Skill |

---

## 2. A Real Day with Coding Agents: 5 Exact Hook Points

```text
[1. Pick Up Task]     Issue / Linear -> clean worktree from origin/main
      ├─ Hook 1: AGENTS.md + STATUS.md + multi-agent-git-flow Skill
      │          + workspace-git.py pre-commit/pre-push hook (blocks direct main commits)
      ▼
[2. Plan & Code]      Claude Code / Cursor / Codex (+ optional superpowers)
      ├─ Hook 2: Non-trivial task gate (>3 files / >50 lines -> plan + failing test first)
      │          + secure-vibe-coding Skill (optional L2: `deps` PreToolUse hooks)
      ▼
[3. Before "Done"]    Agent prepares to claim "fixed / passing"
      ├─ Hook 3: done-claim-verify + audit-pr-diff Skills
      │          -> 4 Fake-Done breakpoints, DoneClaim + does_not_prove[], file:line audit
      ▼
[4. Open PR & CI]     GitHub PR + Actions
      ├─ Hook 4: Fail-closed CI template + Reusable `action.yml` (`audit-repo.py`)
      │          -> 40-char Action SHA pins, multi-language traps, OAS-* Rule IDs in review
      ▼
[5. Merge & Launch]   GitHub Merge Boundary -> Production Readiness
      └─ Hook 5: github-ruleset.import.json + CODEOWNERS + observe-github-ruleset.py
                 + audit-production-readiness Skill (5-dimension H1/H2 audit before release)
```

---

## 3. Progressive Adoption Ladder (Don't Adopt Everything on Day 1)

| Stage | Time | What You Actually Do |
|---|---|---|
| **0. Try It Read-Only** | 10 sec | Run `python3 scripts/audit-repo.py /path/to/your-repo --github` (zero `pip install`, writes nothing). |
| **1. Solo Daily Driver** | 1 min | Install the 6 language-agnostic Skills globally into Claude Code / Cursor / Codex. |
| **2. Repo Baseline (`L0`)** | 5 min | Run `scripts/bootstrap.sh --profile L0 --target <repo>` (adds unified `AGENTS.md`, thin `@AGENTS.md` `CLAUDE.md`, `STATUS.md`, `.gitignore`, fail-closed `make agent-check`). |
| **3. Team CI (`L1`)** | 20 min | Add `--profile L1 --ci <python\|node-ts\|rust\|go\|java>`, add the 4-line `action.yml` audit step, and enable `workspace-git.py guardrails --apply`. |
| **4. Governed Production (`L2`)** | 1 hour | Import `github-ruleset.import.json`, configure real `CODEOWNERS`, audit live Rulesets via `observe-github-ruleset.py`, run `audit-production-readiness` before launch, and optionally add `deps` / `sealed-data`. |
