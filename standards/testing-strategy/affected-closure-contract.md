# Affected-Test Closure Candidate Contract

**Status**: candidate contract; shadow/advisory only

This contract gives product repositories a common machine-readable carrier for
affected-test advice. It does not own a product's path map, import graph, test
entrypoints, CI conditions, required status, or merge authority. Those remain
product-local implementation facts and must be reviewed in the product
repository.

## Report identity

Reports use the closed schema
[`affected-closure-report.v1.schema.json`](schema/affected-closure-report.v1.schema.json)
and `schema_version=openagenticsecurity.testing.affected-closure-report.v1`. A report is always
`authority=candidate` and `trusted=false`. It binds to full lowercase base/head
Git SHA-1 values, or carries an explicit bounded error with both revisions
`null`. Changed paths are repository-relative, safe POSIX paths from a
no-rename NUL-delimited name-status diff; they are ordered by path and status.

The only classifications are `docs_only`, `frontend_only`, `backend_only`,
`shared_boundary`, and `full`. Reasons and recommended suite identifiers are
stable and unique. A product adapter must resolve every recommended suite to a
real repository entrypoint; this contract never embeds a second pytest, build,
integration, browser, or selector implementation.

## Fail-closed and shadow rules

- `shadow` reports set `shadow_only=true`; `pull_request_fast_path` reports set
  it to `false`, but both remain candidate evidence.
- Invalid Git input, an empty diff, an unknown/unmerged status, malformed or
  unclassified paths, and security, migration, governance, CI, deployment, or
  release boundaries must result in `full`. An error report has no claimed
  revisions or changes and includes `full_boundary:git_error`.
- `docs_only` may not recommend a frontend, backend, integration, browser, E2E,
  agent, or full suite. A product's documentation allowlist must be explicit;
  a `.md` suffix alone is never sufficient.
- Reports cannot select or skip tests, alter required status or branch
  protection, bypass review, or authorize merge/release. Periodic, full, and
  release compatibility suites remain independent backstops.
- No timestamp, username, hostname, local absolute path, PR label, commit
  message, environment hint, or dirty working-tree byte may affect the report.

## Local contract gate

The committed valid/invalid fixtures and mutation proof are checked without
starting a product runtime:

```bash
make affected-test-closure-check
```

The check validates schema closure, duplicate-key rejection, deterministic
ordering, exact revision/error semantics, shadow-only boundaries, and the
docs-only anti-expansion rule. It does not claim that a product adapter's
suite names or path rules are correct; each product must add its own real Git
diff and entrypoint wiring proof.

The committed suite catalogue must contain at least one stable suite ID and a
non-empty product-owned entrypoint descriptor for every ID. The checker only
checks that a recommended ID is present and resolvable in this catalogue; it
never interprets or executes the descriptor.

Repository-local classifiers remain product-owned candidate adapters. Adopting
this shared carrier, publishing real-PR shadow observations, and measuring
false positives/negatives are separate steps. No trusted enforcement or test
skipping authority is created by this document or its checker.
