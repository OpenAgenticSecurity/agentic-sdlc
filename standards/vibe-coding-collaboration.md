# Vibe Coding Collaboration Standard

**Status**: accepted baseline
**Updated**: 2026-11-20

Vibe Coding can move fast only when context, ownership, and verification are explicit. This standard applies to human engineers and coding agents collaborating in single- or multi-repo projects.

## Core Rules

- Keep shared cross-repo architecture and contract decisions in your platform docs repo (or dedicated `docs/architecture/`).
- Keep service/product implementation details in the owning repository.
- Never make silent broad refactors.
- Never change a shared contract without updating contract docs and tests.
- Never claim completion without fresh verification output.
- Prefer small, reviewable PRs over large mixed changes.
- Preserve user or teammate changes you did not make.
- Stability first: protect primary flows, shipped features, deployment paths, and user-visible behavior.
- Service and plane boundaries are execution constraints: do not collapse data custody, policy/control, model advice, and tool execution into one unguarded path.
- Do not opportunistically change frontend UI unless it is explicitly in scope.

## Context Pack for Agent Tasks

Every agent task should include or discover:

- repository and branch
- exact goal
- files or modules in scope
- files or modules out of scope
- protected primary flow
- affected product boundaries
- UI scope: in-scope or out-of-scope
- relevant product docs
- relevant platform docs
- expected tests
- stop conditions

For repository-local coding work, agents should first read the repo's AI context files defined in [ai-coding-context.md](ai-coding-context.md). For cross-repository work, agents should also read the organization's shared architecture, integration contracts, and [sdlc.md](sdlc.md).

## Multi-Agent Work

Use parallel agents only when work is independent and write scopes do not overlap. Assign file ownership explicitly.

Examples of safe split:

- one agent updates data-plane documentation
- one agent updates API adapter tests
- one agent reviews contract fixtures

Examples of unsafe split:

- two agents edit the same contract file
- one agent changes a schema while another changes consumers without coordination
- one agent refactors product boundaries while another writes docs from old assumptions

Multi-agent work must also follow [multi-ai-git-workflow.md](multi-ai-git-workflow.md): one task, one branch, one worktree, one owner.

## Cross-Layer Consistency and Shared-Layer Fixes

Defects that agents reintroduce most often do not sit inside one file. They sit between layers, or in a shared layer that each change works around locally.

- A disabled or unlicensed feature is disabled at every layer at once: navigation entry, direct route, backend API, and any public feature-flag endpoint. One test asserts every layer from the same flag or registry, so a newly added layer cannot be left out.
- Wiring is part of the change. A new API ships with its caller, and a new setting or toggle ships with the runtime code that reads it. An endpoint nothing calls, or a toggle nothing reads, is not complete.
- One displayed meaning has one authoritative field. Two views deriving the same status from different fields, or a client re-deriving what the backend already decided, is a defect even while both happen to agree.
- The second occurrence of a defect is fixed in the shared layer (request client, serializer, state store, base component), not with another local workaround. The second copy of a helper or component is pulled back into the shared layer before a third appears.
- A code comment that explains around a shared-layer defect records an open bug. Link or open an issue; the comment is not the fix.
- When the same component or flow needs a third fix within a week, stop patching. Re-model its state and data flow, and add a test for the failure class before the next fix.

## Human Review Focus

Human reviewers should check:

- whether the agent respected scope
- whether the agent protected primary flows and provided stability evidence
- whether the agent respected product boundaries and UI scope
- whether assumptions match product reality
- whether tests prove the right behavior
- whether a new fallback (`?? 0`, `|| []`, a default parameter, a `catch` that only logs) can make a failed read look like valid data
- whether a fix repeats a local workaround that belongs in a shared layer
- whether docs were updated in the right authority location
- whether generated prose overclaims maturity

## Forbidden Patterns

- duplicating product-local runbooks into a shared standards repo
- copying large product architecture dumps into shared governance docs without distilling decisions
- changing root workspace Git state
- using generated text as current truth without owner review
- mixing marketing pitch material with engineering authority docs
- changing UI while fixing backend, queue, deployment, MCP, or data-model issues unless UI is explicitly in scope
- collapsing data custody, advisory logic, policy/control gates, and external tool adapters into a single unguarded implementation

## Status Truth Rule

For repository implementation reality, trust the local `docs/architecture/STATUS.md` over older roadmap, architecture, or generated docs. If a module is marked deleted or design-only, do not assume it exists without reading source.

## Context Drift Rule

If work changes implementation reality, update the repo-local status/context files before closing the task. If the change affects shared cross-repo boundaries, update the shared docs in the same PR batch.

## End State Rule

At task completion, the default handoff state is a clean latest default branch in every touched repository. If local-only WIP makes switching or fast-forwarding unsafe, preserve that WIP and report why the repo did not end on its default branch.

## Handoff Format

Use this handoff when a task crosses people or agents:

```text
Goal:
Repos:
Branch:
Files changed:
Contracts affected:
Boundaries affected:
Protected flows:
UI scope:
Tests run:
Docs updated:
Risks:
End state:
Next owner:
```

## Batch migration acceptance

Before replacing a shared component, helper or contract, enumerate production
consumers, owner, migration state, justified exceptions and acceptance tests. A new
abstraction and green leaf tests do not complete the consumer migration. Preserve
runtime call-time dependency binding, transaction/ownership boundaries and failure
semantics; test the actual caller after extraction.

Independent branches also need combined-tree verification for shared imports,
locales, schemas, dependency locks and bundle budgets. Freeze baseline, review head
and merged tree identities separately. No-growth typing/lint/complexity gates do
not mean existing debt is zero. Compatibility deletion needs external callers,
runtime-use observations, compatibility windows, data disposition and rollback
proof in addition to a static zero-caller search. Local performance improvements
require the same workload and remain distinct from production SLO evidence.
