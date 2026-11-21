# DoneClaim Evidence Template

> Use this template in PR descriptions, handoffs, and release verifications.
> `DONE` is derived from dereferenced evidence within explicit limits — never
> self-attested as a bare boolean by an agent.
>
> See [fake-done-dereference.md](fake-done-dereference.md) and
> [done-claim.example.json](done-claim.example.json).

```markdown
## DoneClaim

- **Subject**: `<service / binary / package / UI flow / schema>`
- **Revision**: `<exact 40-char git commit SHA or image digest>`
- **Environment**: `<local / ci / staging / prod-canary + runtime versions>`
- **Predicate**: `<exact user-visible or system property asserted>`
- **Evidence locator**: `<reproducible command, log/artifact path, CI run URL, or trace ID>`
- **Independent observer**: `<different evidence source or role: CI runner / browser QA / secondary reviewer / native readback>`
- **Bridge writer**: `<none | name of seed/harness script if seeded>`

### Four Dereference Checks

- [ ] **Subject identity**: `<PASS | NOT_RUN | NOT_APPLICABLE>` — Verified live process/artifact matches expected revision and handles traffic.
- [ ] **Acceptance predicate**: `<PASS | NOT_RUN | NOT_APPLICABLE>` — Verified end-to-end user/cross-layer rule (not just render or HTTP 200).
- [ ] **Workload / lifecycle**: `<PASS | NOT_RUN | NOT_APPLICABLE>` — Verified under representative/tail load and confirmed clean stop/cancellation/reclamation.
- [ ] **Claim provenance**: `<PASS | NOT_RUN | NOT_APPLICABLE>` — Verified primary sources, consistent denominator, immutable snapshot, and falsifying counterexample.

### Explicit Limits (`does_not_prove`)

- Does NOT prove production capacity or multi-tenant scale beyond `<tested envelope>`.
- Does NOT prove `<untested environment / unverified integration / deferred gate>`.

### Derived Verdict & Ownership

- **Derived state**: `<VERIFIED | PASS | FAIL | NOT_RUN | UNKNOWN | CONFLICT | ERROR | HITL | FAILED>`
- **First breakpoint (if not verified)**: `<exact failing invariant; downstream steps marked not reached>`
- **Risk acceptance / approver**: `<owner handle or pending HITL>`
```
