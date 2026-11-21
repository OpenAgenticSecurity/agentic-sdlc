# Standards

**Status**: accepted baseline
**Updated**: 2026-11-20
**Chinese**: [README.zh.md](README.zh.md)

This directory owns the 7 core Agentic SDLC standards and 2 lightweight closed
JSON Schema contracts directly runnable in any repository.

## Core Agentic SDLC Standards

| File | Purpose |
|------|---------|
| [sdlc.md](sdlc.md) | Lifecycle, monotonic gates (`A0`–`A5`), and Definition of Done |
| [secure-vibe-coding.md](secure-vibe-coding.md) | Secure-by-default AI coding invariants (auth/fail-closed, injection/SSRF/path/ReDoS, secrets & crypto, supply chain, agent boundaries, negative security tests, `deps` carrier) |
| [ai-coding-context.md](ai-coding-context.md) | `AGENTS.md`, `CLAUDE.md`, `VIBE_CODING_CONTEXT.md`, and `STATUS.md` truth rules |
| [vibe-coding-collaboration.md](vibe-coding-collaboration.md) | Human–agent collaboration, cross-layer consistency, and shared-layer fix rules |
| [multi-ai-git-workflow.md](multi-ai-git-workflow.md) | Multi-human / multi-AI Git worktrees, Managed Issue Claims, and diverged-main SOP |
| [agent-issue-pr-loop.md](agent-issue-pr-loop.md) | Auditable issue discovery, scope freeze, PR linkage, and closure loop |
| [testing-strategy.md](testing-strategy.md) | Test layers, affected-closure selection, gate integrity, and frontend/backend evidence |

## Lightweight Executable Contracts (Closed Schemas & Mutation Fixtures)

| Control Lane | Specification | Deterministic Checker |
|---|---|---|
| **Affected-Test Closure** | [testing-strategy/affected-closure-contract.md](testing-strategy/affected-closure-contract.md) | `scripts/check-affected-closure.py` |
| **External Enforcement Evidence** | [testing-strategy/enforcement-evidence-contract.md](testing-strategy/enforcement-evidence-contract.md) | `scripts/check-enforcement-evidence.py` + `scripts/observe-github-ruleset.py` |

> **Need full L2 protocol schemas for UI Assurance (8 schemas) and Code Health Ratchet/Retirement (10 schemas)?**
> Those enterprise Guardian contracts live in the sibling repository
> `OpenAgenticSecurity/assurance-contracts` to keep `agentic-sdlc` lean and
> immediately runnable.

## Rule

Adopting repositories may add stricter local rules, but should not weaken these
core safety, verification, or non-self-attestation invariants.
