# Independent Mechanism Reviewer Checklist (L2 Governed)

Use this checklist whenever a PR modifies an **enforcement surface** (CI
workflows, Make targets, schemas, checkers, compilers, test selectors,
`CODEOWNERS`, PR templates, `AGENTS.md`, or `CLAUDE.md`).

> Candidate CI running from the PR head is **not self-attesting**.

## 1. Exact Revision & Provenance

- [ ] CI checked out the exact PR head SHA (`git rev-parse HEAD == EXPECTED_SHA`).
- [ ] No new push invalidated earlier approvals (`require_last_push_approval` is on).
- [ ] All dependencies installed with hash pinning or locked runtime digests.

## 2. Fail-Closed Integrity

- [ ] Missing tools, missing files, invalid JSON, duplicate keys, symlinks, or
      unsafe paths exit non-zero (`NOT_RUN` / `ERROR` / `FAIL`), never green skip.
- [ ] At least one **negative mutation fixture/test** proves a tampered input
      cannot pass.
- [ ] No new silent fallback (`|| []`, `?? 0`, bare `except Exception`) hides
      verification failure.

## 3. Authority Separation

- [ ] Agent prose, commit messages, PR labels, or dirty worktrees cannot narrow
      affected-test closure, reduce derived risk, or waive obligations.
- [ ] Writing maintainer commands (`*-generate`) remain excluded from
      read-only validation gates (`*-check`).
- [ ] Live branch ruleset protection was independently observed
      (`scripts/observe-github-ruleset.py`) rather than assumed from `CODEOWNERS`.
