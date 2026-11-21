# Reliable, Stable & Performant AI Coding Standard

**Status**: accepted baseline
**Updated**: 2026-11-21
**Chinese**: [reliable-and-performant-coding.zh.md](reliable-and-performant-coding.zh.md)

## Goal

Security rules keep an AI-written system from being breached; reliability,
stability, and performance rules keep it from collapsing at P99 load, leaking
resources over multi-hour agent runs, or silently breaking when models or
dependencies upgrade.

This standard defines **pre-coding invariants** that coding agents must apply
*while writing code* — rather than waiting for post-hoc PR review.

---

## 1. Resource Lifecycles & Long-Path Resilience

AI-generated code commonly works on a single happy-path call and breaks after
100 consecutive agent loop iterations.

- **Whoever creates a resource owns closing it**: Manage HTTP clients, LLM
  SDKs, DB sessions, SSH/socket connections, and file handles via explicit
  context managers / RAII / `defer` / app lifespans — never allocate per-call
  clients without teardown (eliminates `Event loop is closed` and descriptor
  exhaustion).
- **Design for long-path loops, not one-shot scripts**: Reuse persistent
  connections (connection pools / SSH multiplexing), apply bounded exponential
  backoff on transient transport failures, attach heartbeats/health probes, and
  decode untrusted command/network bytes safely (`errors="replace"` or explicit
  UTF-8 lossy decoding).
- **Bounded payloads everywhere**: Cap upload/download streams at the edge and
  stream chunks rather than buffering entire payloads in RAM; cap response
  sizes, pagination limits (`default=20`, hard `max=200`), and tool outputs
  with explicit truncation disclosure.

## 2. Idempotency, `RESULT_UNKNOWN` & Blast-Radius Control

Across external APIs and networks, *"request sent, no receipt received"*
(`RESULT_UNKNOWN`) is normal physics — distributed exactly-once does not exist.

- **Never blindly retry mutating calls on `RESULT_UNKNOWN`**: Require
  idempotency keys on state-changing writes and perform an independent
  read-after-write reconciliation check before retrying or escalating to human
  review.
- **Four-layer blast-radius governance for automated side effects**:
  1. **Pre-execution physical caps**: Rate/asset caps independent of the LLM
     (forbid automatic mutation of critical infrastructure).
  2. **Reversible-first with TTL**: Prefer time-bounded reversible actions and
     pre-register rollback/compensation steps before executing.
  3. **Out-of-band emergency stop**: Keep kill switches outside the LLM loop
     and UI, invalidating in-flight grants atomically via a monotonic safety
     epoch.
  4. **Explicit durable state machines**: Long-running jobs must persist leases,
     heartbeats, and fencing tokens so timed-out retries cannot overwrite newer
     owners.

## 3. Concurrency, Event-Loop Hygiene & Capacity Ledgers

- **Never block an async event loop**: Do not call synchronous DB drivers,
  synchronous cache/HTTP clients, or heavy CPU parsing inside `async` handlers
  (Python `async def`, Node/Tokio event loops); offload blocking calls cleanly
  or match handler concurrency type to the driver.
- **Never hold DB connections or locks across remote awaits**: Commit/release
  short DB transactions before awaiting external HTTP/LLM/sandbox calls; test
  row locks (`SELECT ... FOR UPDATE`) on the real production DB engine, not
  in-memory SQLite.
- **Encode multiplicative ledgers as contract tests** (see
  [`examples/backend-contract-gates.py`](../examples/backend-contract-gates.py)):
  - **DB pool ledger**: `sum(processes * (pool_size + max_overflow)) * rollout_factor <= 0.7 * db_max_connections`.
  - **Timeout monotonicity**: `queue_visibility > stale_cleanup > task_hard > task_soft > sub_agent > tool_or_sse > llm_client`.
  - **Query budget & indexes**: Add composite `(tenant_id, ...)` and explicit
    foreign-key indexes; prevent N+1 with strict relation loading + SQL query
    count tests; use 64-bit integers (`BIGINT`) for durations and counters.
- **Keep idle systems quiet**: Periodic tasks (`<60s`) run a read-only `EXISTS`
  probe first and disable result-store writes; bypass buffering compression
  (e.g., GZip) on SSE/streaming endpoints.

## 4. Schema Single-Authority & Observable Degradation

- **Single schema authority**: Persistent storage schemas evolve exclusively
  through versioned migrations (Alembic, Goose, Flyway, Prisma Migrate) —
  forbid runtime `create_all()` or silent schema mutation on startup.
- **Observable degradation (never fake green)**: Separate `loading`, `error`,
  and `actually empty` states explicitly across backend and frontend; forbid
  fallback defaults (`?? 0`, `|| []`, silent `catch`) that turn failed reads
  into plausible values; call `rollback()` before recording failure state on DB
  errors.
- **Zero unbounded regexes**: Keep parsing and redaction regexes linear-time
  with explicit input length caps before matching.

## 5. Thin-vs-Thick Architecture & Model-Upgrade Discipline

Base models jump every 3–6 months; architecture must compound rather than rot.

- **Build thick where model improvements compound**: Canonical fact/data
  models, deterministic governance/authorization/audit kernels, sandboxed
  execution substrates, and reproducible eval benchmarks.
- **Build thin (and delete aggressively) on model-workaround glue**: Avoid heavy
  prompt scaffolding or multi-agent reflection layers built solely to patch a
  weak model's temporary blind spots.
- **Treat every model upgrade as a high-risk release**: Never swap a production
  or coding-agent model by editing one env var without running a fixed
  regression suite checking completion rate, tool errors, refusal rate,
  concurrency deadlocks (stronger models issue parallel tool calls), fixed
  context-compression threshold mismatches, and schema-strictness drift.

## 6. Engineering-Isolated Multi-Agent & Tool Harness Design

- **Isolate, do not free-chat**: Multi-agent gains come from clean
  `TaskEnvelope` context isolation, least-privilege tool intersection (keep
  raw multi-MB telemetry tools on sub-agents, not supervisors), append-only
  single-writer blackboards that record non-owner writes as explicit `conflict`,
  and deterministic aggregation that preserves disagreements for evidence
  falsification.
- **Design tool harnesses for agents, not raw REST dumps**: Use tiered semantic
  primitives for high-frequency governed reads, controlled sandboxes for
  open-ended analysis (graduating repeated sandbox scripts into versioned
  tools), bounded byte-sliced spillover for large outputs, and **actionable
  error messages** that tell the agent the exact next recovery step rather than
  causing retry loops.

## Related Documents

- Backend performance review checklist: [checklists/backend-performance-review.md](../checklists/backend-performance-review.md)
- Frontend 454-bug review checklist: [checklists/frontend-vibe-coding-review.md](../checklists/frontend-vibe-coding-review.md)
- Runnable starter contract gates: [examples/backend-contract-gates.py](../examples/backend-contract-gates.py)
- Security invariants: [secure-vibe-coding.md](secure-vibe-coding.md)
