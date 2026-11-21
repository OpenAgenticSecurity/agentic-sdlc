# Bootstrapping Agentic SDLC into Your Repository

**Updated**: 2026-11-20
**Chinese**: [BOOTSTRAP.zh.md](BOOTSTRAP.zh.md)

You do **not** need to install a framework or CLI package to adopt
`OpenAgenticSecurity/agentic-sdlc`. Want to see what is currently missing or
unsafe in your repo first? Run the read-only, zero-dependency self-audit:

```bash
python3 /path/to/agentic-sdlc/scripts/audit-repo.py /path/to/your-repo [--github]
```

Then pick either of the two 2-minute bootstrap paths below and wire your Coding
Agent and GitHub repository settings.

---

## Choose Your Starting Profile

| Profile | Best For | Time | What Gets Installed |
|---|---|---|---|
| **`L0`** (`profiles/L0-solo/`) | Solo developer or small repo | ~5 min | `AGENTS.md`, `CLAUDE.md` (mirror), `docs/architecture/STATUS.md`, `docs/VIBE_CODING_CONTEXT.md`, `.github/pull_request_template.md`, worktree `.gitignore` rules, a fail-closed `make agent-check` entrypoint |
| **`L1`** (`profiles/L1-team/`) | Multi-human / multi-agent team | ~20 min | Everything in `L0` + `.github/ISSUE_TEMPLATE/`, `.github/workflows/candidate-gates.yml` (generic, or a Python / Node-TS / Rust / Go / Java template via `--ci`), Managed Issue Claim protocol |
| **`L2`** (`profiles/L2-governed/`) | Security-critical / governed engineering | ~1 hour | Everything in `L1` + enforcement-surface `.github/CODEOWNERS`, `ruleset-policy.json`, independent mechanism-review checklist, GitHub Ruleset verification |

---

## Path 1 — Zero-Install AI Bootstrap Prompt (Fastest)

Have your own Coding Agent (Claude Code, Cursor, or Codex) inspect your real
repository stack and scaffold the right files directly. Paste this prompt into
a clean topic branch / worktree:

```text
Bootstrap OpenAgenticSecurity/agentic-sdlc (profile: L0 — or change to L1 / L2)
into this repository.

Reference source:
- Local clone at /path/to/agentic-sdlc (or https://github.com/OpenAgenticSecurity/agentic-sdlc)
- Read `profiles/L0-solo/` (plus `L1-team/` / `L2-governed/` if requested).

Rules:
1. First inspect this repository's REAL stack (package.json, pyproject.toml,
   Cargo.toml, go.mod, Makefile, .github/workflows/, existing AGENTS.md/CLAUDE.md).
2. Do NOT overwrite existing files silently. If a file exists, show a minimal
   merge proposal instead.
3. Fill `AGENTS.md`, `CLAUDE.md`, `docs/VIBE_CODING_CONTEXT.md`, and
   `docs/architecture/STATUS.md` with REAL entrypoints and REAL verification
   commands that actually run in this repo — zero invented commands or placeholders.
4. Append multi-tool worktree patterns (`.worktrees/`, `.claude/worktrees/`,
   `.cursor/worktrees/`, `.codex/worktrees/`) to `.gitignore` if missing.
5. Keep `AGENTS.md` and `CLAUDE.md` behaviorally equivalent.
6. Run the repo's real check command and report exact commands + exit codes.
```

### Mandatory 4-Point Post-Bootstrap Verification (Human Check)

Never blindly trust an agent-generated bootstrap:
1. Run the verification command written in `AGENTS.md` (e.g., `make agent-check`) — confirm it actually executes and fails on a real broken test (no `0 tests collected` or green `skip`).
2. Check `docs/architecture/STATUS.md` — confirm every `Verified` module actually exists in code.
3. Confirm `AGENTS.md` and `CLAUDE.md` do not contradict each other.
4. Confirm `.gitignore` ignores `.worktrees/`, `.claude/worktrees/`, `.cursor/worktrees/`, and `.codex/worktrees/`.

---

## Path 2 — Deterministic Zero-Dependency Script (`scripts/bootstrap.sh`)

Prefer deterministic file copying with zero LLM involvement? Run the bundled
pure-Bash script. It never overwrites existing files unless `--force` is passed,
and it never modifies an existing `Makefile` at all:

