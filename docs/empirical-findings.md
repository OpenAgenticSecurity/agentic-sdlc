# Empirical Findings: Why Coding Agents Fail in Real Repositories

**Status**: empirical evidence summary
**Updated**: 2026-11-21
**Chinese**: [empirical-findings.zh.md](empirical-findings.zh.md)

Every rule, checklist, skill, and fail-closed script in
`OpenAgenticSecurity/agentic-sdlc` comes from real multi-repo AI-assisted
production engineering rather than hypothetical prompt advice.

Across **200B+ tokens** of sustained multi-repository agentic development
(concurrent Claude Code, Cursor, and Codex sessions across Python, TypeScript,
React, and Rust services), we ran **four bounded empirical studies** with
explicit denominators and logged two major operational incidents. This page
summarizes the exact data, how each failure mode occurs, which control in this
repository addresses it, and what these observations **do not** prove.

---

## 1. Evidence Overview (Explicit Denominators)

To avoid denominator mixing (`Fake-Done Breakpoint #4`), every metric below is
bound to its exact study dataset rather than extrapolated across all 200B+
tokens:

| Study / Incident | Exact Dataset / Denominator | Headline Measurement | Concrete Control in This Repo |
|---|---|---|---|
| **1. Session Survival & Seven Sins** | 443 tracked sessions / 8.4B tokens | `<5K` LOC autonomous ~100% vs `>10K` LOC unstructured ~55%; failure rate jumps `<10%` → **35.7%** past 200+ messages | [vibe-coding-seven-sins.md](../checklists/vibe-coding-seven-sins.md), [ai-coding-context.md](../standards/ai-coding-context.md) |
| **2. Frontend Defect Audit** | 454 deduplicated issues across ~100K LOC React/TS (321 root-caused; 216 with discovery channel) | Unit tests, `tsc`, and CI caught only **7%**; top 4 root causes = **84%** | [frontend-vibe-coding-review.md](../checklists/frontend-vibe-coding-review.md), [`audit-pr-diff`](../skills/audit-pr-diff/SKILL.md) |
| **3. Backend Performance Audit** | 100+ real fixes across ~380K LOC FastAPI + SQLAlchemy + Celery + K8s | Only **16%** found proactively; only **5%** caught by CI | [backend-performance-review.md](../checklists/backend-performance-review.md), [ci-python.yml](../profiles/L1-team/workflows/ci-python.yml) |
| **4. Fake-Done & Review Audits** | 24-finding AI review audit; 15-fixture legacy gate; 43-finding counterevidence review; 33 diagrams | **24 → 2** verified blockers; **15/15 → 0/15** gate drift; **43 → 29** after counterevidence; **0/33** diagrams unconditionally accurate | [fake-done-dereference.md](../checklists/fake-done-dereference.md), [`done-claim-verify`](../skills/done-claim-verify/SKILL.md), [observe-github-ruleset.py](../scripts/observe-github-ruleset.py) |
| **5. Operational Incidents** | Multi-worktree & subagent production ops | **~260M tokens burned in 1 hour** (forked subagents); **7.8 GB vs 240 KB** audit archives; silent wrong-checkout pytest runs | [agent-ops-and-workspace-hygiene.md](../checklists/agent-ops-and-workspace-hygiene.md), [link-shared-node-deps.mjs](../scripts/link-shared-node-deps.mjs), [workspace-git.py](../scripts/workspace-git.py) |

---

## 2. Study 1 — The 10K LOC Phase Transition & Context Cliff

In the 443-session / 8.4B-token tracked sample:

- **Phase transition**: Disposable prototypes (`<5K` LOC, 1–6 sessions) succeed
  at nearly 100% in conversational mode. Once a codebase crosses `>10K` LOC and
  50+ sessions, unstructured vibe coding drops to **~55%** because cross-session
  consistency decays.
- **Three failure archetypes**:
  1. **Sandbox Wall (~60%)**: missing write permissions, network blocks, or tool
     mismatches cause agents to loop blindly.
  2. **Context Window Exhaustion (~25%)**: session failure rates stay `<10%`
     early on, then spike to **35.7%** past 200+ messages.
  3. **Capability / Filter Ceiling (~15%)**: routing architecture-heavy edits to
     low-reasoning modes or mismatched tools.
- **Seven recurring failure classes**: premature victory declarations, ghost
  modules (created cleanly but never wired into any caller), cross-session
  Frankenstein patterns (sync DB mixed into `async def`), big-bang rewrites,
  plausible fake fallback data, dormant `DEFAULT = False` flags, and
  aspirational docs drifting from code reality.

**How this repo stops it**: `STATUS.md` as implementation reality anchor, hard
60-message compaction boundaries, `"wire it or delete it"`, and deterministic
`scripts/workspace-git.py` isolation so parallel agents cannot corrupt `main`.

---

## 3. Study 2 — Frontend: Why Green CI Caught Only 7% of 454 Real Bugs

Across 454 deduplicated frontend defects in a ~100K LOC React/TypeScript
application (321 with identifiable root causes, 216 with known discovery
channels):

- **How defects were actually found**: **35%** by humans clicking real flows,
  **31%** via deep audits, and **only 7%** by unit tests, TypeScript, and CI
  combined (most of that 7% came from browser QA agents, not unit tests).
- **Why**: Backends throw HTTP 500 with a stack trace; frontends silently render
  a plausible-looking page using `?? 0` or `|| []`.
