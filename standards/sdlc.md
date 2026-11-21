# Agentic SDLC Standard

**Status**: accepted baseline
**Updated**: 2026-11-20

This SDLC is designed for single- and multi-repo Vibe Coding projects where humans and coding agents collaborate across repository boundaries.

## Lifecycle

1. Intake
2. Design
3. ADR when needed
4. Implementation plan
5. Branch setup
6. Test-first or test-pinned implementation
7. Review
8. Release
9. Post-release verification
10. Retrospective

## Intake

Every non-trivial task should define:

- business goal
- protected primary flow
- affected repositories
- affected contracts
- affected product boundaries
- owner
- expected verification
- rollback or stop condition

## Design

Design is required before implementation when the change:

- affects more than one repository
- changes architecture or product boundaries
- changes a contract
- changes deployment or operational behavior
- touches security, privacy, or customer evidence

Small product-local changes can use product-local issue or PR descriptions.

Design work must respect core engineering boundaries: prefer explicit runtime configuration over hardcoded defaults, use managed queue semantics for durable async work, prioritize stability over unrequested feature expansion, treat repository/service boundaries as execution constraints, require explicit scope for UI changes, prefer deterministic or evaluatable algorithms over LLM judgment, and validate LLM outputs against closed schemas and policy gates before execution.

## ADR Gate

An ADR is required when a decision affects two or more repositories or changes platform authority.

## Implementation Plan

Implementation plans should be broken into tasks that can be reviewed independently. Each task should state:

- files touched
- tests added or changed
- commands to run
- expected result
- documentation update

## Testing Gate

No change is complete without fresh verification evidence. At minimum:

- product-local tests for product-local changes
- contract tests for cross-product contracts
- documentation checks for docs changes
- smoke or deployment verification for release and delivery changes

See [testing-strategy.md](testing-strategy.md).

Code Health candidate work follows the same test-first boundary: publish the
closed contract and negative fixtures before product adapters, keep candidate
checks non-writing, and preserve periodic/full/release compatibility suites.
F2 evaluates an exact base/head pair, loads policy/baseline from exact trees,
and reports unsupported language adapters as `NOT_EVALUATED`. Docs-only PRs
remain on `make check` and do not mechanically run complete frontend/backend
suites; an actual shared contract, architecture/enforcement, build, or release
boundary still expands the closure. A backend-only internal change does not
mechanically trigger the full frontend suite unless the affected-contract
closure crosses a shared boundary.

## Governed UI Delivery Gates

Products adopting UI Assurance use six monotonic gates:

| Gate | Decision boundary |
|---|---|
| `A0 Task Admission` | Approve task, base, scope, surfaces, risk floor, context, and stop conditions |
| `A1 Local Feedback` | Give fast advisory feedback without issuing merge authority |
| `A2 PR Candidate` | Recompute actual diff and obligations, then retain candidate evidence |
| `A3 Trusted Merge Guardian` | Independently evaluate exact PR-head and merge-group revisions against protected policy and reviews |
| `A4 Preview and Release` | Test and admit the same immutable artifact digest |
| `A5 Post-release` | Append canary, escape, blockage, flake, latency, and effectiveness observations |

Unavailability is monotonic: an enforced `A3` blocks instead of falling back to
candidate CI, and `A4` blocks instead of shipping an untested rebuild. A new
push invalidates old head evidence. A PR that changes its validator, workflow,
schema, test, CODEOWNERS, PR template, or agent instruction is not
self-attesting and requires the architecture or contract owner plus a distinct
mechanism reviewer.

## Review Gate

Every PR should explain:

- what changed
- why it changed
- how it was validated
- which primary flows were protected and which may be affected
- whether product boundaries, async-task semantics, or UI scope changed
- risks and rollback
- docs updated or why not needed

For Vibe Coding work, include agent context and any generated assumptions that human reviewers need to check.

## Release Gate

Release candidates should have:

- version or tag
- compatibility statement
- release notes
- test evidence
- migration notes when contracts changed
- rollback notes

## Definition of Done

A task is done only when:

- implementation matches the accepted design or documented deviation
- tests or checks passed freshly
- docs are updated in the correct authority location
- no unresolved placeholders remain
- risk and rollback are known
- owner accepts the change
