# External Enforcement Evidence Candidate Contract

**Status**: candidate contract; read-only observation; not trusted enforcement

**Updated**: 2026-11-21

This contract closes a governance evidence gap that cannot be closed by a green
local test, a present CI job, or a `CODEOWNERS` entry. It defines a stable,
machine-readable carrier for an independently observed GitHub ruleset. The
carrier is useful for diagnosing whether a repository's intended protection is
actually represented by the observed ruleset, while remaining explicitly below
the trusted-enforcement boundary.

## Scope and report identity

The schema is
[`enforcement-evidence.v1.schema.json`](enforcement-evidence/schema/enforcement-evidence.v1.schema.json).
Every report must set `authority=candidate` and `trusted=false`. It binds:

- the repository and default branch;
- the exact ruleset API reference and a `sha256:` response digest supplied by
  the external observer; and
- the normalized policy expectation and the observed active branch ruleset.

The checker does not fetch the API or recompute the external response digest.
The observer owns that read-only acquisition, retention of the raw response,
and the mapping from the API response to this normalized shape. `observed_at`
is descriptive evidence, not proof that the state remains current.

Arrays that represent sets are sorted and unique. In particular, policy status
contexts, observed status contexts, branch include/exclude patterns, and bypass
actor tuples are deterministic. This prevents equivalent observations from
being hidden behind ordering or duplicate-key normalization.

## Required protection semantics

The normalized observation is accepted only when all of these comparisons hold:

| Boundary | Required observation |
|----------|---------------------|
| Source binding | Repository, ruleset ID, and API reference identify the same object |
| Scope | An active branch ruleset covers the default branch and does not exclude it |
| Status | Every policy-required status context is present in the observed pull-request rule |
| Status source | When `require_status_check_source_binding=true`, every required status check binds a positive `integration_id` (not `null` / "any source") |
| Review | Observed approving-review count is at least the policy minimum |
| Review integrity | Code-owner review, stale-review dismissal, and last-push approval are enabled |
| Bypass | No actor has unconditional (`always` / `exempt`) bypass, and any `pull_request` bypass actor must appear in `policy.allowed_pull_request_bypass_actors` |

Missing required status checks, an unbound status-check source (`integration_id=null`),
disabled last-push approval, an unconditional or unapproved `pull_request` bypass actor,
an inactive or wrong-target ruleset, a source/repository mismatch, or an uncovered default
branch fail closed. A malformed report, duplicate JSON key, unsafe reference, invalid
RFC 3339 timestamp, or non-deterministic set is also a failure.

The committed mutation fixtures isolate these failure modes:
`missing-required-status.json`, `unbound-status-source.json`,
`last-push-disabled.json`, `unconditional-bypass.json`,
`unapproved-pr-bypass.json`, and `source-mismatch.json`. The valid fixture is a
regression control for checker behavior only; it is not a statement about the
current remote ruleset of any repository.

## Authority and non-goals

This is a candidate evidence contract. It does not:

- call GitHub, change a ruleset, grant a bypass, or authorize merge/release;
- select, skip, or narrow a product test suite;
- establish required status, protected execution, CODEOWNER approval,
  independent mechanism review, or admin-bypass independence; or
- turn exact-head CI success, job presence, a local fixture, or a `CODEOWNERS`
  match into trusted enforcement.

An external observer, an architecture/contract owner, and an independent
mechanism reviewer remain separate governance requirements. A product adapter
may publish this evidence as shadow/advisory data, but must retain its own
real API acquisition and repository wiring proof. A missing observer or raw
response is `NOT_RUN`, not a successful skip.

## Local contract gate

The checker is intentionally network-free and bounded:

```bash
set -euo pipefail
make governance-enforcement-evidence-check
```

`make check` invokes the same target, so documentation-only changes do not
require a mechanical frontend or backend full suite. The affected-closure
rules in the [testing strategy](../testing-strategy.md) still decide when a
shared contract, schema, generated client, auth/permission, serialization,
WebSocket, SSR/BFF, or shared-build change joins the frontend and backend
closure. This contract never replaces those product-local tests or the
periodic full and release suites.

Changes to this schema, checker, fixtures, Make wiring, or governance wording
are enforcement-surface changes. They require the architecture/contract owner
and a second independent mechanism reviewer; this document cannot provide
either approval itself.
