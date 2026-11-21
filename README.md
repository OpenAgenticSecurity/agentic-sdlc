# OpenAgenticSecurity — Agentic SDLC

[![CI](https://github.com/OpenAgenticSecurity/agentic-sdlc/actions/workflows/ci.yml/badge.svg)](https://github.com/OpenAgenticSecurity/agentic-sdlc/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Maturity: L0–L2 Spec & Scripts](https://img.shields.io/badge/Maturity-L0%E2%80%93L2%20Spec%20%26%20Scripts-emerald.svg)](MATURITY.md)

**English** | [中文](README.zh.md) | [Project Site](https://openagenticsecurity.github.io/agentic-sdlc/)

**Stop letting coding agents grade their own homework.**

Guardrails for repositories where coding agents write the code: rules the agent reads, local checks it cannot skip, and a GitHub merge boundary it cannot approve for itself.

Everything here is plain Markdown, YAML and standalone scripts that you copy into your own repository. No framework lock-in. No CLI package to install.

Distilled from **200B+ tokens** of multi-repo AI-assisted production engineering — backed by explicit-denominator studies: **443 tracked sessions (8.4B tokens)**, **454 real frontend bugs (only 7% caught by CI)**, **100+ backend performance incidents (only 5% caught by CI)**, and **24→2 AI code-review verification audits** ([Empirical Findings](docs/empirical-findings.md)).

---

## Use It in 60 Seconds

Pick one. The full walkthrough (Claude Code / Cursor / Codex and GitHub wiring) is in [**BOOTSTRAP.md**](BOOTSTRAP.md) ([中文接入指南](BOOTSTRAP.zh.md)).

### Option A — Install 6 Standalone Skills Into Your Coding Agent

```bash
# Claude Code 2.1.275+ native one-step plugin install (zero third-party npm):
/plugin install agentic-sdlc --marketplace OpenAgenticSecurity/agentic-sdlc

# Cross-agent CLI (Claude Code / Cursor / Codex; pin a version such as skills@1.9.0 if you prefer):
npx skills add OpenAgenticSecurity/agentic-sdlc
```

Native plugin manifests are included at `.claude-plugin/`, `.cursor-plugin/`, and `.codex-plugin/`. All 6 Skills are **100% self-contained & language-agnostic** (zero broken paths inside external repos):

| Skill | Your agent reaches for it when |
|---|---|
| **`bootstrap-agentic-sdlc`** | a repository has no `AGENTS.md`, `STATUS.md`, PR template or CI gate yet |
| **`secure-vibe-coding`** | it writes or reviews code touching auth, tenant scope, SQL, shell, paths, URLs, secrets, crypto, dependencies or CI |
| **`audit-pr-diff`** | it is asked to review a branch diff or pull request before merge |
| **`audit-production-readiness`** | it is asked whether an AI-built codebase is truly production-ready vs demo-grade (5-dimension audit, 3-layer defaults, data liveness, H1/H2 verdict) |
| **`done-claim-verify`** | it is about to say "done", "fixed" or "passing" |
| **`multi-agent-git-flow`** | it starts work in a repository other people or agents also edit |

### Option B — Zero-Install One-Liner (Paste Into Any Coding Agent)

```text
Read https://github.com/OpenAgenticSecurity/agentic-sdlc/blob/main/llms.txt and
bootstrap profile L0 (or L1/L2) into this repository using my real build/test
commands without overwriting existing files.
```

### Option C — Deterministic Pure-Bash Bootstrap (No LLM)

```bash
git clone https://github.com/OpenAgenticSecurity/agentic-sdlc.git

# Preview first (--dry-run writes nothing):
bash agentic-sdlc/scripts/bootstrap.sh --profile L0 --target /path/to/your-repo --dry-run

# Apply L0 solo baseline + 6 Agent Skills:
bash agentic-sdlc/scripts/bootstrap.sh --profile L0 --target /path/to/your-repo --with-skills

# Apply L1 team baseline with a language CI template (python | node-ts | rust | go | java) + checklists:
bash agentic-sdlc/scripts/bootstrap.sh --profile L1 --ci python --target /path/to/your-repo --with-checklists
```

The script never overwrites existing files, prints the exact follow-up check for the profile you chose, and leaves you with a `make agent-check` entrypoint that **fails closed until you point it at your real lint, typecheck and test commands**.

---

## 10-Second Proof: Run It Against Your Own Repo (Zero `pip install`)

Read-only, pure Python 3.11+ standard library, touches nothing — immediately see what blind spots exist in **your own** repository across Python, JS/TS, Go, Rust, Java, GitHub Actions, and GitHub Rulesets:

```bash
git clone https://github.com/OpenAgenticSecurity/agentic-sdlc.git

# 1. Audit your own repo locally in <1 second (zero pip install, read-only):
python3 agentic-sdlc/scripts/audit-repo.py /path/to/your-repo

# 2. Also audit your live GitHub Branch Ruleset read-only (requires authenticated `gh` CLI):
python3 agentic-sdlc/scripts/audit-repo.py /path/to/your-repo --github

# 3. Run the 14-case polyglot planted-trap eval suite (12 traps caught, 0 false positives):
python3 -S agentic-sdlc/scripts/run-evals.py
```

Or drop the reusable composite Action (`action.yml`) into any repository's CI (pinned to a 40-char commit SHA):

```yaml
- uses: OpenAgenticSecurity/agentic-sdlc@<40-char-commit-sha> # v0.2.1
  with:
    target: .
```

Or verify this repository's offline negative-mutation suite (zero network after install):

```bash
cd agentic-sdlc
python3 -m pip install --require-hashes --only-binary=:all: -r requirements-test.txt

# 1. Watch it catch GitHub Rulesets vulnerable to AI post-approval push & unconditional bypass:
make demo-catch-bugs

# 2. Verify this repository's entire deterministic suite:
make verify-all
```

---

## Three-Layer Defense

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Layer 1 · Inside the Agent (Zero Friction, Non-Authoritative Ergonomics)   │
│   skills/ (6 standalone Skills) · llms.txt · unified AGENTS.md (+ @CLAUDE) │
├────────────────────────────────────────────────────────────────────────────┤
│ Layer 2 · Local Deterministic Guardrails (Default-On; Bypassable via Hook) │
│   audit-repo.py (polyglot) · workspace-git.py (pre-commit/pre-push hooks)  │
│   deps (AaC ratchet · dependency-pin guard · secret audit · agent hooks)   │
│   link-shared-node-deps.mjs · sealed-data (cards only, never raw data)     │
├────────────────────────────────────────────────────────────────────────────┤
│ Layer 3 · GitHub Merge Boundary (Non-Self-Attesting External Enforcement)  │
│   L1 Fail-Closed CI (Python/TS/Rust/Go/Java) · Reusable action.yml         │
│   CODEOWNERS · Branch Ruleset Import · observe-github-ruleset.py (--live)  │
└────────────────────────────────────────────────────────────────────────────┘
```

> **Enduring security engineering principles did not expire when AI agents arrived — the executing actor, trust boundary, and speed changed.**
> **Done is a derived fact bound to exact revisions and verifiable evidence, never a boolean self-reported by an agent.**

### Complementary to `superpowers` & Prompt Frameworks

| Dimension | `superpowers` / Prompt Skill Packs | `OpenAgenticSecurity/agentic-sdlc` (+ `deps`) |
|---|---|---|
| **Scope** | **Inner loop**: how one coding agent brainstorms, plans, debugs, and runs TDD | **Outer security boundary**: keeping code secure, `main` clean, and "done" honest across parallel agents & GitHub |
| **Trust Model** | Prompt-level self-discipline inside the model window | **Zero-trust & Non-Self-Attestation**: Git hooks, `deps` lifecycle hooks, exact-SHA CI, and externally observed GitHub Rulesets |
| **Empirical Depth** | General workflow habits | Battle-tested AppSec red lines, 454 frontend bugs, 8 backend perf classes, 4 fake-done breakpoints, multi-worktree shared deps & 260M-token subagent budgets |

Use them together: let `superpowers` sharpen how an agent codes; use **`agentic-sdlc` + `deps`** to ensure it cannot ship insecure code, overwrite `main`, or certify its own broken gates.

---

## How to Use This in Your Workflow (Don't Copy Everything)

Keep Claude Code, Cursor, Codex, and `superpowers` unchanged — `agentic-sdlc` snaps onto **5 high-risk handoff points** in a normal day ([Full 4-Layer Toolchain & Pain-Point Map](docs/workflow-integration.md)):

```text
[1. Pick Up Task]  Issue -> worktree   --> Hook 1: AGENTS.md + STATUS.md + multi-agent-git-flow + Git hooks
[2. Plan & Code]   Inner coding loop   --> Hook 2: Non-trivial task gate + secure-vibe-coding (+ optional deps)
[3. Before "Done"] Agent claims pass   --> Hook 3: done-claim-verify + audit-pr-diff -> DoneClaim + does_not_prove[]
[4. Open PR & CI]  GitHub Actions      --> Hook 4: Fail-closed CI + 4-line action.yml + OAS-* Rule IDs
[5. Merge/Launch]  Production gate     --> Hook 5: GitHub Ruleset + CODEOWNERS + audit-production-readiness (H1/H2)
```

Do **not** copy `standards/` into your product repo, and never point your agent at a floating `main` URL on every session. Each piece has one clear home:

| Where It Lives | What You Put There | Why |
|---|---|---|
| **Global Coding Agent** (Claude Code / Cursor / Codex) | Install the 6 **`skills/`** once via `/plugin install` or `npx skills add` | **Language-agnostic** security, PR audit, production-readiness, fake-done dereference & multi-agent Git guardrails (NOT code style/formatting rules). Loaded only on demand with zero permanent context tax. |
| **Your Product Repo** (copied once, adapted to your stack) | One unified **`AGENTS.md`** + thin `@AGENTS.md` **`CLAUDE.md`** + `STATUS.md` + PR/CI template (`scripts/bootstrap.sh`) | Cursor, Codex, and Claude Code all read one root `AGENTS.md` (no duplicate `.mdc` needed). Put your repo's real commands & language conventions in the stack slots, with `<!-- OpenAgenticSecurity/agentic-sdlc@v0.2.1 -->`. |
| **Local Machine / CI** (run on demand or per PR) | **`scripts/audit-repo.py`** (or 4-line **`action.yml`**) + **`scripts/workspace-git.py guardrails`** | Catches unpinned Actions, multi-language unsafe sinks, `--passWithNoTests`, and direct commits on `main` deterministically. |
| **PR Reviews & GitHub** | Cite stable Rule IDs (**`OAS-CI-01`**, **`OAS-SVC-01`**, **`OAS-GH-02`**) + **`DoneClaim`** + import `github-ruleset.import.json` | Keeps `standards/` & `checklists/` as human reference (like OWASP ASVS) while enforcing the hard merge boundary on GitHub. |

---

## Repository Map

| Path | What It Gives You | Start Here |
|---|---|---|
| **`llms.txt`** | ~1K-token 1-read routing map for any Coding Agent | [llms.txt](llms.txt) |
| **`action.yml`** | Zero-dependency Composite GitHub Action running `audit-repo.py` in any repo's CI | [action.yml](action.yml) |
| **`skills/`** | 6 standalone, zero-overlap, language-agnostic Agent Skills + `.claude-plugin/` / `.cursor-plugin/` / `.codex-plugin/` | [skills/README.md](skills/README.md) ([中文](skills/README.zh.md)) |
| **`checklists/`** | 8 empirical, security, ops & readiness checklists + `DoneClaim` / `Handoff` templates | [checklists/README.md](checklists/README.md) ([中文](checklists/README.zh.md)) |
| **`profiles/`** | Copy-ready **`L0-solo`** (unified `AGENTS.md` + thin `@AGENTS.md` `CLAUDE.md`), **`L1-team`** (Python/TS/Rust/Go/Java fail-closed CI), **`L2-governed`** (importable GitHub Ruleset JSON) | [profiles/README.md](profiles/README.md) ([中文](profiles/README.zh.md)) |
| **`examples/`** | Runnable backend contract gates (`pytest`) & Playwright 3-layer frontend E2E starter | [examples/README.md](examples/README.md) ([中文](examples/README.zh.md)) |
| **`evals/`** | 14-case polyglot planted-trap eval harness (`scripts/run-evals.py`) + Skill eval rubrics | [evals/README.md](evals/README.md) ([中文](evals/README.zh.md)) |
| **`standards/`** | 9 concise bilingual standards (incl. Security, Reliability/Performance & Versioning) + 2 closed contracts (`affected-closure`, `enforcement-evidence`) | [standards/README.md](standards/README.md) ([中文](standards/README.zh.md)) |
| **`scripts/`** | 9 adopter/eval helpers (`audit-repo.py`, `check-change-sync.py`, `run-evals.py`, `bootstrap.sh`, `workspace-git.py`, `agent-claim.py`, `observe-github-ruleset.py`, `link-shared-node-deps.mjs`, `check-product-compliance.sh`) + 3 contract/doc checkers | [BOOTSTRAP.md](BOOTSTRAP.md) |
| **`docs/`** | Agentic SDLC Ontology (9 entities / 5 axioms), workflow integration map, empirical evidence & manifesto | [ontology.md](docs/ontology.md) · [workflow-integration.md](docs/workflow-integration.md) · [empirical-findings.md](docs/empirical-findings.md) · [manifesto.md](docs/manifesto.md) |
| **`site/`** | Zero-dependency bilingual GitHub Pages site + canonical JSON schema hosting | [site/index.html](site/index.html) · [Live Site](https://openagenticsecurity.github.io/agentic-sdlc/) |

### Requirements

| To Use | You Need |
|---|---|
| Skills, checklists, profiles, standards | Nothing — plain Markdown, YAML and JSON |
| `bootstrap.sh`, `check-product-compliance.sh` | Bash 3.2+ and Git on macOS or Linux (Windows is untested; use WSL) |
| `audit-repo.py`, `check-change-sync.py`, `workspace-git.py`, `agent-claim.py`, `observe-github-ruleset.py` | Python 3.11+ standard library; the `gh` CLI for `--github`, `--live`, and `publish` |
| `observe-github-ruleset.py --validate`, `make verify-all` | The hash-locked packages in `requirements-test.txt` |
| `link-shared-node-deps.mjs` | Node.js 18.3+ and npm |

---

## OpenAgenticSecurity Ecosystem

| Repository | Role |
|---|---|
| **`agentic-sdlc`** (this repo) | Methodology, Secure Vibe Coding rules, 8 checklists, 6 standalone Skills, reusable `action.yml`, L0–L2 kits & Git/Ruleset scripts |
| **`deps`** *(upcoming in [OpenAgenticSecurity](https://github.com/OpenAgenticSecurity))* | Optional single-binary Rust **engineering carrier** for Layer 2: Tree-sitter `deps context`/`locate`, `deps aac init`/`check`, `deps lineage-audit`, `deps security-audit`/`security-filter`, Claude Code & Codex lifecycle hooks (`deps agent-hook install`), and `deps agent-verify --receipt` |
| **`sealed-data`** *(upcoming in [OpenAgenticSecurity](https://github.com/OpenAgenticSecurity))* | Optional Rust CLI that lets agents build and run data pipelines against approved data cards (`sealed-data seal`) without reading the real dataset |
| **`assurance-contracts`** *(upcoming in [OpenAgenticSecurity](https://github.com/OpenAgenticSecurity))* | Optional enterprise L2 protocol suite: 18 closed JSON Schemas & candidate checkers for UI Assurance and Code Health retirement ledgers |

`deps` and `sealed-data` are optional companion repos planned for publication under [OpenAgenticSecurity](https://github.com/OpenAgenticSecurity). Integration steps are in [BOOTSTRAP.md](BOOTSTRAP.md#optional-deterministic-local-enforcement-with-deps-and-sealed-data).

---

## Trust Boundary Reminder

All candidate checks in this repository run from repository-controlled source and are **advisory / not self-attesting**. See [**MATURITY.md**](MATURITY.md) ([中文](MATURITY.zh.md)), [**CONTRIBUTING.md**](CONTRIBUTING.md), [**CODE_OF_CONDUCT.md**](CODE_OF_CONDUCT.md), [**SECURITY.md**](SECURITY.md), and [**LICENSE**](LICENSE).

### Who This Is For (and Honest Limits)

`agentic-sdlc` is built primarily for **software engineers, tech leads, security engineers, and AI-native teams** running Coding Agents on real production or multi-repo codebases.

- **Scope boundary**: This repository focuses on **coding-agent software delivery guardrails** across any language stack (web apps, APIs, CLIs, libraries, or AI products). Full production agent runtime architecture (durable execution, workload identity planes, long-term memory governance, and runtime incident runbooks) intentionally lives in dedicated companion repositories rather than bloating this starter kit.
- **If you are a solo non-engineer Vibe Coder**: `L0` + `skills/` will still prevent ~80% of common disasters (leaked keys, broken auth, fake data, clobbered `main`) and keep your repository clean enough for an engineer to take over later — **but no SDLC template or AI skill can replace human engineering judgment for commercial production**. Before taking customer money on payments, auth, multi-tenant data, or production operations (backups, rate limits, spend caps, incident response), have a qualified engineer review the live system.
