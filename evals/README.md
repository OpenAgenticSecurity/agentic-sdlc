# Deterministic Guardrail & Skill Evaluation Suite

**Updated**: 2026-11-21
**Chinese**: [README.zh.md](README.zh.md)

Never trust a guardrail or skill on prose claims alone. This directory holds
two complementary evaluation tracks:

## 1. Deterministic Guardrail Evals (Zero Network, Zero `pip install`)

Run the offline polyglot planted-trap benchmark against `scripts/audit-repo.py`
(pure Python 3.11+ standard library, executes in ~1 second):

```bash
python3 -S scripts/run-evals.py
# Or via Makefile:
make eval-deterministic
```

It synthesizes 14 isolated cases — **12 planted-violation traps** (missing
context/worktree hygiene, unpinned GitHub Actions, missing `permissions` /
`persist-credentials: false`, `@org/` CODEOWNERS placeholder, Python fail-open
`except: pass` / `shell=True` / hardcoded fallback secret, JS/TS
`dangerouslySetInnerHTML` + `--passWithNoTests`, Go `InsecureSkipVerify` /
`sh -c`, Rust `danger_accept_invalid_certs`, Java `Runtime.exec` /
`ObjectInputStream`, and weak GitHub Rulesets allowing post-approval push or
unbound `integration_id: null`) plus **2 clean polyglot controls** — asserting
100% planted-trap recall and 0% false positives.

## 2. Agent Skill Evals (`evals/skills/`)

Structured `prompt.md` + `graders/rubric.md` cases compatible with paired A/B
evaluations (e.g. `claude plugin eval`):

| Case | Target Skill(s) | What It Tests |
|---|---|---|
| [`fake-done-dereference`](skills/fake-done-dereference/prompt.md) | `done-claim-verify` | Refusing to call `0 tests collected` + untested staging a green `PASS`; emitting `DoneClaim` with `does_not_prove[]` |
| [`three-layer-default-and-liveness`](skills/three-layer-default-and-liveness/prompt.md) | `audit-production-readiness` | Catching a dead spend guard whose production writer is missing + 3-layer default mismatch (code `False` vs `.env.default` `1`) |
| [`secure-vibe-coding-ssrf-idor`](skills/secure-vibe-coding-ssrf-idor/prompt.md) | `secure-vibe-coding` | Enforcing server-side tenant scope, SSRF `169.254.169.254` blocking, zero hardcoded fallback secret, and negative security tests |
