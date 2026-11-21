# Contributing to OpenAgenticSecurity

Thank you for contributing to `OpenAgenticSecurity/agentic-sdlc`. Because this
repository owns machine-verifiable Agentic SDLC standards, schemas, and
checkers, contributions follow the same evidence-first rules documented in
`standards/`.

## What Makes a Good Contribution

- **A checklist item or rule backed by a real failure.** Open a
  "Checklist or standard proposal" issue and describe the incident, bug or
  measurement that motivates it.
- **A bug fix with a test that fails first.** Especially anything that lets a
  check pass when it should fail.
- **A template that works on a stack we do not cover yet.** Run it on a real
  repository and say which one.

Vulnerabilities go through [SECURITY.md](SECURITY.md), not public issues.

## Core Rules

1. **One task, one branch, one worktree, one explicit scope.** Do not develop
   directly on `main`.
2. **Evidence before assertions.** Run fresh local verification commands before
   opening a PR and paste exact commands and results into the PR body.
3. **Negative fixtures matter as much as happy paths.** Every new schema rule,
   invariant, or security control should add at least one failing mutation test
   proving invalid input cannot silently become green.
4. **Enforcement surfaces are not self-attesting.** PRs touching `scripts/`,
   `tests/`, `standards/**/schema/**`, `Makefile`, `.github/**`, `skills/**`,
   `.*-plugin/**`, `llms.txt`, `AGENTS.md`, or `CLAUDE.md`
   require review by both the architecture/contract owner and a second
   independent mechanism reviewer.
5. **Preserve bilingual parity.** Keep English (`*.md`) and Chinese (`*.zh.md`)
   core standards and checklists aligned when changing normative behavior.
6. **Never commit secrets, credentials, personal paths, or customer data.**

## Minimum Verification Before PR

Install hash-locked test dependencies (Python 3.11+):

```bash
python3 -m pip install --require-hashes --only-binary=:all: -r requirements-test.txt
```

For documentation-only changes:

```bash
make check
```

For changes touching schemas, scripts, tests, CI workflows, plugins, skills, or
agent instructions:

```bash
make verify-all        # contract checks, docs check, Ruff, full pytest suite
make static-analysis   # ShellCheck + actionlint from digest-pinned images (needs Docker)
```

CI runs `make verify-all` on Ubuntu (Python 3.11 and 3.13) and macOS, plus
`make static-analysis`.

Never edit generated JSON fixtures or digests by hand without running
`make verify-all` to prove deterministic schema closure and negative mutations
stay green.

## Changing Test Dependencies

`requirements-test.txt` is a hash-locked file generated from
`requirements-test.in`. Edit the `.in` file, then regenerate the lock with
[uv](https://docs.astral.sh/uv/):

```bash
uv pip compile requirements-test.in --universal --generate-hashes \
  --no-header --no-annotate --python-version 3.11 -o requirements-test.txt
```

## Releasing

Plugin manifests under `.claude-plugin/`, `.cursor-plugin/` and `.codex-plugin/`
carry the version, and `skills/README.md` / `skills/README.zh.md` cite it.
`tests/test_repo_governance.py::test_plugin_manifest_versions_agree` lists every
file and fails if one is missed. Bump them together, then push a `v<version>`
tag. The release workflow re-runs `make verify-all` and publishes a source
archive with SHA-256 checksums; release notes are generated from merged PRs.
