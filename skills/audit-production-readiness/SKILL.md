---
name: audit-production-readiness
description: Use when auditing whether a repository or AI-built system is truly production-ready versus demo-grade across architecture, design, functionality, performance, and security, or when running a full-repo implementation audit before launch.
---

# Five-Dimension Production Readiness Audit (Standalone Skill)

> **Non-Authoritative Projection**: This skill produces a grounded, read-only
> engineering assessment. It cannot waive production risks, certify security
> compliance, or substitute for live load/penetration testing.

## 1. Honesty Protocol (Violating Any Rule = Audit Failure)

1. **Assume defects exist**: Success is measured by verified findings, not praise.
2. **No ungrounded praise**: Never state a positive property without `file:line`
   evidence or measured output.
3. **Tag every claim with its evidence source**:
   - `[Fact]` — directly read from code (`path:line` + key snippet)
   - `[Measured]` — observed via live/local command (exact command + output)
   - `[Inference]` — structural deduction (explicit reasoning chain)
   - `[Unknown]` — insufficient material; never guess or fill with generic advice
4. **Attach confidence + falsifier**: State `High / Medium / Low` confidence and
   one sentence on what evidence would falsify the claim.
5. **Strictly read-only & zero secret leakage**: Never modify or commit to the
   audited repo. Never record secret, token, or password values — record key
   names, counts, and permission bits only.

## 2. Seven Evidence Disciplines (High-Frequency Audit Traps)

1. **Trace negative claims to the construction point**: Before claiming *"X has
   no timeout / auth / cap / caller"*, trace caller → constructor → DI /
   middleware / config. `grep` returning zero hits is NOT proof.
2. **Verify data liveness (production writer exists)**: For every guard, budget,
   or metric that reads field `F`, locate the **production writer** (`file:line`).
   A guard reading a field that is only populated in tests or remains `0` on the
   canonical path is a dead control — file it as a defect.
3. **Trace claimed features from live entrypoints**: A `STATUS.md` checkmark or
   closed issue proves nothing if live HTTP/CLI/worker entrypoints never reach
   that code path ("unwired claim").
4. **Reproducible counts & consistent denominators**: Every count, ratio, or
   density must carry the exact unfiltered command and scope (`git ls-files` vs
   `find` drift invalidates comparisons).
5. **No performance verdicts without measurement**: Without `[Measured]` data,
   label findings `[Unverified Hypothesis]` and provide the minimal measurement
   probe.
6. **Check defaults across all three layers**: Never write *"off/on by default"*
   from code alone — check (a) code/Settings default, (b) shipped deployment
   templates (`.env.example`, Helm/Compose/IaC), and (c) live deployed value
   (mark `[Deployment-Dependent]` if live access is unavailable). Template edits
   do not prove existing environments updated.
7. **Write arithmetic out & verify term semantics**: Write explicit inequalities
   (e.g. `10700 + 300 = 11000 > 10800`) and confirm at `file:line` whether each
   term is per-call, shared within one execution, or cumulative across turns.

## 3. Coupling, Fix & Deployment Disciplines

- **Map neighboring limits before recommending a cap**: For timeouts, retries,
  pools, concurrency, iterations, or token budgets, list every neighboring limit
  on the same resource and derive the fix from their inequality — never suggest
  an isolated magic number.
- **State fix preconditions & failure modes**: Specify when a recommended fix
  stops working (e.g. *"run as non-root — ineffective if mounted token files are
  `0644` or `/proc/1/environ` is readable by the same UID"*) plus blast radius
  (estimated files, migrations, contracts).
- **Mark deployment-dependent severity**: Tag findings that hinge on cluster,
  proxy, or storage config as `[Deployment-Dependent]` and include a read-only
  probe mapping `Output A -> Severity X; Output B -> Severity Y`.
- **Subagent verification**: Re-verify all high-severity `[Fact]` findings,
  negative claims, and counts returned by subagents. Mark unverified items
  `[Unverified Subagent Inference]`; mark failed/blocked dimensions
  `NOT_EVALUATED` (never assign a score).

## 4. Adversarial Dual-Hypothesis Verdict (Debate Before Scoring)

Before scoring, write the strongest evidence-backed case for both hypotheses:
- **H1**: *"Under the stated deployment assumptions, this implementation can
  support production scale and ongoing evolution."*
- **H2**: *"This is demo-grade; real load or requirement changes will force a
  rewrite."*

Rule clearly between H1 and H2 using verified evidence — no hedging.

## 5. Audit All Five Dimensions (Language-Agnostic)

1. **Architecture**: Layer boundaries & cycles, swap blast radius (DB/LLM/tools),
   end-to-end data flow & data liveness, state ownership & crash/deploy recovery,
   horizontal scaling single points (in-memory state, sticky sessions, local disk).
2. **Design**: API & error model consistency, abstraction/duplication density,
   type strictness (typed domain models vs untyped dicts/`any`), error boundary
   discipline, 12-factor config & startup coupling invariants.
3. **Functionality**: Claimed-vs-live feature reality table, vibe-coding residue
   (mocks, dead code, test-only production functions), edge cases (empty state,
   idempotency, retry/cancel), agent loop closure (if applicable), test assertions
   vs smoke-only tests.
4. **Performance** (`[Unverified Hypothesis]` unless `[Measured]`): Latency
   breakdown, frontend render/bundle/virtualization, backend N+1 / blocking I/O /
   pool ledger, LLM context/token accounting liveness, first concurrency bottleneck.
5. **Security**: Secret exposure & runtime `/proc`/env boundary, endpoint auth
   coverage (resolved via dependency graph, not naive grep), injection surfaces
   (SQL/shell/XSS/template/SSRF), and AI/agent attack surface (prompt injection,
   tool privilege boundaries, HITL gates on destructive actions, tenant isolation).

## 6. Output Structure & Round-Over-Round Continuity

Emit: (1) Stated Deployment Assumptions & Exact Commit SHA Baseline, (2) H1/H2
Verdict (`<= 200` words), (3) 5-Dimension Scorecard (`1–5` with one-line anchored
evidence, or `NOT_EVALUATED`), (4) Severity-Ranked Findings (dimension, source
tag, evidence, confidence, falsifier, fix with preconditions & blast radius),
(5) Feature Reality Table, (6) Reproducible Metrics Table, (7) Deployment &
Measurement Probe List, (8) Open Product/Ops Decisions, (9) Delta vs Prior Round
(`Closed` / `Persisting` / `New` from prior `EVIDENCE.md`), (10) Uncovered Scope
(`does_not_prove`), and (11) Self-Challenge (top 3 ways this audit could be wrong
and how to falsify each).

*Optional full checklist*: `https://github.com/OpenAgenticSecurity/agentic-sdlc` (`checklists/production-readiness-audit.md`).
