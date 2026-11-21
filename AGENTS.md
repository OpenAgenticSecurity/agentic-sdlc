# AGENTS.md — OpenAgenticSecurity/agentic-sdlc

## Scope

These instructions govern `OpenAgenticSecurity/agentic-sdlc`. This repository
owns lean, immediately usable Agentic SDLC standards, Secure Vibe Coding
guardrails, empirical checklists, progressive adoption profiles (`L0`–`L2`),
6 standalone Agent Skills (`skills/`), and deterministic governance scripts.

## Session Start

Read in this order before non-trivial work:

1. `README.md` (or `README.zh.md`) and `llms.txt`
2. `BOOTSTRAP.md` and `MATURITY.md`
3. The relevant standard, checklist, skill, or script

## Core Operating Rules

- Treat `standards/` and `scripts/` as authoritative; `AGENTS.md`, `CLAUDE.md`,
  and `skills/` are ergonomic projections, never approval authorities.
- Before editing in a Git checkout, run `git fetch --prune origin`,
  `git status --short --branch`, and `git branch -vv`.
- Never develop directly on `main`. Use one task, one branch, one worktree, one
  owner, and one explicit scope.
- Never revert, reset, rebase, stash, or overwrite unowned local changes.
- Prefer deterministic scripts, closed schemas, and negative mutation tests over
  prose alone.
- Never collapse `NOT_RUN`, `FLAKY`, `ERROR`, `UNKNOWN`, or `NOT_EVALUATED`
  into `PASS`.
- Never commit secrets, credentials, personal user paths (`/Users/<name>`),
  customer data, or private keys into docs, fixtures, or PRs.
- Keep English (`*.md`) and Chinese (`*.zh.md`) mirrors behaviorally aligned.
- Run `make check` for docs-only changes and `make verify-all` before claiming
  completion on any enforcement surface.

## Enforcement Surfaces (Not Self-Attesting)

Any change touching one or more of the following paths modifies an enforcement
or specification surface and is **not self-attesting**:

```text
standards/testing-strategy/**
scripts/**
tests/**
profiles/**
skills/**
.claude-plugin/**
.cursor-plugin/**
.codex-plugin/**
llms.txt
requirements-test*
pyproject.toml
Makefile
action.yml
.github/**
AGENTS.md
CLAUDE.md
```

Candidate jobs execute from PR-controlled sources and are **not self-attesting**
and do **not** constitute trusted enforcement. Changes to enforcement surfaces
require review by both the architecture/contract owner and a second independent
mechanism reviewer under protected GitHub Rulesets.

## Required Checks

```bash
make check             # Docs, links, placeholders, paths, affected-closure & enforcement-evidence
make verify-all        # Full deterministic suite (check + lint + agent-governance-test)
make static-analysis   # ShellCheck + actionlint (needs Docker) when touching scripts/*.sh or workflows
```

## CLAUDE.md Parity

`CLAUDE.md` must remain behaviorally equivalent to this file.
