# Starter Verification Gate Examples

**Updated**: 2026-11-21
**Chinese**: [README.zh.md](README.zh.md)

Our empirical audits found that conventional unit tests and type checks caught
only **7%** of real frontend bugs and **5%** of real backend performance
incidents ([Empirical Findings](../docs/empirical-findings.md)).

These minimal, copy-ready starter gates show how to graduate high-frequency
checklist items into deterministic automated tests:

| Example | What It Graduates Into Code | How to Use |
|---|---|---|
| [`backend-contract-gates.py`](backend-contract-gates.py) | SQL query-budget ceiling (anti-N+1), multiplicative DB connection-pool ledger, timeout-chain monotonicity, and negative path/tenant rejection tests | Runnable directly with `pytest examples/backend-contract-gates.py`; adapt parameters to your real config & ORM |
| [`frontend-3layer-gate.spec.ts`](frontend-3layer-gate.spec.ts) | Disabled-feature 3-layer test (UI + direct route + backend `403`/`404`), `loading`/`error`/`empty` separation (anti-`?? 0` fake fallback), and off-happy-path cancel test | Copy into your Playwright E2E suite and point routes/selectors at your app |

## Verification Rule

Before trusting any copied gate, **plant a deliberate violation** (for example,
lower `db_max_connections`, invert `task_soft_limit > task_hard_limit`, or make
an error route return fake `[]`) and confirm the test turns **red**.
