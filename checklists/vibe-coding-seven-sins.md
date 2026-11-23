# Vibe Coding Survival & Seven Sins Checklist

**Status**: accepted baseline
**Updated**: 2026-11-20
**Chinese**: [vibe-coding-seven-sins.zh.md](vibe-coding-seven-sins.zh.md)
**Empirical Basis**: [Empirical Findings §2](../docs/empirical-findings.md) (443 real sessions, 8.4B tokens across multi-repo production projects)

> **Core Finding**: Structure is not the enemy of speed — structure is the
> prerequisite for speed. Small disposable projects (`<5K` LOC, 1–6 sessions)
> achieve ~100% success in autonomous mode; large projects (`>10K` LOC, 50+
> sessions) without structure collapse to ~55% and accumulate cross-session
> consistency drift.

---

## 1. Know Your Phase Transition Zone

| Dimension | Safe Zone (Disposable Mode) | Danger Zone (Architecture Mode) |
|---|---|---|
| Codebase size | `<5K` LOC | `>10K` LOC |
| Session count | 1–6 sessions | 50+ sessions |
| Complexity | Single domain | Multi-system integration (DB + Queue + Frontend + Agents) |
| Failure strategy | Regenerate faster than debug | Must root-cause and fix cleanly |
| Required control | Conversational iteration | PRD / Task ID, Git checkpoints, `/compact`, gap analysis, circuit breakers |

## 2. Guard Against the Three Failure Archetypes

- [ ] **Sandbox Wall (~60% of failures)**: Before launching an autonomous session, verify write permissions, network access, and tool availability. Never let an agent loop blindly on permission denials.
- [ ] **Context Window Exhaustion (~25% of failures)**: Enforce a hard **60-message** compaction boundary (failure rate jumps from `<10%` to **35.7%** past 200+ messages). Split planning and execution into separate fresh sessions.
- [ ] **Capability / Filter Ceiling (~15% of failures)**: Do not send complex architecture tasks to models with thinking/reasoning disabled; match tool mode to task shape (short human-in-the-loop surgical edits vs. bounded long-horizon runs).

## 3. Audit for the Seven Deadly Sins

| # | Sin | Failure Pattern | Required Countermeasure |
|---|---|---|---|
| 1 | **Declare Victory, Then Fix Forever** | "Phase Complete" docs appear while basic flows fail; "code exists" mistaken for "code works". | Verify live behavior & integration paths; never trust completion percentage claims. |
| 2 | **Ghost Modules (Dead Code)** | Clean helpers (`pagination.py`, async DB layer, shared types) are created and never wired into real callers. | **"Wire it or delete it"** + **"Show me the caller"**: every new module must have a real caller before session end. |
| 3 | **Cross-Session Frankenstein Architecture** | Session 1 writes `async def`, Session 2 uses sync DB `Session`, Session 3 adds an unused async engine. | Run a single-session consistency check against repo rules before committing; enforce architectural invariants via lint/tests. |
| 4 | **Big Bang Rewrite** | Agent rewrites thousands of lines in one leap, breaking subtle integration points; "fix forward" burns hundreds of messages. | Cap single-PR refactors (target `<500` lines per verifiable step); prefer decisive `git revert` over sunk-cost debugging. |
| 5 | **Too-Real Fake Data** | Fallback handlers return plausible fake model names, metrics, or fixtures instead of failing or reporting unknown. | Forbid silent mock fallbacks in production code; fail explicitly or display `UNKNOWN` / error state. |
| 6 | **Dormant Feature Flags** | Every session adds a `DEFAULT = False` flag; nobody audits what should ship enabled or be retired. | **2-week flag audit**: any flag still `False` after two weeks must be either enabled or removed (full retirement schema in `OpenAgenticSecurity/assurance-contracts`). |
| 7 | **Documentation Progress Illusion** | Polished changelogs and design docs describe *aspirational* state rather than implemented code reality. | Maintain an evidence-backed `STATUS.md`; trust verified code & tool outputs over prose. |

## 4. Mandatory 6-Step Session Loop (for `>1K` LOC Repos)

1. **Context Sync** — Load `STATUS.md`, `VIBE_CODING_CONTEXT.md`, and relevant standard/contract.
2. **Gap Analysis** — Diff design vs. actual code before editing.
3. **Plan-then-Do** — Produce an explicit step plan with zero placeholders (`// TODO`, `"coming soon"`, stub functions); approve before coding.
4. **Scoped Execution** — Execute in small increments with a Git checkpoint before every major change.
5. **Verification** — Run real integration/unit tests and linters (integration tests catch boundary bugs that unit tests miss).
6. **Checkpoint & Compact** — Commit clean scope, update `STATUS.md` / working memory, and trigger `/compact` or open a fresh session before crossing 60 messages.

## 5. High-Signal DOs & DON'Ts

### DO

- [ ] Trigger a **circuit breaker after 3–5 consecutive failures** — stop retrying, inspect root cause, and reset context.
- [ ] Enforce **"Wire it or delete it"** and **"Show me the caller"** for every new utility or abstraction.
- [ ] Prefer **integration tests over isolated mocks** at module boundaries.
- [ ] Use **absolute imports** in deep directory trees so refactors do not silently shatter relative paths.
- [ ] Design cross-cutting invariants (such as `tenant_id` isolation and explicit resource cleanup) from line one.
- [ ] Track loop detection by **`(tool_id, normalized_params_hash)`**, not bare `tool_id`.

### DON'T

- [ ] Never write bare `except Exception: pass` that silences real failures.
- [ ] Never hardcode `localhost` or host-specific paths.
- [ ] Never accept placeholder stubs (`// TODO: implement`) in merged code.
- [ ] Never mix synchronous blocking calls inside `async def` handlers or graph nodes.
- [ ] Never leave cross-session resources (HTTP/LLM/DB/SSH clients) without an explicit `with` / `async with` owner.
- [ ] Never pressure an agent with emotional prompts — supply the exact stack trace and ask for root-cause analysis.

## 6. Four Architectural Disciplines & Model-Upgrade Guardrails

1. **Separate Reasoning from Execution**: Keep LLM planning/decision logic cleanly separated from deterministic I/O and state execution (empirical compounding: structured architecture drove a ~10x gap in messages per 1K LOC, `r = 0.969`).
2. **Explicit Resource Lifecycles**: Whoever creates a client/session/connection owns closing it via context managers.
3. **Protocol over Glue Code**: Replace repetitive bespoke adapters with explicit schemas and protocols to reduce cross-session cognitive tax.
4. **Plan Before Structural Change**: Large architecture changes start in a fresh planning session and land as reversible increments.
5. **Treat every model upgrade as a high-risk release**: Upgrading to a stronger model can still break working workflows via (a) fixed context-compression thresholds clipping fresh tool output, (b) old defensive prompts conflicting with native tool calling, (c) stronger parallel tool calls exposing latent concurrency deadlocks, (d) stricter safety refusals blocking legitimate defensive/security bug fixes, (e) over-exploration exhausting step/rate budgets, (f) IDE/proxy silent fallback to a weaker default model, or (g) stricter schema adherence exposing previously masked ambiguity — always run a fixed regression suite before switching.
