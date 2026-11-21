# Security Policy

## Scope

`agentic-sdlc` contains specifications, JSON Schemas, deterministic checkers,
and governance scripts intended to reduce risk when AI coding agents participate
in software delivery. Adopters copy these files into their own repositories, so
a flaw here can weaken a control somewhere else.

In scope:

- A way for malformed or adversarial input (symlinks, duplicate JSON keys,
  non-canonical paths, environment injection, crafted GitHub API responses) to
  make a fail-closed check pass, or to make a script write outside its target.
- A template under `profiles/` or a skill under `skills/` that instructs an
  agent to do something unsafe by default.
- A shipped workflow that leaks credentials or runs unpinned third-party code.

Out of scope: weaknesses in an adopter's own configuration after they changed
the templates, and the explicit non-goals listed in [MATURITY.md](MATURITY.md).

## Supported Versions

Security fixes are made on `main` and included in the next tagged release.
Before `v1.0.0` only the latest release is supported.

## Reporting a Vulnerability

1. **Do not** open a public issue with exploit details before triage.
2. Report privately through
   [GitHub Security Advisories](https://github.com/OpenAgenticSecurity/agentic-sdlc/security/advisories/new).
3. Include:
   - Affected script, schema, template, or skill path
   - Minimal reproduction fixture or command
   - Expected fail-closed behavior vs. observed bypass
   - Exact Python / Bash / OS / Git version and the commit SHA you tested

We aim to acknowledge reports within 72 hours. Every fix ships with a
regression test that fails on the vulnerable revision.

## Security Design Expectations

- All checkers must **fail closed** on missing dependencies, malformed JSON,
  duplicate object keys, non-canonical paths, symlinks, or invalid Git inputs.
- Never replace `NOT_RUN`, `FLAKY`, `ERROR`, `UNKNOWN`, or `NOT_EVALUATED` with
  a green `PASS`.
- Never embed raw credentials, tokens, private keys, or host-specific user
  paths into fixtures, logs, receipts, or documentation.
