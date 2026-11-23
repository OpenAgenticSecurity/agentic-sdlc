# CLAUDE.md — OpenAgenticSecurity/agentic-sdlc

@AGENTS.md

Use [AGENTS.md](AGENTS.md) as the single canonical guide for this repository
(Git worktree/PR isolation, bilingual parity, and non-self-attesting enforcement
surfaces).

- Docs-only edits: `make check`
- Any enforcement-surface edit: `make verify-all` (plus `make static-analysis`
  when touching `scripts/*.sh` or workflows). Candidate CI is **not self-attesting**.
