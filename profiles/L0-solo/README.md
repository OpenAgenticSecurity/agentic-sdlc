# Profile L0 — Solo / Small Project Baseline (~5 Minutes)

Use this profile when a single engineer (working with Claude Code, Cursor, or
Codex) wants immediate protection against dirty `main` checkouts, hallucinated
modules, insecure AI coding defaults, and unverified "done" claims — with zero
extra tooling required.

## Files Included (Copy Directly Into Your Repo)

| File Here | Target Path in Your Repo | Purpose |
|---|---|---|
| `AGENTS.md` | `AGENTS.md` | Canonical agent instructions + Secure-by-Default coding red lines |
| `CLAUDE.md` | `CLAUDE.md` | Concise Claude Code mirror aligned with `AGENTS.md` |
| `STATUS.md` | `docs/architecture/STATUS.md` | Single source of truth for `Verified` / `Partial` / `Deleted` / `Planned` modules |
| `VIBE_CODING_CONTEXT.md` | `docs/VIBE_CODING_CONTEXT.md` | 2-minute session onboarding & protected primary flows |
| `pull_request_template.md` | `.github/pull_request_template.md` | Evidence-first PR template with security & negative-test check |
| `.gitignore.snippet` | Append to `.gitignore` | Ignores multi-tool worktree namespaces (`.worktrees/`, `.claude/worktrees/`, `.cursor/worktrees/`, `.codex/worktrees/`) |
| `Makefile.agent-check.snippet` | `Makefile` (or merge into yours) | The `make agent-check` entrypoint that `AGENTS.md` and `CLAUDE.md` name. It fails closed until you replace its last line with your real lint, typecheck and test commands |

## Quick Apply (Optional Pure-Bash Helper)

```bash
bash /path/to/agentic-sdlc/scripts/bootstrap.sh \
  --profile L0 \
  --target /path/to/your-repo \
  --with-skills

# Read-only check that the baseline is in place:
bash /path/to/agentic-sdlc/scripts/check-product-compliance.sh --profile L0 /path/to/your-repo
```

`bootstrap.sh` creates the `Makefile` only when the repository has none. An
existing `Makefile` is never modified; the snippet is placed next to it instead.
