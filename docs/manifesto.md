# OpenAgenticSecurity Manifesto: Security Engineering in the Age of AI Agents

**Status**: foundational essay (concise English edition; [manifesto.zh.md](manifesto.zh.md) includes an extended multi-repo case-study appendix)
**Updated**: 2026-11-20
**Chinese Original**: [manifesto.zh.md](manifesto.zh.md)

> Existing security governance, architecture review, defense in depth, identity,
> and cryptographic infrastructure did not become obsolete because AI agents
> arrived. What changed is the **executing actor**, the **trust boundary**, and
> the **speed**. This essay explains how enduring security engineering
> principles re-anchor into an Agentic SDLC, and which controls must become
> machine-verifiable.

## 0x00 Enduring Principles Did Not Expire — The Actor Changed

Security architecture sits at the intersection of business intent, application
logic, network topology, deployment, and operations. Architecture review is not
handing out a checklist after a meeting; it is identifying risk from business
and data flows, specifying controls, and verifying that those controls actually
land in production.

Traditional security governance separates four layers:

- **Policy** — principles, scope, and non-negotiable baselines.
- **Standard** — technical baselines translating policy into testable rules.
- **Procedure / SOP** — who does what under which conditions.
- **Exception** — time-bounded, approved deviations bound to an owner and
  compensating controls.

Those layers close into a continuous feedback loop:

```text
Business & Risk
  -> Governance & Authoritative Standards
  -> Scenario-Specific Design
  -> Engineering Implementation
  -> Independent Verification & Continuous Operations
  -> Feedback, Remediation, or Explicit Risk Acceptance
```

AI agents do not invalidate this loop. What disappears is the set of **implicit
boundaries** that organizational handoffs, human waiting time, and system
separation used to supply for free.

## 0x01 Agents Turn Implicit Boundaries into Explicit Control Problems

In a human-only SDLC, requirements, design, coding, testing, release, and
operations happen across different people, times, and systems. That friction
implicitly enforced separation of duties: authors rarely approved their own
risk, QA re-observed outputs independently, and production credentials did not
sit on every developer's laptop.

An AI agent can cross every stage in a single session: write code, pick tests,
explain away failures, open a PR, trigger deployment, and declare "done."

Three terms are worth keeping distinct:

- **AI-assisted SDLC**: humans drive the lifecycle; AI assists on isolated tasks.
- **AI-native SDLC**: workflows and artifacts are redesigned around AI.
- **Agentic SDLC**: an actor with tools, state, identity, permissions, and
  side-effect capabilities operates inside trust boundaries.

This repository addresses the **control problem of Agentic SDLC** — answering
four plain questions with verifiable facts instead of prose:

1. **Who authorized this action?**
2. **What exact objects and revisions did it affect?**
3. **Who verified the result, using which fixed rules?**
4. **Who owns failure, revocation, and recovery?**

| Implicit Boundary in Traditional SDLC | What Changes with Agents | Explicit Control Required |
|---|---|---|
| Role division implies identity & accountability | One account hides humans, agents, runners, retries, and handoffs | Separate human authority, agent/session/attempt, workload identity, and evidence issuer |
| Stage handoffs trigger fresh checks | One agent crosses multiple stages continuously | Every state transition defines inputs, outputs, entry criteria, and valid failure exits |
| Human latency limits blast radius | Agents create high-frequency parallel side effects | Task-scoped grants, rate/budget limits, and revocable paths |
| Engineers curate their own context | Agents ingest repos, web pages, issues, and tool outputs | Provenance, authority, digest, freshness, and applicability must be verifiable |
| Review is independent from the author | Agents can edit implementation, tests, CI, and validators together | Fixed rules, protected verification environments, independent review of mechanism changes |
| Ops independently checks deploys | Agents treat exit-code-0 scripts as runtime truth | Artifact provenance, live workload identity, config, business semantics, and rollback read-back |
| Humans decide when to stop | Agents retry, downgrade, or game checks until green | `NOT_RUN`, `HITL`, `FAILED`, cancellation, handoff, and revocation are first-class states |

## 0x02 Re-Anchoring Security Engineering Principles

Security left-shift cannot move *every* proof to the left. Whether an artifact
was actually deployed, runs under the right workload identity, satisfies
business semantics, and rolls back cleanly can only be proven in live runtime.
The operating posture for Agentic SDLC is three-part:

```text
Security by Default : safe boundaries out of the box (read-only default, isolated worktrees, minimal tools, short-lived identity)
Shift Left          : admission, scope, policy, data classification, exact revision, and dependency closure before side effects
Runtime Closure     : live verification of deployed identity, business semantics, revocation, and recovery
```

### 1. Standards Must Be Machine-Usable, but Authority Never Belongs to Prompts