```bash
# Preview changes first (--dry-run writes nothing):
bash /path/to/agentic-sdlc/scripts/bootstrap.sh \
  --profile L0 \
  --target /path/to/your-repo \
  --dry-run

# Apply L0 solo baseline + 6 Agent Skills:
bash /path/to/agentic-sdlc/scripts/bootstrap.sh \
  --profile L0 \
  --target /path/to/your-repo \
  --with-skills

# Apply L1 team baseline with a language CI template + empirical review checklists:
bash /path/to/agentic-sdlc/scripts/bootstrap.sh \
  --profile L1 \
  --ci python \
  --target /path/to/your-repo \
  --with-skills \
  --with-checklists

# Verify adoption signals (read-only). Pass the profile you bootstrapped;
# the script prints this exact command when it finishes:
bash /path/to/agentic-sdlc/scripts/check-product-compliance.sh --profile L1 /path/to/your-repo
```

What to expect afterwards:

- **`make agent-check` exists and fails closed.** `AGENTS.md`, `CLAUDE.md` and the
  generic L1 workflow all call it. In a repository without a `Makefile` the
  script creates one whose `agent-check` recipe exits non-zero with
  `agent-check is not configured` until you replace that line with your real
  lint, typecheck and test commands. If you already have a `Makefile`, it is
  left untouched and `Makefile.agent-check.snippet` is placed next to it for you
  to merge.
- **`--ci` picks the L1 workflow** installed at
  `.github/workflows/candidate-gates.yml`: `generic` (default, runs
  `make agent-check`), `python` (Ruff `F`/`B`/`S`/`ASYNC` + pytest), `node-ts`
  (`npm ci`, lint, `tsc --noEmit`, tests), `rust` (fmt, clippy `-D warnings`,
  tests), `go` (`gofmt`, `go vet`, `go test -race`), or `java` (Gradle/Maven
  wrapper).
- **`--with-skills` writes to `.agents/skills/` by default.** Pass
  `--skills-dir .claude/skills` for Claude Code or `--skills-dir .cursor/skills`
  for Cursor.

Optional local Git guardrails (blocks AI agents from committing directly on
`main` or your primary checkout, and blocks direct pushes to `main` — while
preserving and forwarding all existing Git hooks such as `commit-msg` and
`post-checkout`; remember `--no-verify` can still bypass local hooks, so GitHub
Rulesets remain the hard merge boundary):

```bash
# Single repository (run inside your repo — never touches sibling repos):
cd /path/to/your-repo
python3 /path/to/agentic-sdlc/scripts/workspace-git.py guardrails --apply

# Remove cleanly at any time (restores previous core.hooksPath):
python3 /path/to/agentic-sdlc/scripts/workspace-git.py guardrails --remove

# Multi-repo workspace (--root is the parent directory containing your repos):
python3 /path/to/agentic-sdlc/scripts/workspace-git.py guardrails \
  --root /path/to/parent-workspace \
  --apply
```

---

## Wiring into Your Coding Agents

| Coding Agent | Files It Automatically Loads | Recommended Setup |
|---|---|---|
| **Claude Code** | `CLAUDE.md` (thin `@AGENTS.md` pointer), `.claude/skills/*/SKILL.md` | Native one-step install: `/plugin install agentic-sdlc --marketplace OpenAgenticSecurity/agentic-sdlc` (or `npx skills add OpenAgenticSecurity/agentic-sdlc`); keep `AGENTS.md` canonical at repo root. |
| **Cursor** | `AGENTS.md` (natively), `.cursor/skills/*/SKILL.md` | Install 6 skills via `npx skills add` / `.cursor-plugin/`; keep `AGENTS.md` at repo root (no duplicate global `.mdc` needed). |
| **Codex / Generic Agents** | `AGENTS.md`, `.agents/skills/*/SKILL.md`, `llms.txt` | Install via `npx skills add` / `.codex-plugin/` (or point the agent at `llms.txt`); keep `AGENTS.md` canonical at repo root. |

> **Reminder**: `skills/`, `AGENTS.md`, and `CLAUDE.md` are
> **non-authoritative ergonomics**. Whenever a rule matters every time, back it
> with a lint rule, test, or GitHub branch ruleset — rules in prose decay across
> context compaction.

