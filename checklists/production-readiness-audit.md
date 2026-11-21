# Five-Dimension Production Readiness Audit Checklist

**Status**: accepted baseline
**Updated**: 2026-11-21
**Chinese**: [production-readiness-audit.zh.md](production-readiness-audit.zh.md)
**Companion Skill**: [`skills/audit-production-readiness/SKILL.md`](../skills/audit-production-readiness/SKILL.md)

> **Why This Exists**: Single-PR reviews catch local bugs, yet a repository with
> 100 green PRs can still be demo-grade in production — dead spend guards reading
> fields nobody writes, 3-layer config default drift, conflicting timeout/pool
> caps, or unwired `STATUS.md` claims. This checklist turns battle-tested
> full-repo implementation auditing into a repeatable, language-agnostic
> discipline.

---

## 1. Pre-Audit Parameters & Honesty Protocol

Fill every parameter before reading code (write `UNKNOWN` — never leave blank):
- **Target & Exact Baseline**: repository + exact 40-char commit SHA from freshly fetched `origin/<default>`.
- **Deployment Assumptions**: topology, replica count, tenant model (single-tenant vs multi-tenant SaaS), stateful storage type.
- **Runtime Access**: `none` or strictly read-only (`SELECT`, `EXPLAIN` without `ANALYZE`, read-only metrics/logs/cluster queries).
- **Prior Audit Baseline**: path to previous `EVIDENCE.md` (or `first round`) + explicit out-of-scope list.

Non-negotiable rules:
- [ ] **Assume defects exist**: never write ungrounded praise without `file:line` or measured evidence.
- [ ] **Tag every finding**: `[Fact]` (`file:line`), `[Measured]` (command + output), `[Inference]` (reasoning chain), or `[Unknown]`.
- [ ] **Include confidence + falsifier**: `High / Medium / Low` plus one sentence stating what evidence would overturn the conclusion.
- [ ] **Strictly read-only & zero secret values**: never commit during an audit; record secret key names, counts, and file permission bits only.

---

## 2. Seven Evidence Disciplines (Prevent False Audits)

- [ ] **1. Trace negative claims to construction**: Never assert *"missing timeout / auth / cap / caller"* from `grep` returning empty — trace caller → constructor → DI / middleware / config.
- [ ] **2. Verify data liveness**: Every guard, quota, or dashboard counter reading field `F` must have a verified **production writer** (`file:line`). Read-only or test-only fields mean the guard is dead.
- [ ] **3. Trace claims from live entrypoints**: Verify every `STATUS.md` checkmark or closed issue from real live HTTP/CLI/worker entrypoints; mark unreachable implementations as `unwired claim`.
- [ ] **4. Reproducible counts & fixed denominators**: Attach the exact unfiltered command and scope for every count or ratio (`git ls-files` vs `find` mismatches silently corrupt percentages).
- [ ] **5. Performance requires measurement**: Without `[Measured]` data, classify findings as `[Unverified Hypothesis]` and supply the minimal read-only probe or load test.
- [ ] **6. Check defaults across all three layers**: Compare (a) code/Settings default, (b) shipped deployment template (`.env.example`, Helm/Compose/IaC), and (c) live deployed value (`[Deployment-Dependent]` if unobserved). Updating a template does not prove existing environments changed.
- [ ] **7. Write arithmetic out & verify term semantics**: Show explicit arithmetic and verify at `file:line` whether each parameter is per-call, shared across one execution, or cumulative across turns.

---

## 3. Coupling, Fix & Deployment Disciplines

- [ ] **Derive limits from neighboring limits**: List every timeout, retry, concurrency, pool, queue-visibility, or budget cap on the same resource and derive fixes from their inequality — never recommend an isolated magic number.
- [ ] **State fix preconditions & failure modes**: Document when a fix breaks or becomes ineffective (e.g., running as non-root fails if mounted secret files are `0644` or `/proc/1/environ` is readable by the same UID) and note blast radius (files, migrations, contracts).
- [ ] **Tag deployment-dependent severity**: Mark environment-sensitive items `[Deployment-Dependent]` with a minimal read-only probe (`Result A -> Severity X; Result B -> Severity Y`).
- [ ] **Verify subagent outputs**: Re-verify every high-severity `[Fact]`, negative claim, and count produced by subagents. Label unverified items `[Unverified Subagent Inference]` and failed dimensions `NOT_EVALUATED`.

---

## 4. Adversarial Dual-Hypothesis Verdict (H1 vs H2)

