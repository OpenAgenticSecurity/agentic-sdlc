# Versioning & Release Discipline Standard

**Status**: accepted baseline
**Updated**: 2026-11-21
**Chinese**: [versioning-and-releases.zh.md](versioning-and-releases.zh.md)

## Goal

In AI-assisted repositories, versioning fails in predictable ways: coding agents
bump only one of five version manifests, silently jump from `0.x` to `1.0.0`
inside an ordinary bug-fix PR, or conflate human release tags with immutable
machine digests. This standard defines clear **SemVer decision rules**,
**ontological separation of version types**, and **non-self-attesting release
boundaries**.

---

## 1. Keep Four Version Identities Strictly Separate

Never collapse distinct version concepts into a single string:

| Version Layer | Format | Authority / Consumer | Rule |
|---|---|---|---|
| **1. Release Version** | `vMAJOR.MINOR.PATCH[-pre.N]` | Humans, changelogs, package registries | Governs backward compatibility commitments |
| **2. Immutable Revision / Artifact Digest** | 40-char Git commit SHA + `sha256:...` | CI, GitHub Actions, containers, receipts | Machine verification & production deploy bind **digests**, never mutable tags (`:latest`, `@v4`, `@main`) |
| **3. Wire / Schema Contract Version** | `namespace.domain.name.v1` | Producers & consumers of JSON/API schemas | Bump `.v1 -> .v2` **only** on breaking schema changes — never couple mechanically to code releases |
| **4. Feature-Flag Exposure State** | `OFF` (dark ship) vs `ON` (launched) | Platform config / runtime rollout | Dark-shipped code behind default-`OFF` flags may ship in `PATCH`; flipping default to `ON` is `MINOR` |

---

## 2. SemVer Decision Flow

```text
Does the change fix a bug, security flaw, or doc/test error without changing
public API behavior, CLI contracts, or data formats?
├── Yes -> PATCH (vX.Y.Z+1)
└── No  -> Does it add backward-compatible capabilities, commands, options,
           or additive schemas/migrations?
      ├── Yes -> MINOR (vX.Y+1.0, reset PATCH to 0)
      └── No  -> Breaking removal/rename, incompatible protocol/auth/migration,
                 or raised minimum runtime?
            ├── Yes -> MAJOR (vX+1.0.0, reset MINOR & PATCH to 0)
            └── No  -> Internal refactor with zero external impact -> PATCH
```

### Pre-1.0 (`0.x.y`) vs Stable (`>=1.0.0`)

- **`0.x.y` (Pre-1.0)**: Minor versions (`0.1.0 -> 0.2.0`) add capabilities and
  may introduce documented breaking adjustments with migration notes; patches
  (`0.1.0 -> 0.1.1`) remain strictly compatible fixes.
- **`>=1.0.0` (Stable)**: Every `MAJOR` bump requires an ADR, a migration
  guide, an explicit compatibility window, and consumer notification before
  removal.

---

## 3. Hard Agent Rules (Prevent Version Drift & Unauthorized Bumps)

1. **Ordinary feature/fix PRs must NOT bump release versions**: Coding agents
   must never edit release version manifests or invent release tags inside
   routine PRs. Version bumps belong in a dedicated release commit/PR approved
   by an authorized maintainer (Axiom 4: Producer/Judge Separation).
2. **Single source of truth + deterministic consistency test**: Enumerate every
   file that carries the release version (`pyproject.toml`, `package.json`,
   `Cargo.toml`, plugin manifests, Helm `Chart.yaml`, READMEs/site badges) and
   enforce agreement with a deterministic test that fails red if any copy
   drifts (for example, `tests/test_repo_governance.py::test_plugin_manifest_versions_agree`).
3. **Never rewrite or force-move published tags**: Published release tags
   (`vX.Y.Z`) are immutable. If a release has a defect, ship `vX.Y.Z+1` — never
   delete and re-push `vX.Y.Z`.
4. **Pin downstream references to immutable versions**: Downstream repos copying
   templates or calling reusable GitHub Actions must record exact release tags
   plus 40-char commit SHAs (never floating `main`).

---

## 4. Reproducible Release Gate

Every tagged release (`vX.Y.Z`) must be produced by a protected workflow — never
hand-built tarballs uploaded from a developer laptop:

- Re-run the full deterministic verification suite (`make verify-all`) on the
  exact tagged commit.
- Generate release notes deterministically from merged PR categories
  (`.github/release.yml`).
- Publish source/build archives alongside `SHA256SUMS.txt` and **SLSA build
  provenance attestations** (`actions/attest-build-provenance` pinned to 40-char
  SHA).
- Verify deployed artifacts and live runtime readback (not just tag creation)
  before closing the release.

## 5. Consumer Provenance Verification (Close the SLSA Loop)

Publishing attestations does nothing unless consumers verify them at install or
deployment time (SLSA v1.2):

- **Verify before executing or deploying**: Check artifact digest (`SHA256SUMS.txt`),
  cryptographic signature, trusted OIDC issuer/builder, canonical source
  repository, and expected build workflow (for example, `gh attestation verify`
  or `cosign verify`).
- **Fail closed on mismatch**: Reject a valid signature from an unexpected
  repository/builder, a mismatched digest, or a tampered tool/plugin catalog.

## 6. Behavioral Change Admission (Beyond Source-Code Diffs)

In AI-assisted systems, a source-code diff is not the sole release trigger.
Changes to **prompts, skills, tool catalogs, retrieval/index config, memory or
compaction policies, safety policies, or model routing** are behavior-changing
releases:

- Inventory behavioral component identities alongside code revisions (disclose
  explicitly when a hosted model cannot be pinned to an immutable snapshot).
- Require relevant evaluation runs (not just unit tests) and an explicit
  rollback or disable path before promoting behavioral changes.
- Enforce coupled-change checks (e.g. `scripts/check-change-sync.py`) so prompt
  or tool-catalog edits cannot skip regression gates.
