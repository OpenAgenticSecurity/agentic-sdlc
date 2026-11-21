# "Fake-Done" Dereference & Evidence Audit Checklist

**Status**: accepted baseline
**Updated**: 2026-11-20
**Chinese**: [fake-done-dereference.zh.md](fake-done-dereference.zh.md)
**Sources**: [Agentic Assurance Engineering](https://fz.cool/agentic-software-engineering-real-sdlc/) & [How Agents Fail: Verification Breakpoints of "Fake Done"](https://fz.cool/agentic-fake-done-breakpoints/)
**Templates**: [done-claim.template.md](done-claim.template.md) | [done-claim.example.json](done-claim.example.json)

> **Core Principle**: Agent output is an untrusted draft by default. Never stop
> at a green label (`active`, `v2`, `HTTP 200`, `all tests pass`) —
> **dereference** the label back to the live object, exact revision, user
> property, workload envelope, and primary evidence source.

---

## 1. The Four Dereference Breakpoints

A delivery can show green lights while silently failing along any of four
independent axes. Audit every non-trivial claim across all four:

| Breakpoint | Green Signal You See | What You Must Actually Dereference |
|---|---|---|
| **1. Subject identity** ("Did I change the thing actually serving?") | Config updated, checkout switched, service manager says `active`, version tag looks right | Live PID → working directory & loaded code revision → confirm live requests actually hit that process/artifact |
| **2. Acceptance predicate** ("Did I test the property users actually need?") | Component renders, unit test asserts something, API returns HTTP 200 | End-to-end user journey and cross-layer rule agreement (e.g., disabled feature hidden in UI, blocked by route guard, and rejected by backend) |
| **3. Workload / lifecycle** ("Did I test the real operating world?") | Nice before/after numbers, timeout signal fired | Exact code revision + environment + tail workload + explicit proof that cancelled/timed-out workers actually stopped and released resources |
| **4. Claim provenance** ("Is the report actually grounded?") | Polished report with tables, counts, and case lists | Primary source per item, consistent/comparable denominator, immutable saved snapshot, and explicit falsification criteria |

- [ ] **First-breakpoint rule**: On multi-stage paths, stop at the first broken invariant and mark downstream steps `not reached`. Never bypass auth or stitch together mismatched traces to draw a fake end-to-end green line.

## 2. The Seven-Tuple `DoneClaim`

Every completion claim must record all seven fields (see [done-claim.template.md](done-claim.template.md)):

```text
DoneClaim = subject + revision + environment + predicate
          + evidence_locator + independent_observer + limits (does_not_prove[])
```

- [ ] Never accept a bare boolean (`"done": true`) or prose summary without `evidence_locator` and `does_not_prove[]`.
- [ ] Distinguish **seeded readback** (proves ingest/read plumbing) from **native producer proof** (requires authorized execution, `source_commit` + `deployment_digest`, `stable_trace_id`, independent readback, and `bridge_writer: none`).

## 3. Do Not Collapse Legal Non-Green States

| State | Meaning | Rule |
|---|---|---|
| `PASS` / `VERIFIED` | Single check passed / claim verified within declared bounds | Never self-written without dereferenced evidence |
| `FAIL` | Observed invariant violated | Must block state transition (`failure_effect`) |
| `NOT_RUN` | Check/dependency did not execute | Never relabel as `PASS` |
| `UNKNOWN` | Missing identity, revision, or observation | Never guess a plausible default |
| `CONFLICT` | Two evidence sources disagree | Escalate to `HITL`, do not silently pick the greener one |
| `ERROR` | Verifier or harness crashed | Treat as non-passing failure |
| `NOT_APPLICABLE` | Dimension explicitly out of scope for this claim | Must be declared explicitly, not omitted |
| `HITL` / `FAILED` | Human risk/authority decision required / budget exhausted | **Legal terminal/pause exits** — agents must be allowed to stop |

## 4. Delivery Evidence Layers (Know What Each Layer Proves)

| Layer | Proves | Does NOT Prove |
|---|---|---|
| **Source** | Code committed at exact SHA | That commit is deployed |
| **CI / Build** | Specified checks passed on candidate revision | Running instance executes that artifact |
| **Deploy provenance** | Live process/image matches commit/digest & config | Real business path executed successfully |
| **Runtime readback** | Authorized execution produced verifiable object read back independently | Production peak scale, every environment, or absence of unrelated regressions |

## 5. Audit Your Gates & Findings Too (Verifiers Drift!)

Empirical lessons:
- **15/15 → 0/15 legacy fixture gate drift**: A green gate can faithfully validate an obsolete schema version.
- **24 → 2 AI code-review audit**: Chunked diff-only review without PR-head checkout produces fluent *candidate findings*, not verified blockers.
- **43 → 29 counterevidence audit**: Separate **Fact confidence** (does the code/sink exist?) from **Impact confidence** (is it reachable under real deployment, auth, and controls?).
- **0 / 33 architecture diagrams unconditionally accurate**: Valid SVG/XML only proves syntax; diagrams are claim-bearing artifacts that decay unless bound to exact commits and status tags (`Current`, `Partial`, `Stale`, `Target-only`).

### Gate & Review Audit Checklist

- [ ] Every blocking gate pins `verifier_version`, `subject_version`, `fixture_origin`, reproducible `command`, explicit `failure_effect`, and time-boxed `exception` (`owner` + `expires_at`).
- [ ] AI review outputs start as **candidate findings**; before blocking merge, verify against exact PR-head checkout (`file:line`), callers, Git history, tests, and prior review thread.
- [ ] High-severity findings undergo **independent counterevidence review** (different evidence source/role actively checking reachability, preconditions, and existing controls).
- [ ] Architecture/status docs carry `verified_at`, `source_commit`, verification command, and `does_not_prove[]`; stale docs downgrade to historical records.

## 6. Seven Questions Before Accepting Any Agent Delivery

1. Who defined the objective and shared truth?
2. Under what identity did the agent act, and what blast radius could it touch?
3. Who holds active write ownership right now?
4. Where should this change fail first (negative case / planted mutation)?
5. Does the evidence actually support Source, CI, Deploy, or Runtime?
6. What counterexample would falsify the claimed impact?
7. Who is authorized to accept residual risk or raise autonomy?