`AGENTS.md`, `CLAUDE.md`, editor rules, and skills are **ergonomic projections**
of standards into coding tools — never the authority root. Authoritative rules
still answer: who approved them, which exact version applies, where they apply,
when they expire, and how exceptions are granted. An agent cannot grant itself
scope expansion, waive mandatory obligations, or turn a temporary bypass into a
permanent rule via prose.

### 2. Defense in Depth Is Not "Add a Second Agent"

Having Model B review Model A does not create defense in depth if both share
the same stale checkout, poisoned context, and candidate validator. Independent
layers require distinct privileges and failure modes:

```text
Task Admission -> Human Authority & Task Grant -> Agent / Workload Identity
  -> Tool Gateway & Sandbox -> Scoped Diff & Branch Protection
  -> Independent Verification -> Artifact Admission
  -> Runtime Identity & Read-Back -> Revocation, Rollback & Recovery
```

Controls themselves must be protected. Any PR modifying its own validators,
workflows, schemas, policies, `CODEOWNERS`, or agent instructions is **never
self-attesting**.

### 3. Identity & Cryptographic Infrastructure Form One Trust Chain

```text
Human Authority -> Task-Scoped Grant -> Agent / Session / Attempt
  -> Runner Workload Identity -> Short-Lived Cert / Secret Lease
  -> Tool & Service Call -> Audit, Expiry, Revocation & Rotation
```

Raw long-lived secrets never belong in prompts, chat transcripts, or agent
memory. Agents receive opaque `SecretRef` metadata or bounded short-lived
leases resolved strictly inside workload boundaries backed by Vault/KMS/HSM.

### 4. Context and Evidence Are Data-Security Assets

Prompts, repo slices, tool outputs, traces, screenshots, receipts, and agent
memory traverse the full data lifecycle (collect, transmit, store, use, share,
destroy). Encryption in transit is not proof of data security without identity,
classification, authorization, retention bounds, and verifiable disposal.

## 0x03 Controls That Must Be Machine-Verifiable

Machine-verifiable does not mean delegating business judgment to machines.
Humans retain authority over goals, risk acceptance, waivers, and production
releases. Machines ensure applicable rules cannot be forgotten, revisions cannot
be silently swapped, and missing evidence cannot be reported as green.

Never collapse results into `passed=true`. Preserve explicit non-passing states:
`PASS`, `FAIL`, `NOT_RUN`, `FLAKY`, `ERROR`, `UNKNOWN`, `CONFLICT`,
`NOT_APPLICABLE`, `NOT_EVALUATED`, and `WAIVED_WITH_DEBT`.

Never blur the **Five-Layer Fact Chain**:

```text
Evidence
  -> VerificationResult
  -> Receipt
  -> Decision
  -> Outcome
```

- **Evidence**: raw logs, screenshots, traces, artifacts, source windows.
- **VerificationResult**: deterministic judgment over evidence under fixed rules.
- **Receipt**: result cryptographically/canonically bound to task, subject,
  exact revision, environment, and policy.
- **Decision**: state transition made by an authorized principal based on receipts.
- **Outcome**: actual change observed in the real world after deployment.

> A screenshot is not deployment authorization; a green PR job is not a trusted
> verification receipt; a merged PR is not a verified production outcome.

## 0x04 Matching Control Strength to Risk & Infrastructure

Do not wait for an enterprise platform before adopting Agentic SDLC controls:

- **L0 Solo / Small Project**: exact base revisions, isolated git worktrees,
  honest `STATUS.md`, explicit `NOT_RUN`/`FAIL` reporting, reproducible commands.
- **L1 Team**: managed issue claims with owned-path conflict detection,
  affected-test closure contracts, non-writing drift checks, candidate CI.
- **L2 Governed / High-Assurance**: independent ruleset enforcement evidence,
  two-reviewer non-self-attestation boundaries, content-addressed policy
  bundles, digest-bound `DoneClaim` & verification receipts, short-lived
  workload identity, and immutable artifact promotion.

When infrastructure is missing, **shrink agent permissions rather than using
prompts to pretend controls exist**.

## 0x05 Definition of Done

An agent-assisted change is done only when derived facts match its risk claim:

- Task, identity, scope, risk, acceptance criteria, dependencies, and stop
  conditions were admitted by an authorized owner;
- Actions stayed inside grant boundaries without leaking secrets into context
  or logs;
- Actual diff, affected closure, and validation obligations were computed
  independently without hiding `NOT_RUN`, `ERROR`, `UNKNOWN`, or `CONFLICT`;
- Reviews, receipts, merge decisions, and release artifacts bind to the **same
  exact revision**;
- Deployment claims carry artifact provenance, live runtime identity, business
  semantic checks, and rollback refs;
- Exceptions, residual risks, handoffs, and temporary paths carry explicit
  owners and expiry;
- Grants, short-lived certificates, secret leases, child processes, and remote
  actions are expired, revoked, or explicitly handed off.

**Done is a derived fact — never a boolean self-reported by an agent.**
