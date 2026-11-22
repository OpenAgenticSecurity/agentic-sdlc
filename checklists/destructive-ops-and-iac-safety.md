# Destructive Ops, Database Migration & IaC Safety Checklist

**Status**: accepted baseline
**Updated**: 2026-11-22
**Chinese**: [destructive-ops-and-iac-safety.zh.md](destructive-ops-and-iac-safety.zh.md)

> **Why This Exists**: Public postmortems of coding agents damaging live
> production systems share four recurring patterns: (1) local `.env` files
> pointing at production databases during a forced schema push or cleanup,
> (2) written rules or `/careful` modes failing to stop a destructive CLI call,
> (3) agents bypassing `terraform/production/*` path bans by editing shared
> modules (`terraform/modules/shared/`), and (4) deleting same-account
> snapshots or missing object-storage assets during migration cleanup.

---

## 1. Environment & Credential Physical Isolation

- [ ] **Zero production credentials in coding-agent environments**: Dev/test
  workstations, local `.env`, and coding-agent sandboxes must never hold live
  production DB URLs, cloud admin keys, or deploy tokens.
- [ ] **Separate human-gated production roles**: Production applies, DB drops,
  and cluster mutations require a separate role or human-triggered workflow
  that the coding agent cannot assume on its own.
- [ ] **Block destructive schema & cleanup shortcuts**: Forbid agent execution
  of `db push --force-reset`, `DROP TABLE`, `DROP COLUMN`, `TRUNCATE`,
  `terraform destroy`, or `kubectl delete` against any non-ephemeral target.

## 2. IaC & Shared-Module Blast-Radius Guardrails

- [ ] **Govern shared IaC modules at the highest environment tier**: Protect
  cross-environment modules (`terraform/modules/shared/**`, shared Helm charts)
  with the exact same `CODEOWNERS` and multi-reviewer rulesets as `production/`.
- [ ] **Protect stateful resources against aggressive drift reconciliation**:
  Require `lifecycle { prevent_destroy = true }` on databases, storage buckets,
  and KMS keys; require explicit human sign-off on any `-/+ replace` or
  `destroy` line in a Terraform plan.
- [ ] **Enforce staging bake windows**: Never allow an agent to open an
  auto-merge production deploy PR immediately (0-minute bake) after staging
  turns green; encode mandatory bake-time gates in CI/CD, not Confluence prose.
- [ ] **Verify container hardening on infra diffs**: Reject `privileged: true`,
  mutable `:latest` tags, and missing `read_only` / `no-new-privileges` /
  `cap_drop: ALL` in deployment manifests.

## 3. Agent-Unreachable Backups & Whole-Asset Verification

- [ ] **Keep backups outside agent credential reach**: Store authoritative
  backups/snapshots in a separate account, vault, or immutable object-lock
  bucket that the agent's credentials cannot delete or overwrite.
- [ ] **Verify every storage plane before deleting old resources**: Never
  approve a migration cleanup solely on DB row counts — independently verify
  object/blob storage, file assets, checksums, and a sample restore.
- [ ] **Independently verify agent disaster/rollback claims**: When an agent
  claims *"safe to delete"* or *"rollback is impossible"*, verify directly via
  read-only probes and Git/snapshot history before acting.
