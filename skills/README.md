# Agent Skills (6 Standalone Non-Authoritative Projections)

**Updated**: 2026-11-21
**Chinese**: [README.zh.md](README.zh.md)
**Authoritative Source**: [`standards/`](../standards/README.md) & [`checklists/`](../checklists/README.md) (`v0.2.1`)

> **Trust Boundary**: Every `SKILL.md` in this directory is **100% standalone**
> (works inside any unrelated repo via `npx skills add`) and **explicitly
> non-authoritative**. Skills help Coding Agents carry the workflow, while real
> trust boundaries live outside the prompt window: local Git hooks
> (`scripts/workspace-git.py`), **`deps`** lifecycle hooks, and
> protected GitHub Rulesets (`scripts/observe-github-ruleset.py`).

## Install Into Your Coding Agent

```bash
# Universal skills CLI (Claude Code / Cursor / Codex / etc.):
npx skills add OpenAgenticSecurity/agentic-sdlc

# Or copy into your repository via the zero-dependency bootstrap script:
bash /path/to/agentic-sdlc/scripts/bootstrap.sh --profile L0 --target /path/to/your-repo --with-skills
```

Native plugin manifests are included at `.claude-plugin/`, `.cursor-plugin/`,
and `.codex-plugin/`.

> **Scope & Language Independence**: These 6 skills encode **language-agnostic
> security, verification, PR-audit, production-readiness, and Git workflow
> invariants** — **not** coding-style or framework conventions (formatting,
> naming, or lint rules belong in each repository's own `AGENTS.md` and
> linters). Occasional language snippets inside a skill are illustrative
> examples of universal failure classes.

## Included Skills (6, Zero Overlap)

| Skill | When to Invoke / What It Enforces | Authoritative Backing |
|---|---|---|
| [`bootstrap-agentic-sdlc`](bootstrap-agentic-sdlc/SKILL.md) | Set up `L0`/`L1`/`L2` Agentic SDLC (+ optional `deps`) into an existing repo safely | `BOOTSTRAP.md`, `profiles/` |
| [`secure-vibe-coding`](secure-vibe-coding/SKILL.md) | Write secure AI-generated code: fail-closed auth/tenant, safe sinks, secrets & crypto, anti-slopsquatting, negative security tests | `standards/secure-vibe-coding.md`, `checklists/secure-vibe-coding-review.md` |
| [`audit-pr-diff`](audit-pr-diff/SKILL.md) | Review current diff/PR with `file:line` grounding against security, frontend (454-bug), backend-perf (8-class), seven-sins & mechanism-review checklists | `checklists/` |
| [`audit-production-readiness`](audit-production-readiness/SKILL.md) | Full-repo 5-dimension audit (Architecture/Design/Functionality/Performance/Security) with 7 evidence disciplines, 3-layer defaults, data liveness & H1/H2 production-vs-demo verdict | `checklists/production-readiness-audit.md` |
| [`done-claim-verify`](done-claim-verify/SKILL.md) | Fail-closed verification: 5-layer fact chain, 4 fake-done breakpoints, legal non-green states, negative mutations, non-self-attestation & `DoneClaim` | `checklists/fake-done-dereference.md`, `standards/testing-strategy.md` |
| [`multi-agent-git-flow`](multi-agent-git-flow/SKILL.md) | `STATUS.md` truth, fresh remote baseline, isolated worktrees, Managed Issue Claims, cross-session handoffs, anti-stacked-PR base, shared worktree deps & 5-point safe cleanup | `standards/multi-ai-git-workflow.md`, `standards/agent-issue-pr-loop.md`, `standards/ai-coding-context.md` |
