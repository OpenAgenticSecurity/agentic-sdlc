# Backend Performance Review Checklist for AI-Written Systems

**Status**: accepted baseline
**Updated**: 2026-11-20
**Chinese**: [backend-performance-review.zh.md](backend-performance-review.zh.md)
**Source**: [Vibe Coding Application Performance: Runs vs. Holds Up](https://fz.cool/vibe-coding-backend-performance/) (100+ real performance fixes across ~380K LOC FastAPI + SQLAlchemy + Celery + K8s backend; only 16% proactive, 5% caught by CI)

> **Core Reality**: Frontend bugs draw a normal-looking wrong page; backend
> performance bugs leave tasks stuck in `running` forever — and in an Agent
> platform, slow or looping backend agents burn real LLM dollars. Agents test
> at **P50** (6 events, 38 rows, 23s); production breaks at **P99** (1,000+
> events, 100K rows, 90+ minute runs) and across **multiplicative factors** no
> single diff shows.

---

## 1. Eight Empirical Performance Trap Categories

### 1. Startup, Container & Release Lifecycle

- [ ] **Install all deps AND the app package at image build time** — never run `uv run` / network installs at container startup (eliminated 5-minute startup overhead down to ~8s).
- [ ] **Proper PID 1 signal handling**: Start the server via `exec` (or `tini`) so `SIGTERM` reaches the app cleanly.
- [ ] **Separate three K8s probes**: `startupProbe` for slow boot; lightweight `livenessProbe` (e.g., heartbeat file, NOT heavy `celery inspect ping` or DB queries); `readinessProbe` for traffic admission.
- [ ] **Graceful shutdown chain inequality**: `terminationGracePeriodSeconds >= preStop + longest_task + margin` (default 30s SIGKILLs long-running workers on every deploy).
- [ ] **Response-type-aware compression**: Never wrap SSE/streaming endpoints in buffering GZip middleware; bypass compression for `text/event-stream` while compressing large JSON responses.

### 2. Database, Indexes & Connection Pool Math

- [ ] **Never ship unpaginated list endpoints**: Share one common pagination dependency (`default=20`, hard `max=200`), server-side search/filter, and matching composite indexes `(tenant_id, ...)` — including **foreign-key columns** (PostgreSQL does not auto-index FKs).
- [ ] **Kill N+1 at the ORM/test boundary**: Default relations to `lazy="raise"` or use explicit `selectinload` / batch `IN`; lock hot endpoints with a **SQL query-budget regression test** (`before_cursor_execute` counter).
- [ ] **Write-time aggregation**: Pre-compute dashboard totals (e.g., token usage) on write instead of reading full message bodies into Python on every dashboard load.
- [ ] **Connection pool total ledger (contract test)**: Verify `sum(processes * (pool_size + max_overflow)) * rollout_factor <= 0.7 * db_max_connections` (or place PgBouncer in front).
- [ ] **Rollback before writing failure status**: On DB disconnect or error inside a long task, call `rollback()` before recording failure state (otherwise the task stays `running` forever); never inherit parent DB connections into child processes.
- [ ] **64-bit counters & durations**: Default `duration_ms`, counters, and IDs to `BIGINT` (32-bit `duration_ms` overflows after ~24.86 days).

### 3. Event Loop & Concurrency

- [ ] **Match handler type to I/O driver**: Use `def` (threadpool) when calling sync SQLAlchemy `Session`, sync Redis, or sync file parsing; use `async def` ONLY when the entire chain is truly async (`asyncpg` / `AsyncSession`) or offloads blocking work via `asyncio.to_thread`.
- [ ] **NEVER hold a DB connection across `await` remote/LLM/HTTP calls**: Close/commit the short session before awaiting remote I/O, and open a new short transaction only if writes are needed after return.
- [ ] **Align threadpool and DB pool budgets** (Starlette/AnyIO default threadpool is 40 tokens); set pool checkout timeout and return explicit `503` on exhaustion.
- [ ] **Enforce with lint**: Enable Ruff `ASYNC` rules and add an AST CI check forbidding sync `Session` injection into `async def` routes.
- [ ] **Test locks & transactions on the production DB engine** (PostgreSQL `SELECT ... FOR UPDATE` deadlocks do not reproduce on SQLite).

### 4. Bounded Data Volume & Fan-Out

- [ ] **Stream large uploads/downloads**: Hash and stream chunks to a single disk buffer or presigned object-storage URL (avoid 2–3x memory spikes from concatenating chunks in RAM).
- [ ] **Enforce size limits at the outer edge first** (Ingress/Nginx `client_max_body_size`) plus per-type app caps and MIME validation.
- [ ] **Cap pagination, selectors, and sub-agent fan-out**: Bound maximum pages/items/parallel children, store large tool outputs by reference, and disclose truncation explicitly.

### 5. Idle Quietness & Request Amplification

- [ ] **Idle systems must stay quiet**: High-frequency scheduled tasks (`<60s`) must run a lightweight read-only `EXISTS` probe before opening a claim transaction, and set `ignore_result=True` (enforce via unit test!).
- [ ] **Disable orphan beat tasks by default**: Scheduled tasks with no active writer in a deployment must stay gated off.
- [ ] **Push + delta over full-snapshot polling**: Inline event deltas in notifications (falling back to snapshot reload only past size limits); split lightweight status endpoints from multi-MB bootstrap payloads; use Page Visibility backoff and short-TTL/single-flight caches.

### 6. Timeout Inequalities & Clean Cancellation

Encode the timeout hierarchy as a **contract test** so config changes cannot silently invert it:

```text
queue_visibility_timeout > stale_cleanup_threshold > task_hard_limit > task_soft_limit > sub_agent_budget > tool_or_sse_timeout > llm_client_timeout
```

- [ ] **Zero unbounded clients**: Set explicit connect/read/write/pool timeouts on every LLM SDK, HTTP client, and shared Redis socket.
- [ ] **Never swallow `SoftTimeLimitExceeded`**: Catch it explicitly before `except Exception`, flush cleanup/failure state, and re-raise.
- [ ] **Propagate deadlines & cancellation**: Divide parent budget across sequential sub-agent batches; propagate cancellation to child processes and remote tools.
- [ ] **Use lease + heartbeat instead of raw start-time heuristics** for stale/zombie task cleanup, covering inline runs, implicit-end workflows, and orphaned child runs.

### 7. Agent Loops & LLM Cost Controls

- [ ] **Multi-dimensional hard caps**: Enforce max turns, max tool calls, max tokens, and wall-clock limit — on limit, instruct the model to synthesize a conclusion from gathered facts rather than silently dying.
- [ ] **Hard loop termination (not endless warnings)**: Hash `(tool_name, canonical_args)` and terminate after N repeated identical calls or consecutive failures; attach explicit guidance when a tool legitimately returns empty results.
- [ ] **Clean tool contracts**: Log human-readable tool names (not internal UUIDs) in history; coerce safe numeric strings before validation; return actionable schema errors (`expected X, got Y`).
- [ ] **Window-scaled context & 3-tier tool degradation**: Derive context budget from actual model window; degrade old tool outputs gracefully (`full` → `summary` → `retrievable_ref`) instead of dropping recent tool results and causing oscillation.
- [ ] **Prompt caching & on-demand exposure**: Keep static prefixes (system prompt, tool defs, skill index) stable ahead of dynamic turns; expose skill/tool loaders only when skills exist; deduplicate identical alert storms by fingerprint before dispatching agents.

### 8. CPU, ReDoS & Resource Reclamation

- [ ] **Linear-time regexes + input length cap**: Eliminate nested quantifiers/overlapping alternation in redaction/parsing regexes (use Python 3.11+ atomic groups `(?>...)` or RE2); truncate untrusted input before regex execution.
- [ ] **Process-level client reuse & context managers**: Manage HTTP, LLM SDK, and vector-DB clients via app lifespan or `with` / `async with`; treat `ResourceWarning` as an error in tests.
- [ ] **Standard event loops & bounded workers**: Use `asyncio.run()` instead of manual loop creation/close; configure Celery `worker_max_tasks_per_child` / `worker_max_memory_per_child`; keep `py-spy` / OpenTelemetry ready for production profiling.

---

## 2. Five Pre-Delivery Backend Rules

1. **Write down runtime assumptions**: Max rows per list, max events per session, max task duration, concurrent users, and process count — put them in tests/comments so expiry becomes visible.
2. **Test with P99 tail data on the real DB**: Build a seeded tail dataset (100K rows, 1,000-event session) and run concurrency tests on PostgreSQL, not SQLite.
3. **Compute multiplicative ledgers in one place**: One test checks the full connection-pool sum across all processes; one test checks all timeout inequalities.
4. **Graduate the 2nd occurrence into a gate**: Query-budget test, `<60s` beat `ignore_result` test, AST `async def` + sync `Session` lint, and pool contract test.
5. **File real issues immediately — and inspect idle staging stats**: Notes left in commit messages disappear in the next agent session. Before shipping, check staging task/SQL/Redis counts while **nobody** is using the system: if it is busy while idle, it will collapse under load.
