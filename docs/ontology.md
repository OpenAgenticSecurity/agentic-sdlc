# Agentic SDLC Ontology: Nine Entities & Five Axioms

**Status**: foundational reference
**Updated**: 2026-11-21
**Chinese**: [ontology.zh.md](ontology.zh.md)

Coding agents rarely fail because they forgot a checklist item in prose. Across
**15,384 real Claude Code & Codex engineering turns** and **200B+ tokens** of
multi-repo production practice, recurring failures stem from **category
errors** — treating fundamentally different engineering objects as if they were
the same thing (equating session memory with code reality, a single file edit
with a complete coupled change, a summary with evidence, or a code default with
live production configuration).

This one-page ontology defines the **9 first-class entities** and **5 axioms**
that unify every standard, checklist, skill, and deterministic script in
`OpenAgenticSecurity/agentic-sdlc`.

---

## 1. Nine First-Class Entities

| # | Entity | What It Actually Is | What Agents Mistake It For |
|---|---|---|---|
| 1 | **`Intent & Scope`** | Admitted goal, `in_scope`, `out_of_scope`, protected primary flows, and stop conditions | Casual chat prompt or silent opportunistic refactors |
| 2 | **`RealityAnchor`** | Verifiable ground truth: exact 40-char Git SHA, live DB schema, `STATUS.md`, read-only runtime probe | Model priors, stale design docs, or conversation memory |
| 3 | **`Workspace & Revision`** | Exact primary checkout vs isolated task worktree, dirty working-tree bytes vs committed `HEAD` object | Bare branch name (`main` or `feat/...`) |
| 4 | **`ArtifactGraph`** | Code linked by explicit edges to coupled tests, contracts, 3-layer configs, docs, and `STATUS.md` | Single-file diff in isolation |
| 5 | **`Execution & Effect`** | Policy-gated action producing side effects with explicit `RESULT_UNKNOWN`, TTL, and compensation paths | Pure model reasoning or optimistic "fire and forget" |
| 6 | **`Evidence`** | Reproducible raw observation: exact command, exit code, primary output, SHA-256 digest, independent readback | Agent narrative summary or `"done": true` claim |
| 7 | **`Gate & Verifier`** | Independent mechanism with pinned version, declared coverage, legal non-green states, and negative mutations | Candidate producer or self-attesting PR check |
| 8 | **`Authority & Decision`** | Authorized principal or protected GitHub Ruleset advancing `Merge`, `Release`, or `Waiver` | Model confidence score or local green run |
| 9 | **`Lesson & Rule`** | Incident graduated into a failing negative mutation test and deterministic gate | Unindexed chat transcript or manual `/learn` note |

---

## 2. Five Ontological Axioms

### Axiom 1 — Reality Overrides Memory (`RealityAnchor > SessionMemory`)
Whenever conversation history, older docs, or model priors disagree with a
`RealityAnchor` (freshly fetched `origin/<default>`, real caller→constructor
trace, `STATUS.md`, or live read-only observation), the `RealityAnchor` wins
unconditionally.

- **Enforced here**: `standards/ai-coding-context.md`, `skills/multi-agent-git-flow`,
  `skills/audit-production-readiness` (7 evidence disciplines & 3-layer defaults).

### Axiom 2 — Coupled Artifact Closure (`ArtifactGraph`)
Editing a primary node in `ArtifactGraph` (source code, API route, schema,
config template, or enforcement script) leaves the task ontologically
**`PARTIAL`** — never `DONE` — until every required coupled edge (tests /
negative security tests, consumer contracts, 3-layer config notes, docs, and
`STATUS.md`) is updated or explicitly waived with an auditable reason.

- **Enforced here**: `scripts/check-change-sync.py`, `profiles/L1-team/agentic-sync.example.json`,
  `standards/testing-strategy/affected-closure-contract.md`, `checklists/handoff.template.md`.

### Axiom 3 — Non-Collapsing State Machine
`PASS`, `FAIL`, `NOT_RUN`, `UNKNOWN`, `RESULT_UNKNOWN`, `FLAKY`, `CONFLICT`,
`ERROR`, `NOT_APPLICABLE`, `NOT_EVALUATED`, and `HITL` are mutually exclusive
first-class states. Mapping any non-passing state into a boolean `true` or a
plausible fake fallback (`?? 0`, `|| []`, `0 tests collected` exiting 0) is an
ontological violation.

- **Enforced here**: `skills/done-claim-verify`, `checklists/fake-done-dereference.md`,
  `scripts/audit-repo.py` (`OAS-JS-02`, `OAS-SVC-01`, explicit `NOT_RUN`),
  `standards/reliable-and-performant-coding.md`.

### Axiom 4 — Producer/Judge Separation (Non-Self-Attestation)
The actor that produces a `Patch` never holds authority to issue the final
`Decision` or certify changes to its own `Gate`. Any PR touching workflows,
`action.yml`, schemas, checkers, `CODEOWNERS`, tests, or agent instructions
must be decided across an external protected boundary.

- **Enforced here**: `profiles/L2-governed/github-ruleset.import.json`,
  `scripts/observe-github-ruleset.py`, `scripts/audit-repo.py --github`,
  `profiles/L2-governed/mechanism-review-checklist.md`.

### Axiom 5 — Asymmetric Knowledge Evolution
Every production incident or audit finding must graduate into a reproducible
negative test or deterministic gate. Automated learning or rule synthesis may
**only tighten constraints, add context, or surface blind spots** — never
auto-expand permissions, remove approvals, downgrade gate severity, or add
permanent allowlists.

- **Enforced here**: `checklists/production-readiness-audit.md`, `evals/`,
  `scripts/run-evals.py`, `CONTRIBUTING.md`.

---

## 3. Honest Limits (`does_not_prove`)

An ontology makes hidden boundaries explicit; it does not replace engineering
execution. Adopting these terms without deterministic checks (`audit-repo.py`,
`check-change-sync.py`, fail-closed CI, protected GitHub Rulesets, and real
integration tests) leaves every axiom unenforced.