Before assigning scores, argue the strongest evidence-backed case for both sides:
- **H1 (Production-ready)**: Under the stated deployment assumptions, the architecture supports production scale and evolution.
- **H2 (Demo-grade)**: Load growth or requirement changes will force a structural rewrite.

Deliver a clear verdict (`<= 200` words) grounded in verified findings — no hedging.

---

## 5. Five Language-Agnostic Audit Dimensions

### A. Architecture
- [ ] **Boundaries & cycles**: UI / API / domain / worker / persistence separation; zero business logic leaking into transport handlers.
- [ ] **Replaceability**: Estimated file blast radius to swap DB, queue, external provider, or LLM vendor.
- [ ] **Data flow & liveness**: End-to-end request lifecycle closed with no orphaned states or dead writers.
- [ ] **State ownership & recovery**: Where session and long-job state live; behavior across restarts, deploys, and node failures.
- [ ] **Horizontal scaling blockers**: In-memory state, sticky sessions, single-worker locks, non-portable local storage.

### B. Design
- [ ] **API & error contract**: Consistent error model, versioning, and separation of internal vs user-facing errors.
- [ ] **Abstraction & duplication**: Duplication density with exact measurement command; over- vs under-engineering.
- [ ] **Type discipline**: Strict static types (`strict: true`, mypy/static typing, Rust/Go/Java domain types) vs untyped maps/`any`.
- [ ] **Configuration hygiene**: 12-factor env separation, secret/config decoupling, and startup assertions for coupled config limits.

### C. Functionality
- [ ] **Feature reality table**: Claimed capability × status (`Complete` / `Partial` / `Stub` / `Missing` / `Unwired Claim`) × live entrypoint `file:line`.
- [ ] **Vibe-coding residue**: Hardcoded mocks, dead code, commented blocks, production helpers called only by tests.
- [ ] **Edge cases & idempotency**: Empty states, concurrency, retries, idempotency on mutations/payments, cancellation recovery.
- [ ] **Test authenticity**: Behavioral assertions vs "does not throw" smoke tests; test-to-critical-path ratio.

### D. Performance (`[Unverified Hypothesis]` Without Measurement)
- [ ] **Latency breakdown**: Critical-path timing, serial vs parallel external/tool calls, streaming behavior.
- [ ] **Frontend**: Bundle budget, avoidable re-renders, virtualized long lists, streaming Markdown/table scaling.
- [ ] **Backend**: N+1 queries, blocking I/O on async loops, total DB pool ledger (`sum(procs * (pool + overflow)) * rollout <= 0.7 * max_conn`), caching.
- [ ] **Cost & concurrency bottleneck**: Token/cost accounting liveness (if AI-powered) and static prediction of the first bottleneck at target concurrency + verification method.

### E. Security
- [ ] **Credentials & runtime exposure**: Hardcoded secrets count (with command), secret boundaries across client/server/logs/env/mounted files/`/proc`.
- [ ] **AuthN/AuthZ coverage**: `M / N` protected endpoints computed via route/dependency graph (not naive decorator grep) + tenant/object IDOR check.
- [ ] **Injection & unsafe sinks**: SQL/NoSQL, shell/command, XSS/HTML, template, SSRF, path traversal, unsafe deserialization.
- [ ] **AI/Agent attack surface (if applicable)**: Prompt-injection exposure, least-privilege tool identity, HITL gates on destructive actions, multi-dimensional loop/cost caps, cross-tenant memory isolation.
- [ ] **Pre-release operational safety**: Verify `SECRET_KEY` / signing keys are preserved across deploys (changing them breaks password hashes, sessions, and encrypted columns); require verified DB backups, forward-compatible non-destructive migrations, and critical-table row-count checks; pin immutable container image digests (never `:latest`) with `read_only`, `no-new-privileges`, and `cap_drop: ALL`.

---

## 6. Deliverable Checklist & Round-Over-Round Continuity

- [ ] **Report (`REPORT.md`)**: Baseline & assumptions, H1/H2 verdict, 5-dimension scorecard (`1–5` or `NOT_EVALUATED`), severity-ranked findings, feature reality table, reproducible metrics table, probe list, open decisions, delta vs prior round (`Closed`/`Persisting`/`New`), uncovered scope (`does_not_prove`), and **Self-Challenge** (top 3 ways the audit could be wrong + falsification checks).
- [ ] **Evidence Anchor (`EVIDENCE.md`)**: Scope, exact commit SHA, shortest re-verification commands, known gaps, and next-round pickup items — never freeze full repo copies into audit directories.
