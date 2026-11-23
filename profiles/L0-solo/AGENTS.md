# AGENTS.md (L0 Solo Baseline)

<!-- Baseline adapted from OpenAgenticSecurity/agentic-sdlc@v0.4.0 (Profile L0-solo) -->
<!-- Non-authoritative projection: prose cannot waive tests, scope, or branch protection. -->

## Session Start

1. Read `docs/VIBE_CODING_CONTEXT.md` and `docs/architecture/STATUS.md`.
2. Run `git fetch --prune origin` and `git status --short --branch`.
3. Never commit directly to `main`. Create a clean worktree from `origin/main`:
   `git worktree add .worktrees/<task> -b <feat|fix|docs|chore>/<topic> origin/main`

## Execution Rules

- **Non-trivial task gate**: For changes touching `>3` files, `>50` lines, or
  startup / auth / deployment / shared contract paths, confirm scope and write
  a brief plan before editing production code; add a failing test before
  changing behavior.
- Declare in-scope files, out-of-scope files, and exact verification commands
  before editing.
- Preserve local changes you did not make; never stash/reset unowned work.
- Do not change UI unless explicitly in scope.
- Never report `NOT_RUN`, `FLAKY`, `ERROR`, or skipped prerequisites as `PASS`.
- Update `docs/architecture/STATUS.md` whenever modules are added, wired, or
  deleted.

## Secure-by-Default Coding Rules (Language-Agnostic)

- **Fail closed**: Default deny on auth, authorization, tenant scope, and policy
  errors; never swallow errors silently on security boundaries (no bare
  `except: pass`, empty `catch {}`, or ignored `err`).
- **No unsafe sinks**: Use parameterized queries only; never use shell command
  interpolation (`shell=True` / `sh -c`), `eval`/`exec`/`new Function`, unsafe
  deserialization, or unguarded outbound URL fetches (defend against SSRF, path
  traversal `..`/symlinks, and ReDoS).
- **Zero hardcoded fallback secrets & safe crypto**: Never hardcode fallback
  secrets on env vars, disable TLS verification (`verify=False` /
  `InsecureSkipVerify`), roll custom crypto, or use static IVs / non-CSPRNG
  tokens.
- **3-layer config boundary**: Check code defaults, shipped deployment templates
  (`.env.example`/Helm/Compose), and live deployed values separately; updating a
  template does not prove existing environments changed.
- **Verify new dependencies**: Confirm every newly added package exists and pin
  exact versions/hashes (anti-slopsquatting); pin GitHub Actions to 40-char SHAs.
- **Prove rejections**: Any change touching auth, tenant isolation, file paths,
  SSRF, crypto, or tool boundaries must include at least one negative security
  test proving invalid/malicious input is rejected.
- **Reliability & performance upfront**: Close every created client/session/handle
  via context managers; require idempotency keys and read-after-write checks on
  `RESULT_UNKNOWN` (never blindly retry mutations); never block async event loops
  or hold DB locks across remote awaits; evolve schemas via migrations only.
- **Coupled artifact sync**: Update coupled tests, contracts, docs, and
  `STATUS.md` in the same PR (back with `scripts/check-change-sync.py`).

## Project-Specific Stack Slots (Fill With Real Commands & Conventions)

- **Quick commands** (build / dev / lint / typecheck / test): replace with this
  repo's real commands.
- **New module wiring pattern**: replace with how new endpoints, services, or
  components are registered and tested here ("wire it or delete it").
- **Language / framework banned patterns**: replace with repo-specific lint or
  architecture red lines (enforced by your linter, not prose alone).

## Verification Before Completion

Run fresh checks and report exact commands + exit codes:

```bash
make agent-check
```
