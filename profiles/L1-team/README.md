# Profile L1 — Multi-Human / Multi-Agent Team (~20 Minutes)

Build on top of [`L0-solo`](../L0-solo/README.md) when multiple engineers or
parallel coding agents (Claude Code, Cursor, Codex, bots) collaborate on shared
GitHub repositories.

## Files to Copy Into Your Repo

| File Here | Target Path in Your Repo | Purpose |
|---|---|---|
| `ISSUE_TEMPLATE/` (`config.yml`, `issue.md`, `epic.md`) | `.github/ISSUE_TEMPLATE/` | Generic scope, acceptance-criteria & verification-plan issue templates (replace `<owner>/<repo>`) |
| `candidate-gates.workflow.yml` | `.github/workflows/candidate-gates.yml` | Default: minimal language-agnostic workflow that runs `make agent-check` (the entrypoint installed by `L0`) |
| `workflows/ci-python.yml` / `ci-node-ts.yml` / `ci-rust.yml` / `ci-go.yml` / `ci-java.yml` | `.github/workflows/candidate-gates.yml` (pick one with `--ci python\|node-ts\|rust\|go\|java`) | SHA-pinned, fail-closed language workflows (Python Ruff `F`/`B`/`S`/`ASYNC` + pytest; Node `npm ci` + lint + `tsc` + tests; Rust fmt + Clippy + tests; Go `gofmt` + `go vet` + `-race`; Java/Kotlin Gradle/Maven wrapper) |

## Reference Examples (Optional)

- `issue-claim.example.md` — Managed Issue Claim Comment format validated & checked for owned-path overlaps via `scripts/agent-claim.py`.
- `agentic-sync.example.json` — Declarative coupled-change rules enforced via `scripts/check-change-sync.py` (ensures code/API/doc edits update coupled tests, docs, `STATUS.md`, or bilingual mirrors).
- `suite-catalog.example.json` — Example suite catalogue for repositories adopting `standards/testing-strategy/affected-closure-contract.md`.

## Quick Apply & Local Git Guardrails

```bash
# Bootstrap L0 + L1 files (never overwrites existing files); --ci is optional:
bash /path/to/agentic-sdlc/scripts/bootstrap.sh --profile L1 --ci python --target /path/to/your-repo --with-skills

# Install local pre-commit / pre-push guardrails blocking direct commits/pushes to main:
python3 /path/to/agentic-sdlc/scripts/workspace-git.py guardrails --root /path/to/workspace --apply

# Verify adoption signals in your repository:
python3 /path/to/agentic-sdlc/scripts/audit-repo.py --profile L1 /path/to/your-repo
```
