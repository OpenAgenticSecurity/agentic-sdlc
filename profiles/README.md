# Progressive Adoption Profiles

**Updated**: 2026-11-20
**Chinese**: [README.zh.md](README.zh.md)

Do not force full enterprise governance onto a weekend prototype, and do not
run a multi-agent production platform on prose alone. Each profile is
**self-contained and directly copyable** — or installable in one command via
`scripts/bootstrap.sh` (see [`BOOTSTRAP.md`](../BOOTSTRAP.md)).

| Profile | Audience | Time | What You Get |
|---|---|---|---|
| **[`L0-solo`](L0-solo/README.md)** | Solo developer / small repo | ~5 min | Zero-tool baseline: `AGENTS.md`, `CLAUDE.md`, `STATUS.md`, `VIBE_CODING_CONTEXT.md`, security & evidence PR template, worktree `.gitignore`, fail-closed `make agent-check` entrypoint |
| **[`L1-team`](L1-team/README.md)** | Multi-human / multi-agent team | ~20 min | `L0` + generic `.github/ISSUE_TEMPLATE/`, exact-head candidate CI workflow (generic or Python / Node-TS / Rust / Go / Java via `--ci`), Managed Issue Claims, local Git `pre-commit`/`pre-push` guardrails |
| **[`L2-governed`](L2-governed/README.md)** | Security-critical / governed engineering | ~1 hour | `L1` + enforcement-surface `CODEOWNERS`, GitHub Ruleset policy & read-only audit (`observe-github-ruleset.py`), independent mechanism-review checklist, optional **`deps`** local carrier (`aac` / `agent-hook` / `security-audit` / `agent-verify`), optional L2 closed contracts |