- **Top 4 root causes accounted for 84% of all classified bugs**:
  1. **Unasserted cross-layer edges (39%)** — 95% of API contract drift, 77% of
     entry/permission mismatches (disabled feature hidden in UI, still live on
     direct route or backend).
  2. **Holds only at small scale / demo (18%)** — O(n²) streaming Markdown
     re-renders, silent truncation of security artifacts, unbounded polling.
  3. **Copied from nearby without fixing the shared layer (16%)** — 70% of
     duplicate code and 55% of layout/nested-scroll traps.
  4. **Plausible fallback instead of explicit `UNKNOWN`/error (11%)** — sharing
     `[]` across `loading`, `error`, and `actually empty`.
  5. **Gate / test failure itself (4%)** — `0 tests collected` or missing tools
     exiting 0.

**How this repo stops it**: the 4-question Frontend Acceptance Ladder
(*Rendered → Reachable → Correct → Holds at scale*), 3-layer disabled-feature
assertions, and the [`audit-pr-diff`](../skills/audit-pr-diff/SKILL.md) skill
combined with fail-closed CI templates ([ci-node-ts.yml](../profiles/L1-team/workflows/ci-node-ts.yml)).

---

## 4. Study 3 — Backend Performance: Runs at P50, Collapses at P99

Across 100+ backend performance fixes in a ~380K LOC FastAPI + SQLAlchemy +
Celery + Kubernetes stack:

- **Only 16%** were caught proactively before landing; **only 5%** were caught
  by CI.
- **Why**: Agents test at **P50** (6 events, 38 rows, 23s); production breaks at
  **P99** (1,000+ events, 100K rows, 90+ minute runs) and across **multiplicative
  ledgers** (process count × pool size × rollout factor) that no single-file
  diff exposes.
- **Recurring traps**: sync SQLAlchemy `Session` injected into `async def`,
  holding DB connections open across `await` LLM calls, unindexed PostgreSQL
  foreign keys and N+1 queries, inverted timeout chains (`soft > hard` or
  `hard > visibility_timeout`), noisy `<60s` Celery beat tasks writing results on
  idle systems, and unbounded agent tool loops.

**How this repo stops it**: Ruff `ASYNC`/`B`/`S` security & async rules baked
into [ci-python.yml](../profiles/L1-team/workflows/ci-python.yml), multiplicative
pool/timeout inequality contracts in
[backend-performance-review.md](../checklists/backend-performance-review.md),
and static fail-open/sink checks in [`scripts/audit-repo.py`](../scripts/audit-repo.py).

---

## 5. Study 4 — "Fake Done" & Why Agents Cannot Grade Their Own Homework

Four independent audits exposed how easily AI-assisted workflows manufacture
green illusions:

- **24 → 2 AI code-review verification audit**: 24 confident AI review findings
  on a chunked diff dropped to **2 real blockers** once verified against the
  exact PR-head checkout, callers, and tests.
- **15/15 → 0/15 legacy gate drift**: A green automated gate was faithfully
  validating an obsolete fixture schema (`15/15` green) while rejecting `0/15`
  of the real current contract.
- **43 → 29 counterevidence audit**: Separating *Fact confidence* (sink exists)
  from *Impact confidence* (reachable under real controls) eliminated a third of
  supposedly high-severity findings.
- **0 / 33 architecture diagrams unconditionally accurate**: Valid SVG/XML only
  proves syntax, never code truth.

**How this repo stops it**:
1. Never collapse `NOT_RUN`, `FLAKY`, `ERROR`, `UNKNOWN`, or `CONFLICT` into
   `PASS` ([done-claim-verify](../skills/done-claim-verify/SKILL.md)).
2. Require a 7-tuple `DoneClaim` with explicit `does_not_prove[]`
   ([done-claim.template.md](../checklists/done-claim.template.md)).
3. Treat PR-controlled CI as **candidate / advisory only** and verify the
   external GitHub merge boundary via
   [`scripts/observe-github-ruleset.py`](../scripts/observe-github-ruleset.py)
   and [`scripts/audit-repo.py`](../scripts/audit-repo.py) — catching rulesets
   where an AI agent can push new commits after human approval
   (`require_last_push_approval: false`), spoof unbound status checks
   (`integration_id: null`), or bypass rules unconditionally.

---

## 6. How to Verify Effectiveness on Your Own Repository in 10 Seconds

Do not take these studies on faith. Run the zero-dependency, read-only self-audit
against **your own repository** (pure Python 3.11+ standard library, zero
`pip install`, modifies nothing):

```bash
# Audit local Layer 1 & Layer 2 signals (context, worktree hygiene, CI action SHA pins, Python AST traps):
python3 scripts/audit-repo.py /path/to/your-repo

# Also audit your live GitHub Branch Ruleset against AI post-approval push & status spoofing (read-only via `gh`):
python3 scripts/audit-repo.py /path/to/your-repo --github
```

To verify that this repository's own negative mutation gates actually turn red
on planted violations (offline, zero network):

```bash
python3 -m pip install --require-hashes --only-binary=:all: -r requirements-test.txt
make demo-catch-bugs
make verify-all
```

---

## 7. Honest Limits (`does_not_prove`)

In keeping with this repository's own verification standard, these empirical
findings explicitly **do not prove**:

- That every team or language stack will experience identical bug ratios to our
  Python/TypeScript/React multi-repo workloads.
- That installing Markdown checklists or Agent Skills alone prevents determined
  prompt injection or eliminates the need for runtime security testing and human
  engineering judgment.
- That a green run of `scripts/audit-repo.py` guarantees a repository is
  vulnerability-free — static checks only catch specific high-signal structural
  and supply-chain failure classes; runtime semantics, business-logic authz, and
  production scale still require integration tests and external enforcement.
