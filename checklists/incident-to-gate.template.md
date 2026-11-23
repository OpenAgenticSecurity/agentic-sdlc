# Incident-to-Gate Closed-Loop Template (Asymmetric Evolution)

Use this template whenever a defect escapes to `main`/production, a near-miss is
caught in staging/ops, or the same review defect class appears a **second
time**. Prose postmortems decay across agent sessions; close the incident only
after a deterministic check turns red on the vulnerable pattern.

```markdown
# Incident-to-Gate: <short title>

- **Date (UTC)**: `<YYYY-MM-DD>`
- **Accountable Owner**: `<@handle>`
- **Escaping Commit / Config / Model**: `<40-char SHA or config ref>`
- **Violated Ontological Axiom**: `<A1 Reality>Memory | A2 Coupled Closure | A3 Non-Collapsing State | A4 Non-Self-Attestation | A5 Asymmetric Evolution>`
- **Security / Failure Track**: `<Track A: AI-Amplified AppSec | Track B: Agent-Native / Reward Hacking | Reliability / Scale>`

## 1. What Escaped & Why Existing Gates Missed It

- **Observed failure / near-miss**: <one-paragraph factual description>
- **Why prior checks stayed green**: <e.g., unit test mocked transport / missing negative test / ruleset allowed post-approval push / shared IaC path unguarded>

## 2. Graduated Deterministic Gate (Mandatory Red -> Green Proof)

- **Gate location**: `<test file:line | linter rule | scripts/... | GitHub Ruleset>`
- **Planted violation proof (MUST FAIL)**:
  - Command: `<exact command>` -> exit `<non-zero>`
- **Adjacent legal control (MUST PASS)**:
  - Command: `<exact command>` -> exit `0`

## 3. Asymmetric Safety Check

- [ ] New rule/memory **only tightens constraints or adds verification** (never auto-expands permissions, drops HITL approvals, or adds permanent ignore allowlists).
- [ ] Coupled `STATUS.md` / checklist / `CODEOWNERS` updated in the same PR.
```