Using the empirical & security checklists during daily development:
- Before merging any security-relevant diff (auth, tenant, paths, SSRF, crypto, deps): paste [`checklists/secure-vibe-coding-review.md`](checklists/secure-vibe-coding-review.md) and require at least one negative security test.
- Before frontend PR sign-off: paste [`checklists/frontend-vibe-coding-review.md`](checklists/frontend-vibe-coding-review.md) into your review prompt.
- Before backend PR sign-off: paste [`checklists/backend-performance-review.md`](checklists/backend-performance-review.md).
- Before declaring a non-trivial task complete: fill out [`checklists/done-claim.template.md`](checklists/done-claim.template.md).

---

## Optional: Deterministic Local Enforcement with `deps` and `sealed-data`

`L0`–`L2` give you instructions, templates and a GitHub merge boundary. Two
optional sibling projects in [OpenAgenticSecurity](https://github.com/OpenAgenticSecurity)
(upcoming public releases) add enforcement on the developer machine, inside the
agent's own edit loop:

- **`deps`** — a single-binary
  Rust CLI (the engineering carrier for `agentic-sdlc`): Architecture-as-Code
  ratchet, dependency-pin API guard, secret-hygiene audit, lifecycle hooks for
  **Claude Code and Codex**, and a pinned stdio MCP server (`deps mcp`) for
  other MCP-capable agents.
- **`sealed-data`** — lets
  agents build and run data pipelines against approved data cards without
  reading the real dataset.

```bash
# Once `deps` is published / installed on PATH:
cd /path/to/your-repo

# 1. Baseline today's module couplings; new cross-boundary imports fail from now on:
deps aac init .
git add .deps/architecture.bundle.json

# 2. Install pre-edit + Stop hooks for the agent you use:
deps agent-hook install . --host claude --host-version "$(claude --version)" --enforce
deps agent-hook install . --host codex --with-mcp

# 3. Run the same gates locally or in CI and keep the replayable receipt:
deps security-audit .
deps agent-verify . --receipt .deps/receipt.json --remediate
```

To keep real datasets out of agent context once `sealed-data` is installed, run
`sealed-data seal` followed by `sealed-data hook install .`.

---

## Wiring into GitHub (`L1` -> `L2`)

1. **Templates & Candidate CI**:
   - Keep `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/`, and `.github/workflows/candidate-gates.yml` (pinned to 40-char Action commit SHAs, exact PR head checkout `${{ github.event.pull_request.head.sha || github.sha }}`, `persist-credentials: false`).
   - Treat PR-controlled CI as **candidate / advisory** — never self-attesting.
2. **Enforcement-Surface `CODEOWNERS` (`L2`)**:
   - Protect `.github/`, `Makefile`, `AGENTS.md`, `CLAUDE.md`, schemas, and gate scripts via `.github/CODEOWNERS` (see `profiles/L2-governed/CODEOWNERS.example`). Replace `@org/...` placeholders with real team/user handles — `check-product-compliance.sh --profile L2` fails closed if `@org/` remains, because GitHub silently skips unknown owners.
3. **GitHub Repository Ruleset on `main` (`L2`)**:
   Import `profiles/L2-governed/github-ruleset.import.json` directly in GitHub
   (**Settings -> Rules -> Rulesets -> New ruleset -> Import a ruleset**), then
   replace `agent-check` / `security-scan` with your exact CI job names (and
   replace `integration_id: 15368` if your CI is not GitHub Actions). It
   enforces `~DEFAULT_BRANCH`, `required_approving_review_count >= 2`,
   `require_code_owner_review`, `dismiss_stale_reviews_on_push`,
   `require_last_push_approval`, source-bound `required_status_checks`, and zero
   unconditional (`always`/`exempt`) or unapproved `pull_request` bypass actors
   (explicit break-glass `pull_request` actors may be allowlisted in
   `allowed_pull_request_bypass_actors`).
4. **Verify Your Live Ruleset (Read-Only)**:
   This needs an authenticated `gh` CLI, and `--validate` needs `jsonschema`
   from the hash-locked requirements file:
   ```bash
   python3 -m pip install --require-hashes --only-binary=:all: \
     -r /path/to/agentic-sdlc/requirements-test.txt

   python3 /path/to/agentic-sdlc/scripts/observe-github-ruleset.py \
     --live \
     --repo owner/your-repo \
     --ruleset-id <RULESET_ID> \
     --default-branch main \
     --policy /path/to/your-repo/.github/ruleset-policy.json \
     --output ruleset-evidence.json \
     --validate
   ```
   Exit code `0` means your observed GitHub ruleset satisfies every policy invariant; exit code `2` fails closed with the exact gap (missing required status, disabled last-push approval, or unconditional bypass).
