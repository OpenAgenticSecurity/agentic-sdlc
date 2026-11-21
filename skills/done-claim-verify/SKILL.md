---
name: done-claim-verify
description: Use when about to claim a task is done, fixed, passing, deployed or verified, when reviewing someone else's completion claim, or when a green label (tests pass, HTTP 200, config updated) is the only evidence offered.
---

# Done-Claim & Fail-Closed Verification (Standalone Skill)

> **Non-Authoritative Projection**: Local green runs and PR-controlled CI are
> advisory evidence only. An agent cannot self-attest a bare `"done": true` or
> grant trusted merge authority.

## 1. Non-Negotiable Verification Invariants

- **Evidence before claims**: Never report a check as passing without fresh
  command output on the exact current revision. Report exact command, pass/fail
  counts, and exit code.
- **Never blur the Five-Layer Fact Chain**:
  `Evidence (raw) -> VerificationResult (fixed rules) -> Receipt (exact rev) -> Decision (authorized principal) -> Outcome (live reality)`.
- **Never collapse non-green states**: Report `PASS`, `FAIL`, `NOT_RUN`,
  `FLAKY`, `UNKNOWN`, `CONFLICT`, `ERROR`, `NOT_EVALUATED`, `HITL`, or
  `FAILED` explicitly. Missing tools/deps/browsers or `0 tests collected` must
  exit **non-zero** (`NOT_RUN`), never a green skip.
- **Verify committed objects & raw counts**: Check generated/attested artifacts
  against `git show HEAD:<path>` (not only uncommitted working tree bytes), and
  never rely on output-truncating CLI wrappers for factual counts.
- **Verify coupled artifact closure**: Confirm code/API/schema edits also synced
  coupled tests, docs, and `STATUS.md` (via `scripts/check-change-sync.py` when
  configured, using deterministic `git diff` / OpenAPI / AST projections rather
  than blind full-repo scans).
- **Prove gates with negative mutations**: Verify at least one violating/
  malicious input fails for the expected reason while an adjacent legal control
  passes.
- **Respect non-self-attestation**: Any PR touching `.github/workflows/`,
  `CODEOWNERS`, `Makefile`, `AGENTS.md`, `CLAUDE.md`, schemas, checkers, or
  tests **cannot attest itself** and must be flagged for independent mechanism
  review under protected GitHub Rulesets.

## 2. Dereference All Four "Fake-Done" Breakpoints

Mark inapplicable dimensions `NOT_APPLICABLE` — never silently omit:

| Breakpoint | Green Label You Might See | What You Must Dereference |
|---|---|---|
| **1. Subject identity** | Config updated, `active`, version tag | Exact Git commit SHA / artifact digest / live PID + cwd actually handling traffic |
| **2. Acceptance predicate** | Component renders, HTTP 200 | Real end-to-end user path & cross-layer rule agreement (UI + route + backend) |
| **3. Workload / lifecycle** | Good demo run, timeout fired | Representative/tail input, error/cancel paths, and proof workers actually stopped & freed resources |
| **4. Claim provenance** | Polished summary / counts | Exact reproducible commands, exit codes, primary outputs, and `bridge_writer: none` (not verifier self-seeding) |

On multi-stage paths, stop at the **first broken invariant** and mark all
downstream stages `not reached`.

## 3. Emit a Grounded `DoneClaim`

If `deps` is installed locally, attach the replayable receipt from
`deps agent-verify . --receipt .deps/receipt.json`:

```markdown
## DoneClaim

- **Subject**: `<service / module / UI flow / schema>`
- **Revision**: `<exact 40-char git commit SHA or artifact digest>`
- **Environment**: `<local / ci / staging + runtime versions>`
- **Predicate**: `<exact property asserted>`
- **Evidence locator**: `<exact commands run + exit codes + artifact/trace ref>`
- **Independent observer**: `<CI runner / browser QA / secondary reviewer / native readback>`
- **Bridge writer**: `<none | harness/seed name>`
- **Dereference checks**:
  - Subject identity: `<PASS | NOT_RUN | NOT_APPLICABLE>`
  - Acceptance predicate: `<PASS | NOT_RUN | NOT_APPLICABLE>`
  - Workload / lifecycle: `<PASS | NOT_RUN | NOT_APPLICABLE>`
  - Claim provenance: `<PASS | NOT_RUN | NOT_APPLICABLE>`
- **Derived state**: `<VERIFIED | PASS | FAIL | NOT_RUN | UNKNOWN | CONFLICT | ERROR | HITL | FAILED>`
- **First breakpoint (if any)**: `<none | exact failing invariant>`
- **Explicit limits (`does_not_prove`)**:
  - Does NOT prove `<untested scale / environment / production deployment / unrelated regressions>`
```

*Optional full reference & read-only GitHub Ruleset observer*: `https://github.com/OpenAgenticSecurity/agentic-sdlc` (`checklists/fake-done-dereference.md`, `scripts/observe-github-ruleset.py`).
