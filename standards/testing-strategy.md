# Agentic Testing Strategy

**Status**: accepted baseline
**Updated**: 2026-11-20

## Goal

Testing should protect product behavior, cross-repository contracts, deployment paths, and governance documentation from drift.

## Test Layers

| Layer | Owner | Purpose |
|-------|-------|---------|
| Unit tests | owning repo | Validate functions, classes, local modules |
| Integration tests | owning repo | Validate subsystems and adapters |
| Contract tests | both producer and consumer repos | Validate cross-service payloads and compatibility |
| End-to-end tests | owning or delivery repo | Validate user-facing workflows |
| Deployment smoke tests | owning or delivery repo | Validate install, boot, health, and minimal workflow |
| Security tests | owning repo | Validate auth, isolation, redaction, permissions |
| Documentation checks | governance & owning repos | Validate links, required docs, no placeholders |

## Cross-Product Contract Testing

Every implemented integration should have:

- golden payload fixtures
- schema validation
- consumer parsing tests
- idempotency tests
- unauthorized or invalid payload tests
- backward compatibility tests for supported versions

## Select Gates from the Affected Closure

Select tests from the actual diff, its import/dependency closure, and contract
boundaries—not mechanically from whether a path is under `frontend` or
`backend`. The default rules are:

- For frontend-only presentation, styling, or local interaction changes that
  do not alter a public contract/API, schema, generated client, auth/permission
  rule, feature flag, shared state, serialization format, WebSocket contract,
  SSR/BFF behavior, or shared build configuration, run frontend lint/type
  checks and focused unit/component tests. A full backend unit suite is not
  required by directory label alone.
- For backend-only internal implementation changes that do not alter any of
  those shared boundaries, run focused backend unit tests and relevant backend
  integration tests. A full frontend suite is not required by directory label
  alone.
- When either side changes one of those shared boundaries, treat frontend and
  backend as one affected closure. Run the relevant producer/consumer contract
  tests, backend parser/service unit or integration tests, frontend consumer
  unit/component/integration tests, and at least one browser/API journey.
- If the closure is uncertain or the change crosses a security or release
  boundary, run the complete affected suites on both sides; directory appearance
  is not dependency evidence.

Cross-layer coverage must include schema validation, consumer parsing, supported
version compatibility, idempotency, and unauthorized/invalid payloads. A missing
browser, fixture service, or dependency is `NOT_RUN` and must make the candidate
command non-zero; it is not a successful skip.

Test cost may be reduced by layering without reducing boundary evidence: retain
at least one end-to-end wiring proof for each expensive real evaluator, source
closure, or browser journey, and use explicit deterministic narrow fixtures only
for orthogonal composition cases. Every test double must declare its scope and
be independently guarded by the real runner, dependency-integrity checks, and a
representative mutation test.

Path-based selection is a fast-feedback optimization for pull requests only.
Periodic full suites and release compatibility gates remain mandatory and must
not be replaced by affected-path filtering.

### Classifier and shadow-mode contract

A product repository may implement deterministic affected-closure advice, but
the classifier itself is an assurance mechanism and must satisfy all of these
rules:

- Derive scope only from exact resolved base and head commit IDs and a
  NUL-delimited, no-rename name-status diff. Agent prose, PR labels, commit
  messages, environment hints, and an uncommitted working tree cannot narrow
  the result.
- An unknown or malformed path/status, empty diff, security, migration,
  governance, CI, deployment, or release boundary must fail closed to the
  complete affected suites. A narrower classification requires an explicit,
  tested rule; an unclassified path never inherits a side by default.
- Emit stable machine-readable output with ordered changes/reasons and no
  timestamp, username, hostname, or machine-local path. Invalid Git input must
  emit a bounded full-closure error result and return non-zero.
- Every recommended suite identifier must resolve to a real repository
  entrypoint. The classifier recommends closures; it does not copy a second
  implementation of pytest, build, integration, or browser selectors.
- Shadow mode is observational only. It must not select or skip tests, feed a
  narrowing condition into existing jobs, or change required status, branch
  protection, bypass, review, or merge authority.
- Shadow advice cannot replace periodic full suites or release compatibility
  gates. Promotion requires representative violating and legal-control
  mutations, measured false-negative/false-positive samples, independently
  reviewed path coverage, and a separate trusted-enforcement decision.
- An explicit gate missing Node/npm, browser, fixture service, local
  dependencies, or another mandatory prerequisite must exit non-zero with a
  bounded missing-requirement inventory. Once preflight passes, the real
  repository command remains authoritative; successful skip text is forbidden.

Classifier output, job presence, and exact-head success are candidate or
PR-controlled evidence and are not trusted enforcement. A mechanism-changing
PR requires the architecture/contract owner and a second independent mechanism
reviewer.

