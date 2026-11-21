# OpenAgenticSecurity Maturity & Trust Boundaries

**Status**: canonical reference
**Updated**: 2026-11-21
**Chinese**: [MATURITY.zh.md](MATURITY.zh.md)

OpenAgenticSecurity follows one non-negotiable rule: **never claim conclusions
beyond verified evidence.** This document records the exact maturity level,
verified scope, and explicit non-goals of every component in `agentic-sdlc`.

## Maturity Tiers

| Tier | Name | Meaning |
|---|---|---|
| **L0** | Local Guardrails | Local Git/worktree isolation, implementation-truth context (`STATUS.md`), Secure Vibe Coding rules, empirical checklists, and repo compliance checks. |
| **L1** | Candidate / Advisory Verification | Closed JSON Schemas, deterministic checkers, negative mutation fixtures, and exact-head PR-controlled CI (**never self-attesting**). |
| **L2** | Trusted Enforcement Pattern | Externally protected runners, immutable branch/ruleset controls, independent two-reviewer approval for mechanism changes, and the **`deps`** local carrier (lifecycle hooks, AaC ratchet, receipts) plus `sealed-data` for dataset sealing. |

## Capability Maturity Matrix

| Control Lane | Location | Current Tier | Deterministically Verified Here | Explicit Non-Goals / Adopter Responsibility |
|---|---|---|---|---|
| **Bootstrap, Self-Audit, Reusable Action, Shared Deps & Git Guardrails** | `BOOTSTRAP.md`, `action.yml`, `scripts/bootstrap.sh`, `scripts/audit-repo.py`, `scripts/run-evals.py`, `scripts/workspace-git.py`, `scripts/agent-claim.py`, `scripts/link-shared-node-deps.mjs` | **L0–L1** | Safe non-overwriting bootstrap (symlink-guarded) with fail-closed `make agent-check`, 5 language CI templates (Python/TS/Rust/Go/Java), zero-dep polyglot repo self-audit (`audit-repo.py` + `action.yml` + 14-case eval suite), reversible managed Git hooks forwarding all client hooks, lease-expiring issue claims, lockfile-keyed Node store | Remote GitHub branch protection, cross-host distributed locking |
| **Empirical, Security, Ops & Readiness Checklists** | `checklists/`, `standards/secure-vibe-coding.*`, `examples/` | **L0–L1 Baseline (+ `deps` Carrier)** | 8 checklists + `DoneClaim`/`Handoff` templates + runnable starter Playwright & backend contract gates (`examples/`); security red lines baked into L0 `AGENTS.md`, PR template & Skills | Prose decays under compaction — graduate recurring defects into lint/test gates & `deps` |
| **Affected-Test Closure Contract** | `standards/testing-strategy/affected-closure-contract.*`, `scripts/check-affected-closure.py` | **L1 Candidate** | Closed schema, deterministic ordering, fail-closed `full` boundaries, `docs_only` non-expansion, adopter `--report`/`--catalog` CLI, positive/negative mutation suite | Product-specific import graphs, real entrypoint wiring proofs, periodic full/release suites |
| **Enforcement Evidence & Ruleset Observer** | `standards/testing-strategy/enforcement-evidence*`, `scripts/check-enforcement-evidence.py`, `scripts/observe-github-ruleset.py`, `profiles/L2-governed/github-ruleset.import.json` | **L1 Candidate (audits L2)** | Offline & live GitHub Rulesets API normalization with SHA-256 response binding, source-bound `integration_id` & `pull_request` bypass allowlist checks, importable Ruleset JSON, negative mutation suite | Continuous protected polling, mutating rulesets, replacing independent human review |
| **AI Tool Projections (Skills / Plugins / Evals)** | `skills/`, `evals/`, `llms.txt`, `.claude-plugin/`, `.cursor-plugin/`, `.codex-plugin/` | **Non-Authoritative Projection** | 6 standalone zero-overlap language-agnostic Agent Skills + skill eval rubrics + `llms.txt` routing map + native plugin manifests | **Never holds approval, waiver, risk-reduction, or trusted-receipt authority** |

> Enterprise L2 protocol suites for **UI Assurance** (8 schemas) and **Code Health Ratchet & Retirement** (10 schemas) live in the sibling repository `OpenAgenticSecurity/assurance-contracts`.

## Non-Self-Attestation Boundary

Changes to `.github/**`, `action.yml`, `Makefile`, `requirements-test*`, `pyproject.toml`,
`scripts/**`, `tests/**`, `standards/**/schema/**`, `skills/**`,
`.*-plugin/**`, `llms.txt`, `AGENTS.md`, or `CLAUDE.md` are **never
self-attesting** and require independent mechanism review under protected branch
rulesets.
