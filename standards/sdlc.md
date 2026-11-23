# Agentic SDLC Standard

**Status**: accepted baseline
**Updated**: 2026-11-23
**Chinese**: [sdlc.zh.md](sdlc.zh.md)

Conventional SDLC assumes code is written slowly by accountable humans naturally
separated across roles. When coding agents write code, syntax generation becomes
cheap while **probabilistic drift, reward hacking, and cross-stage side effects**
accelerate by an order of magnitude. This standard defines the **Dual-Loop
Agentic SDLC** for single- and multi-repository engineering.

---

## 1. The Dual-Loop Agentic SDLC Model

Agentic delivery replaces linear human waterfall handoffs with a **fast
probabilistic inner loop** governed by a **slow deterministic outer loop**:

```text
+-----------------------------------------------------------------------------+
| OUTER LOOP · Deterministic Governance & Authority (Humans + Protected Rules)|
|                                                                             |
|  [1. Freeze Intent, Scope, RealityAnchor & Risk Floor]                      |
|         |                                                                   |
|         v                                                                   |
|  +-----------------------------------------------------------------------+  |
|  | INNER LOOP · High-Velocity Probabilistic Execution (Agent + Sandbox)  |  |
|  |   Isolated Worktree -> Plan -> Test-First Edit -> Coupled Sync        |  |
|  |   -> Emits Untrusted Patch + Candidate Evidence + DoneClaim           |  |
|  +-----------------------------------+-----------------------------------+  |
|                                      | (candidate draft only; never self-attests)
|                                      v                                      |
|  [2. External Referee]  Protected CI · PR-Diff Referee · GitHub Rulesets    |
|         |                                                                   |
|         v                                                                   |
|  [3. Immutable Release & Runtime Readback]  Digest + SLSA + Behavior List   |
|         |                                                                   |
|         v                                                                   |
|  [4. Asymmetric Feedback]  Escaped Defect -> Failing Negative Test / Gate   |
+-----------------------------------------------------------------------------+
```

Engineers shift from **human-as-operator** (typing every line) to
**human-as-governor** (defining intent, setting boundaries, owning merge/waiver
authority, and graduating incidents into deterministic gates).

---

## 2. Five-Layer Engineering Transformation

| Engineering Layer | Conventional SDLC Assumption | Agent-Era Failure Mode | Agentic SDLC Upgrade |
|---|---|---|---|
| **1. Environment** (Repo / IDE / CI) | Trusted single-user checkout; `.env` on laptop; CI is trusted | Parallel agents clobber `main`; poisoned `AGENTS.md`/`.vscode/tasks.json`; CI Comment-and-Control secret theft; local `.env` drops prod DB | Isolated worktrees, read-only shared stores, zero prod credentials in dev/agent env, instruction/IDE config scanning (`OAS-AGT-*`), PR CI treated as **candidate** |
| **2. Context** (Code / Docs / Issue) | Humans filter stale docs in memory | Context compaction erases prose rules; stale docs trigger hallucinated modules; code edits skip doc/test updates | `STATUS.md` reality anchor, thin unified `AGENTS.md`, projection-driven doc updates, declarative `ArtifactGraph` sync (`check-change-sync.py`) |
| **3. Verification** (Tests / Scans) | Green suite = honest verification | **Reward hacking**: agents delete failing assertions, add `# noqa`/`--passWithNoTests`, or write tautological tests; unit tests catch only 7% FE / 5% BE perf bugs | Producer/judge separation, PR-diff referee (`audit-pr-diff.py`), planted negative mutations, first-class `NOT_RUN`/`UNKNOWN`, 3-layer E2E & capacity-ledger contracts |
| **4. Delivery** (Build / Release / Deploy) | Merged source commit = known behavior | Post-approval agent pushes; prompt/model/tool changes alter behavior without code diffs; "fake done" claims | `Evidence -> VerificationResult -> Receipt -> Decision -> Outcome`, SLSA producer + consumer verification, behavioral change manifests, `DoneClaim` + `does_not_prove[]` |
| **5. Operations** (Logs / Incidents) | Human postmortems live in wikis | Runaway token/cost storms; blind retries on `RESULT_UNKNOWN`; same-account backups deleted; wiki notes ignored by next session | Multi-dimensional `$` / turn / fan-out caps, out-of-band `safety_epoch` kill switch, agent-unreachable backups, **Incident-to-Gate** graduation |

---

## 3. Two-Track Security Governance

Traditional vulnerabilities are amplified 10× by AI velocity while a brand-new
class of Confused-Deputy and gate-evasion threats emerges. Solve them on two
explicit tracks:

