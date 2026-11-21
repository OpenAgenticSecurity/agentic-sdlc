# CLAUDE.md — OpenAgenticSecurity/agentic-sdlc

Use [AGENTS.md](AGENTS.md) as the behaviorally canonical guide for this
repository. Claude-specific notes below may assist workflow ergonomics, but
must never weaken the Git, safety, verification, or non-self-attestation rules
in `AGENTS.md`.

## Minimum Loop

1. Read `README.md` / `README.zh.md`, `llms.txt`, `BOOTSTRAP.md`, `MATURITY.md`,
   and the relevant standard, checklist, skill, or script.
2. Check Git state (`git fetch --prune origin`, `git status --short --branch`,
   `git branch -vv`) and work in an isolated topic branch / worktree.
3. Preserve unowned local changes; never commit personal paths, secrets, or
   credentials.
4. Prefer deterministic scripts, closed schemas, and negative tests over prose.
5. Keep `AGENTS.md`, `CLAUDE.md`, and bilingual core docs aligned.
6. Run `make check` for docs-only edits, or `make verify-all` for any
   enforcement-surface edit. Also run `make static-analysis` (needs Docker)
   when touching `scripts/*.sh` or any workflow.

## Path-Conditional Enforcement Checks

When any changed path touches `standards/testing-strategy/**`, `scripts/**`,
`tests/**`, `profiles/**`, `skills/**`, `.claude-plugin/**`,
`.cursor-plugin/**`, `.codex-plugin/**`, `llms.txt`, `requirements-test*`,
`pyproject.toml`, `Makefile`, `action.yml`, `.github/**`, `AGENTS.md`, or `CLAUDE.md`, run:

```bash
make verify-all
```

Candidate jobs execute from PR-controlled sources and are **not self-attesting**
and do **not** establish trusted enforcement, required status, CODEOWNER
approval, independent mechanism review, or admin-bypass independence.