The platform carrier for this advice is the closed
[Affected-Test Closure Candidate Contract](testing-strategy/affected-closure-contract.md).
It fixes exact-revision/error semantics, stable classifications, deterministic
ordering, and the rule that `docs_only` cannot expand into frontend/backend or
full suites. Product repositories must add their own real Git-diff and suite
entrypoint wiring proof; the platform checker does not duplicate those
selectors.

Docs-only changes use `make check` and do not mechanically
run complete frontend or backend suites. If the documentation change edits a
schema, generated contract, architecture/enforcement surface, shared build, or
release input, the changed boundary—not the `.md` suffix—determines the affected
closure and its additional deterministic gates. A repo-local document that
changes executable configuration, generated output, or a public contract follows
the same closure rule.

## Minimum Gates by Change Type

| Change type | Required gate |
|-------------|---------------|
| Docs-only change | `make check` |
| Repo-local code change | unit and relevant integration tests |
| Cross-repo contract change | producer and consumer contract tests |
| Deployment change | smoke test or deployment verification |
| Security-sensitive change | relevant auth, isolation, redaction, or permission tests |
| Release candidate | full test suite plus release smoke checks |

## Gate Integrity

A gate that exists but does not run, does not cover the changed files, or can
be quietly loosened gives false confidence. Product repositories apply these
rules to their own lint, type, test, and budget gates:

- Every gate has a written spec: what it checks, which files it covers, which
  bypasses or suppressions it accepts, which event triggers it, and whether a
  red result blocks merge.
- A new or changed gate is proven by a planted violation that turns it red and
  an adjacent legal case that stays green. Zero collected tests, an all-skipped
  run, or a job that did not trigger is not a pass; never collapse `NOT_RUN`,
  `FLAKY`, `ERROR`, or `UNKNOWN` into `PASS`.
- Budgets, baselines, and suppression lists only decrease. Do not downgrade a
  rule's severity to get a change through. Raising a budget is its own PR with a
  reason and an owner, never a side effect of a feature PR.
- A check that must block merge is a required status check in branch
  protection. A green job that is not required is advisory; see the
  [External Enforcement Evidence Candidate Contract](testing-strategy/enforcement-evidence-contract.md)
  for how required contexts are observed.
- An audit or scanner finding is reproduced against current code before it is
  fixed or reported as a defect.

## Frontend Test Evidence

Unit and component tests with hand-written data miss the defects that reach
users most often: wrong API shapes, large or malformed data, and cross-layer
state. Frontend changes add:

- Fixtures and mocks built from the real API shape, preferably generated from
  the backend schema, plus cases with large volumes, missing fields, and
  malformed values.
- No mocking of the transport or serialization layer on upload, download,
  content-type, or serialization paths. Assert what actually goes over the wire.
- Browser acceptance for user-visible changes, stated against four questions:
  1. Which level is proven: rendered, reachable from real navigation, correct
     with real data, or still correct at production data volume?
  2. Was it exercised in a browser along the real user journey, not only in a
     terminal test run?
  3. For a disabled or unlicensed feature, are entry, direct route, backend
     API, and flag endpoint all consistent?
  4. When a read fails, does the UI show unknown or error rather than a
     plausible value, and does each displayed meaning come from one field?

## Vibe Coding Verification Rule

Agents and humans must report the command that proves the claim. Do not report a task as complete from reasoning alone.

Good report:

```text
Ran `make check`; it completed with exit code 0.
```

Bad report:

```text
Docs should be fine.
```

## Documentation Checks

This repository provides a lightweight documentation check:

```bash
make check
```

This check verifies required files, scans for unresolved placeholders, and checks local Markdown links.

## External Enforcement Evidence Candidate Contract

The [External Enforcement Evidence Candidate Contract](testing-strategy/enforcement-evidence-contract.md)
defines a read-only, normalized carrier for an independently observed GitHub
ruleset. It is deliberately candidate-only: every report is
`authority=candidate` and `trusted=false`, and a committed fixture or a green
checker does not prove the current remote ruleset.

The checker fails closed when required status contexts are missing, last-push
approval is disabled, an unconditional bypass actor is present, the source does
not match the repository/ruleset, the default branch is not covered, or the
report is malformed or non-deterministic. It does not call GitHub, modify
protection, select or skip product tests, or authorize merge/release. The
external observer must retain the raw response and its digest; missing
observation is `NOT_RUN`, not a successful skip.

Run the bounded local contract gate with
`make governance-enforcement-evidence-check`; `make check` invokes the same
target. Exact-head CI, job presence, `CODEOWNERS`, and candidate output remain
separate from trusted enforcement and require an architecture/contract owner
plus an independent mechanism reviewer.