| Track | Threat Model | Required Controls |
|---|---|---|
| **Track A · AI-Amplified AppSec** | Well-intentioned human/agent ships insecure code, SQLi, SSRF, IDOR, fallback secrets, hallucinated packages, or destructive IaC | Upfront `secure-vibe-coding` invariants, deterministic SAST/secret linters in CI, **mandatory negative security test** per security diff, hash-locked deps & 40-char Action SHAs, shared IaC module `CODEOWNERS` parity ([secure-vibe-coding.md](secure-vibe-coding.md)) |
| **Track B · Agent-Native Security** | Coding or runtime agent is prompt-injected, hijacked via repo configs/comments, or games its own graders | Scan & `CODEOWNERS`-lock `AGENTS.md`/`.claude/`/`.mcp.json`/`workflows/`, forbid `pull_request_target` + untrusted title/body interpolation, run `audit-pr-diff.py` against reward hacking, enforce external GitHub Rulesets (`require_last_push_approval` + bound `integration_id`), server-bound `SecretRef`, atomic single-use approvals & read-only exfiltration blocks |

---

## 4. Core Lifecycle & Monotonic Gates

### Intake & Scope Freeze

Every non-trivial task (`>3` files, `>50` lines, or touching startup, auth,
contracts, migrations, or deployment) freezes before production edits:
- business goal and protected primary flow,
- explicit `in_scope`, `out_of_scope`, and UI scope (`out-of-scope` by default),
- affected repositories/contracts and 3-layer config impact (code default vs template vs live env),
- accountable human owner, runnable verification commands, and rollback/stop conditions.

### Design & ADR Gate

Design precedes code whenever a change crosses repositories, alters architecture
or contracts, changes deployment/stateful behavior, or touches security/privacy
boundaries. Decisions affecting two or more repositories or authority boundaries
require an ADR. Prefer deterministic schemas, compilers, and state machines over
LLM judgment; route side-effecting LLM outputs through closed validated IRs.

### Implementation & Coupled Closure

Work in an isolated branch and worktree from freshly fetched `origin/<default>`
([multi-ai-git-workflow.md](multi-ai-git-workflow.md)). Write failing tests
(including negative security tests on security paths) before changing behavior,
apply pre-coding reliability and capacity invariants
([reliable-and-performant-coding.md](reliable-and-performant-coding.md)), and
update all coupled tests, contracts, docs, and `STATUS.md` in the same change
set (`scripts/check-change-sync.py`).

### Independent Verification & Monotonic Gates (A0–A5)

High-assurance delivery enforces six monotonic boundaries:

| Gate | Decision Boundary |
|---|---|
| `A0 Task Admission` | Freeze task, exact base SHA, scope, risk floor, and stop conditions |
| `A1 Local Feedback` | Fast local checks (`make agent-check`, hooks, `deps`) — advisory only, never merge authority |
| `A2 PR Candidate` | Recompute exact diff, run fail-closed CI + `audit-pr-diff.py` referee (`authority: candidate`) |
| `A3 Protected Merge Boundary` | External GitHub Ruleset evaluates exact PR head / `merge_group`, `CODEOWNERS`, `>=2` reviews on enforcement surfaces, and bound status checks |
| `A4 Release & Provenance` | Build, test, SLSA-attest, and consumer-verify the exact immutable artifact digest + behavioral manifest ([versioning-and-releases.md](versioning-and-releases.md)) |
| `A5 Post-Release & Feedback` | Verify live runtime readback, monitor reopen/override/canary signals, and graduate escapes into gates |

Unavailability is monotonic: an enforced `A3` or `A4` blocks rather than falling
back to candidate checks or untested rebuilds. Any push invalidates prior review
and check evidence. Any PR modifying workflows, `action.yml`, schemas, checkers,
tests, `CODEOWNERS`, or agent instructions is **not self-attesting**.

### Review & Release Gates

Every PR states what changed, why, exact verification commands + exit codes,
unverified/`NOT_RUN` items, protected flows, risk/rollback, and accountable
human owner + AI tool provenance ([testing-strategy.md](testing-strategy.md)).

---

## 5. Incident-to-Gate Asymmetric Feedback Loop

Prose postmortems in external wikis are invisible to the next coding-agent
session. Every escaped production defect, near-miss, or recurring review catch
(`>= 2` occurrences) must close through
[`checklists/incident-to-gate.template.md`](../checklists/incident-to-gate.template.md):

1. Anchor the exact escaping commit/config and violated ontological axiom ([docs/ontology.md](../docs/ontology.md)).
2. Add a deterministic check or regression test that **fails red** on the
   vulnerable revision and **passes green** on adjacent legal controls.
3. Apply **asymmetric evolution**: lessons may only tighten constraints, add
   negative tests, or improve context — never auto-expand permissions or weaken
   existing gates.

---

## 6. Definition of Done

Done is a derived fact, never an agent-written boolean:
- implementation matches admitted scope and coupled artifacts (`tests`, `docs`, `STATUS.md`) are synchronized;
- fresh verification passed with zero hidden `NOT_RUN`, `ERROR`, `UNKNOWN`, or reward-hacking suppressions;
- reviews, receipts, merge decisions, and release digests bind to the **same exact revision**;
- `DoneClaim` records explicit `does_not_prove[]` limits, rollback path, and human owner sign-off.
