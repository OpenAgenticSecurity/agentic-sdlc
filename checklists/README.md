# Empirical Checklists & Evidence Templates

**Status**: accepted baseline
**Updated**: 2026-11-20
**Chinese**: [README.zh.md](README.zh.md)

These checklists and templates distill empirical production lessons from
**200B+ tokens** of multi-repo AI-assisted engineering — backed by explicit
sub-studies (443 tracked coding sessions / 8.4B tokens, 24→2 AI code-review
verification audit, 454 real frontend issues, and 100+ backend performance
incidents; see [Empirical Findings](../docs/empirical-findings.md)).

They are designed to be copied directly into PR templates, review gates, and
team runbooks alongside the authoritative [standards/](../standards/README.md)
and deterministic checkers in [scripts/](../scripts/).

## Checklist Index

| Checklist / Template | Empirical Basis | Primary Audience / Stage | Source Article |
|---|---|---|---|
| [vibe-coding-seven-sins.md](vibe-coding-seven-sins.md) ([中文](vibe-coding-seven-sins.zh.md)) | 443 sessions, 8.4B tokens, 3 failure archetypes, phase transition (`<5K` vs `>10K` LOC), 7 sins | Session planning, context boundaries, refactoring (`L0`–`L1`) | [Vibe Coding Survival Guide](https://fz.cool/vibe-coding-complete-guide/) |
| [secure-vibe-coding-review.md](secure-vibe-coding-review.md) ([中文](secure-vibe-coding-review.zh.md)) | Real security audits, applied cryptography operations & AI-code vulnerability classes | Security PR review, negative security testing (`L0`–`L2`) | [Applied Cryptography Ops](https://fz.cool/Applied-Cryptography-Operation-Must-Knowns/) & [Secure Vibe Coding Standard](../standards/secure-vibe-coding.md) |
| [multi-agent-git-gates.md](multi-agent-git-gates.md) ([中文](multi-agent-git-gates.zh.md)) | Concurrent Cursor + Claude Code + Codex multi-repo engineering, 4-owner split | Pre-edit, pre-commit, pre-PR, destructive Git brakes (`L0`–`L1`) | [Multi-Agent Git Workflow](https://fz.cool/Multi-Agent-Git-Workflow/) |
| [fake-done-dereference.md](fake-done-dereference.md) ([中文](fake-done-dereference.zh.md)) | 24→2 review audit, 15/15→0/15 legacy gate drift, 43→29 counterevidence review, 4 dereference breakpoints | Acceptance verification, audit review, runtime closure (`L1`–`L2`) | [Agentic Assurance Engineering](https://fz.cool/agentic-software-engineering-real-sdlc/) & [Fake-Done Breakpoints](https://fz.cool/agentic-fake-done-breakpoints/) |
| [done-claim.template.md](done-claim.template.md) & [done-claim.example.json](done-claim.example.json) | 7-tuple `DoneClaim` + legal non-green status vocabulary + `does_not_prove[]` | PR descriptions, handoffs, release sign-off (`L0`–`L2`) | [Fake-Done Breakpoints](https://fz.cool/agentic-fake-done-breakpoints/) |
| [frontend-vibe-coding-review.md](frontend-vibe-coding-review.md) ([中文](frontend-vibe-coding-review.zh.md)) | 454 real frontend issues; top 4 causes = 84%; CI/unit tests caught only 7% | Frontend PR review, browser QA, UI gate design (`L0`–`L2`) | [Frontend Vibe Coding Issues](https://fz.cool/vibe-coding-issues-in-frontend/) |
| [backend-performance-review.md](backend-performance-review.md) ([中文](backend-performance-review.zh.md)) | 100+ backend perf fixes across 380K LOC; only 16% proactive, 5% caught by CI | Backend PR review, load/tail testing, Agent loop budgets (`L1`–`L2`) | [Backend Performance in Vibe Coding](https://fz.cool/vibe-coding-backend-performance/) |
| [agent-ops-and-workspace-hygiene.md](agent-ops-and-workspace-hygiene.md) ([中文](agent-ops-and-workspace-hygiene.zh.md)) | Multi-worktree shared venv/`node_modules` traps, 260M-token subagent burn, scratch & `audit/EVIDENCE.md`, stacked-PR hazards | Multi-worktree workspace ops, subagent budgets, periodic audits (`L0`–`L2`) | [`scripts/link-shared-node-deps.mjs`](../scripts/link-shared-node-deps.mjs) & real multi-repo incidents |
| [production-readiness-audit.md](production-readiness-audit.md) ([中文](production-readiness-audit.zh.md)) | 5-dimension full-repo implementation audit, 7 evidence disciplines, 3-layer defaults, data liveness & H1/H2 production-vs-demo verdict | Pre-launch full-repo audit, production readiness (`L1`–`L2`) | [`skills/audit-production-readiness/SKILL.md`](../skills/audit-production-readiness/SKILL.md) |
| [agent-config-and-ci-injection.md](agent-config-and-ci-injection.md) ([中文](agent-config-and-ci-injection.zh.md)) | Instruction-file poisoning (hidden Unicode, silent-run social engineering, API hijack), `.vscode/tasks.json` `folderOpen`, `.claude/settings.json`, CI Comment-and-Control (`pull_request_target`) | Agent config review, CI hardening (`L0`–`L2`) | [`scripts/audit-repo.py`](../scripts/audit-repo.py) (`OAS-AGT-01..03`, `OAS-CI-05`) |
| [destructive-ops-and-iac-safety.md](destructive-ops-and-iac-safety.md) ([中文](destructive-ops-and-iac-safety.zh.md)) | Prod DB credential isolation, shared IaC module `CODEOWNERS` parity, `prevent_destroy`, staging bake windows & agent-unreachable backups | DB migrations, Terraform/K8s/infra PRs (`L1`–`L2`) | 2026 public production incident patterns & [`profiles/L2-governed/CODEOWNERS.example`](../profiles/L2-governed/CODEOWNERS.example) |
| [handoff.template.md](handoff.template.md) | Cross-session / cross-layer API, schema & 3-layer config contract handoff | Session compaction (`60`-msg cliff), frontend/backend handoff (`L0`–`L2`) | [`skills/multi-agent-git-flow/SKILL.md`](../skills/multi-agent-git-flow/SKILL.md) |

## Operating Rule

Checklists catch human and agent blind spots quickly, but prose alone decays
across long sessions and context compaction. Whenever the same failure class
appears **twice**, graduate the check from a checklist line into a deterministic
gate (schema, lint rule, query-budget test, contract test, or required status
check) and seed a violating mutation to prove the gate actually turns red.
