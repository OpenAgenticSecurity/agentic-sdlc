# Architecture & Implementation Status

**Updated**: YYYY-MM-DD

**Rule**: If any design doc or roadmap disagrees with this file, trust this
file and verify against real source code.

## Status Legend

- `Verified`: source exists, wired into runtime, covered by passing tests.
- `Partial`: source exists, incomplete, flag-gated, or not fully wired.
- `Deleted`: previously existed, now removed — agents must not assume it exists.
- `Design`: design document only; no production implementation.
- `Planned`: roadmap item; not current behavior.
- `Gap`: documentation claim exceeds code reality.

## Module Reality Table

| Module / Capability | Status | Real Entrypoint | Verification Command | Notes |
|---|---|---|---|---|
| Example Auth Guard | `Verified` | `src/auth/guard.py` | `pytest tests/test_auth.py` | Fail-closed on missing token |
| Legacy V1 Exporter | `Deleted` | — | — | Removed in PR #12; do not re-reference |
