# Frontend Vibe Coding Review Checklist (454-Bug Empirical Study)

**Status**: accepted baseline
**Updated**: 2026-11-20
**Chinese**: [frontend-vibe-coding-review.zh.md](frontend-vibe-coding-review.zh.md)
**Source**: [Frontend Vibe Coding Issues](https://fz.cool/vibe-coding-issues-in-frontend/) (454 deduplicated issues across ~100K LOC React/TS frontend; 321 with identifiable root causes; 216 with identifiable discovery channel)

> **Core Reality**: Backend failures return HTTP 500 and a stack trace;
> frontend failures render a **plausible-looking normal page**. Unit tests,
> TypeScript, and CI caught only **7%** of real issues (most of those from
> browser QA agents); **35%** were hit by humans using the app and **31%**
> required deep audits.

---

## 1. The Four-Question Frontend Acceptance Ladder

Type checking (`tsc`), unit tests, and green CI mostly answer **only Question 1**. Questions 2–4 must be verified in a real browser along the actual user path:

1. **Rendered?** — Does the component mount without crashing?
2. **Reachable?** — Entry point, route guard, role check, and feature flag all agree?
3. **Correct?** — Exact field names, live states, real errors, authoritative source?
4. **Holds at scale?** — Long Markdown/tables, thousands of rows, slow network, cancel, reconnect, narrow viewport?

## 2. Empirical Root-Cause Distribution (Top 4 = 84%)

| Root Cause | Share (of 321) | Primary Manifestations |
|---|---|---|
| **1. Unasserted cross-layer edge** | **39%** | 95% of contract drift, 77% of entry/permission mismatches, 45% of state/timing bugs |
| **2. Holds only at small scale / demo** | **18%** | 45% of state/timing bugs, O(n²) streaming re-renders, silent truncation, unbounded polling |
| **3. Copied from nearby (no shared abstraction)** | **16%** | 70% of duplicate code, 55% of layout defects, repeated call-site workarounds |
| **4. Plausible fallback instead of "unknown"** | **11%** | 55% of plausible fake values (`?? 0`, `|| []`, dead demo fixtures, swallowed errors) |
| **5. Gate / test failure itself** | **4%** | 86% of gate failures (`0 tests collected`, `skip` exiting 0, advisory-only CI) |

---

## 3. Zone-by-Zone PR Review Checklist

### A. Plausible Fake Values (75 issues / 17%)

- [ ] **Audit every `?? 0`, `|| []`, `?? 'agent'`, and `catch { console.error }`**: When a read fails, show an explicit `UNKNOWN` / error state — never a plausible zero or fake default.
- [ ] **Separate three states explicitly**: `loading`, `error`, and `actually empty` must never share an empty array `[]` (prevents flagging healthy items as "disabled/orphaned" while loading).
- [ ] **One authoritative field per display semantic**: Do not let two pages invent conflicting fallback chains (e.g., `sender?.kind ?? (agentId ? 'agent' : 'user')` vs `sender?.kind ?? 'agent'`).
- [ ] **No silent mutation failures**: Failed delete/submit actions must keep the user's input or dialog open and surface the error clearly.
- [ ] **No silent truncation**: Any cap (e.g., 180-char preview, 4,000-char card, top-100 sessions) must disclose truncation and offer expansion/pagination — critical for security artifacts like JWTs or PoCs.
- [ ] **Scrub demo fixtures & fake timers**: Tag mock/demo code unmistakably and scan before shipping so simulated animations or hardcoded fallback models never reach main.

### B. Unasserted Cross-Layer Edges (Entry/Auth 44 + Contract Drift 43)

- [ ] **Disabled-feature 3-layer test**: When a feature flag is `false`, one test verifies all three layers together — UI trigger hidden, direct URL blocked/unavailable, AND backend API returns `403`/`404`.
- [ ] **Backend schema drives frontend fixtures**: Avoid hand-written frontend mocks that mirror wrong camelCase/snake_case field names (e.g., `createdBy` vs `created_by`).
- [ ] **Check both ends of every new surface**: Every new user-facing API must have a verified UI caller; every new admin toggle must have a verified runtime reader (no dead switches).
- [ ] **Isolate bad records**: One malformed row or missing field (e.g., missing `position` on a graph node) must degrade a single card/node, never crash the whole page.
- [ ] **Never save truncated forms over full server records**: If a UI list is capped by an environment limit, saving the form must not silently delete the truncated records.

### C. State & Timing Off the Happy Path (94 issues / 21%)

- [ ] **Single source of truth for state**: Never duplicate messages/entities across both query cache and a local Map patched by refs.
- [ ] **Clear shared caches on auth/session/tenant change**: Logout, session expiry, and identity switch must wipe cached query state.
- [ ] **Test all branches off the straight line**: Verify switch-session, stop/cancel, reload-after-stop, network disconnect vs. user-initiated stop, reconnect, HITL wait/resume, and optimistic-update deduplication in a real browser.
- [ ] **Do not auto-retry non-idempotent POST mutations** without idempotency keys.
- [ ] **3-fixes-in-a-week circuit breaker**: If the same component gets patched 3+ times in a week, stop patching symptoms and re-model its state machine.

### D. Copy-Paste & Structural Constraints (Duplicate 28 + Layout 61 + HTTP Layer 18)

- [ ] **Fix the shared layer on the 2nd occurrence**: Never copy a call-site workaround + comment ("shared client sets `Content-Type: application/json` breaking `FormData`") to a 2nd, 3rd, or 5th upload path.
- [ ] **Do not mock the exact layer under test**: Upload / `FormData` / auth-header / trailing-slash-307 tests must exercise real client serialization at least once.
- [ ] **Make bad patterns unrepresentable in code structure** (rules in docs vanish after context compaction!):
  - Enforce shared page skeletons (`DetailHeader` + single `DetailBody` scroll container) so child panels cannot nest miniature `overflowY: 'auto'` scroll traps.
  - Use `@container` queries instead of viewport media queries inside nested drawers/panes.
  - Wrap single-line controls (`AppTabs`) and forbid raw library imports via lint; bind structural assertions to the route/page registry rather than per-file allowlists.

### E. Scale & Gate Integrity (Scale 23 + Gate Failures 14)

- [ ] **Streaming Markdown / long text**: Parse frozen complete blocks once and render only the live tail (avoid O(n²) re-parse per token); wrap wide Markdown tables in horizontal-scroll containers so flex layouts never blow out.
- [ ] **Virtual lists**: Always set a stable `computeItemKey` using immutable item IDs, never array index.
- [ ] **Polling discipline**: Pause background polling when tab is hidden (Page Visibility API), apply backoff, and split lightweight status endpoints from multi-MB bootstrap payloads.
- [ ] **Test with P99 "large & ugly" fixtures**: Long multi-column tables, thousands of rows, 10+ long localized chart labels spanning 5 orders of magnitude, 4K viewport, and throttled network.
- [ ] **Prove every gate turns red AND blocks merge**:
  - Plant an intentional violation to verify the gate fails.
  - `0 tests collected` and `skip on missing deps` must exit **non-zero**.
  - Lint severity downgrades (`error` → `warn`), new inline `eslint-disable`, and budget bumps require explicit separate-PR review with owner & expiry.
  - Configure gates as **required status checks** in branch/ruleset protection.

---

## 4. Eight Questions Before Frontend Sign-Off

1. Which layer did this verify — only rendered, or reachable, correct, and holding at scale?
2. Was acceptance done only in a terminal, or walked end-to-end in a real browser?
3. When the feature is disabled, do the UI entry, route guard, public flags API, and backend all agree?
4. When a read fails, does the UI honestly show unknown/error instead of `?? 0` or `|| []`? Are long artifacts expandable and backed by a single authority field?
5. Were off-happy-path flows (switch session, disconnect/reconnect, cancel, malformed record) actually tested?
6. Under large text, wide tables, or narrow sidebars, does layout stay intact without nested scroll traps?
7. Is this the 2nd+ occurrence of the same root cause — and if so, was the shared layer fixed?
8. Does the gate actually fail on a planted violation and block merge as a required status check?
