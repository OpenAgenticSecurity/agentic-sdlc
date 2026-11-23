# Profile L2 — High-Assurance / Governed Engineering

Build on top of [`L1-team`](../L1-team/README.md) when agents touch security
controls, auth boundaries, shared contracts, production infrastructure, or
critical user journeys.

## 1. GitHub Non-Self-Attestation Files Included

| File Here | Target Path in Your Repo | Purpose |
|---|---|---|
| `CODEOWNERS.example` | `.github/CODEOWNERS` | Isolates enforcement surfaces (`.github/`, `scripts/`, `Makefile`, `AGENTS.md`, `CLAUDE.md`) for owner review — replace `@org/...` with verified org teams that have Write permission (or individual `@handle`s); `audit-repo.py --profile L2` fails closed if `@org/` remains |
| `github-ruleset.import.json` | Import via GitHub UI (`Settings -> Rules -> Rulesets -> Import a ruleset`) | Ready-to-import GitHub Repository Ruleset enforcing PR reviews, CODEOWNERS, stale dismissal, last-push approval, source-bound status checks (`integration_id: 15368` = GitHub Actions; change if using another CI App), and zero bypasses |
| `ruleset-policy.example.json` | `.github/ruleset-policy.json` | Expected GitHub Ruleset policy (`required_status_contexts` should match your real CI job names; `require_status_check_source_binding: true` rejects spoofable `integration_id: null`; `allowed_pull_request_bypass_actors: []` rejects unapproved `pull_request` bypass actors) |
| `mechanism-review-checklist.md` | `docs/mechanism-review-checklist.md` | Independent checklist for the second mechanism reviewer on enforcement-surface PRs |

## 2. Audit Your Live GitHub Ruleset (Read-Only)

```bash
python3 /path/to/agentic-sdlc/scripts/observe-github-ruleset.py \
  --live \
  --repo owner/your-repo \
  --ruleset-id 12345 \
  --default-branch main \
  --policy .github/ruleset-policy.json \
  --output ruleset-evidence.json \
  --validate
```

`--validate` needs `jsonschema`; install the hash-locked set once with
`python3 -m pip install --require-hashes --only-binary=:all: -r /path/to/agentic-sdlc/requirements-test.txt`.

## 3. Upcoming Local Carrier (`deps` & `sealed-data`)

Pair `L2` GitHub ruleset protection with the upcoming sibling Rust CLIs under
[OpenAgenticSecurity](https://github.com/OpenAgenticSecurity) (`deps` for local
Architecture-as-Code, secret-reference audits, and agent lifecycle hooks;
`sealed-data` for dataset sealing) once published. Teams building custom
protected Guardians can also adopt the closed JSON Schema contracts under
[`standards/`](../../standards/README.md).
