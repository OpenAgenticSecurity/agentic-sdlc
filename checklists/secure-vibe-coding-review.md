# Secure Vibe Coding Review Checklist

**Status**: accepted baseline
**Updated**: 2026-11-20
**Chinese**: [secure-vibe-coding-review.zh.md](secure-vibe-coding-review.zh.md)
**Authoritative Standard**: [standards/secure-vibe-coding.md](../standards/secure-vibe-coding.md)

> **Core Reality**: AI coding agents optimize for making the happy path work
> quickly. Left unchecked, they silently insert `os.getenv("SECRET", "dev")`,
> skip server-side tenant filters, call `requests.get(url)` with redirects on,
> swallow auth errors in `except Exception`, or invent plausible packages.
> Review every security-relevant diff against this checklist — and require at
> least one **negative security test** proving the attack is rejected.

---

## 1. AuthN, AuthZ & Fail-Open Audit

- [ ] **Fail-closed default**: Missing auth, expired/invalid tokens, unknown roles, or lookup errors return `401`/`403` (never fall through to allow).
- [ ] **Server-side tenant & object ownership**: Every DB query scopes by authenticated `tenant_id` / owner ID — never trusts client-supplied tenant/user IDs or UI-only hiding.
- [ ] **No bare `except Exception` on security boundaries**: Policy, auth, and validation checks do not silently swallow errors or default to permissive values.
- [ ] **Strict JWT / token checks**: Signature, explicit algorithm allowlist (no `alg=none`), `exp`, `iss`, and `aud` verified; constant-time comparison (`hmac.compare_digest`) used for secrets/MACs.
- [ ] **Safe CORS & cookies**: Never `Access-Control-Allow-Origin: *` with credentials; session cookies set `HttpOnly`, `Secure`, `SameSite`; CSRF checked on cookie-authenticated mutations.

## 2. Injection, SSRF, Path Traversal & ReDoS

- [ ] **Parameterized queries**: Zero string-interpolated SQL / Cypher / LDAP / NoSQL queries.
- [ ] **No `shell=True` or dynamic code execution**: Subprocess calls use argument lists; zero `eval` / `exec` / untrusted template injection.
- [ ] **Path containment**: File reads/writes/extractions resolve paths against a fixed root and explicitly reject `..`, leading `/`, control chars, and escaping symlinks.
- [ ] **SSRF-safe outbound HTTP**: User/LLM-influenced URLs enforce `https` allowlist, block private/loopback/link-local/metadata IPs (`169.254.169.254`), disable implicit redirects, and enforce timeouts + max body size.
- [ ] **Safe parsing & rendering**: Zero `pickle` / unsafe `yaml.load` on untrusted input; zero raw HTML/SVG injection (`dangerouslySetInnerHTML`); regexes on untrusted input are linear-time and length-capped.

## 3. Secrets & Cryptography Hygiene

- [ ] **Zero hardcoded fallback secrets**: No `os.getenv("KEY", "default-secret")`, no committed `.env` or private keys; missing required secrets fail startup explicitly.
- [ ] **Zero secret leaks**: No tokens, passwords, or private keys in logs, stack traces, error responses, DB plaintext columns, Docker build layers, or LLM prompts.
- [ ] **No custom crypto / weak primitives**: Vetted library only (`cryptography` / WebCrypto / RustCrypto); no MD5/SHA1 for passwords, no ECB, no static IV/nonce, no `random` for tokens (use `secrets` / CSPRNG).
- [ ] **Key separation & TLS**: Distinct keys per purpose/environment, AEAD or Encrypt-then-MAC, TLS verification enabled (`verify=True` always).

## 4. Supply Chain & CI Hardening

- [ ] **Verify every newly added dependency (anti-slopsquatting)**: Confirm package exists, check upstream repository/maintainer, and lock version + hash.
- [ ] **Pinned CI workflows**: GitHub Actions pinned to 40-char commit SHAs, `permissions: contents: read`, `persist-credentials: false`, `--require-hashes` where supported.
- [ ] **No runtime network installs**: Container entrypoints and agent tools never run `curl | sh` or unpinned package installs at runtime.
- [ ] **AI attribution & license compliance**: Every AI-assisted PR names an accountable human owner and records tool/model provenance; verify the agent did not silently inline third-party copyleft snippets or replace an audited security/crypto dependency without approval and SBOM update.

## 5. Agent & LLM Application Boundaries (If Applicable)

- [ ] **Untrusted data never drives sinks directly**: LLM output and external tool results pass strict schema & policy validation before touching SQL, shell, HTTP, or filesystem writes.
- [ ] **Hardened framing**: Untrusted-data markers resist Unicode invisible chars (`Cf` / default-ignorable) and NFKC folding; evidence extraction parses structured fields rather than regex-scanning raw logs.
- [ ] **Canonical-args approval & tool pinning**: High-risk approvals bind `(action, target, canonical_args_hash)`; MCP tool schemas are pinned against rug-pull drift.
- [ ] **Sealed development data**: Coding agents work against synthetic fixtures or sealed data cards (e.g., via `sealed-data seal` + `deps security-audit`), never live production secrets or raw customer datasets.

## 6. High-Frequency Anti-Pattern Quick Table (`NEVER -> ALWAYS`)

| NEVER Write This | ALWAYS Write This | Why |
|---|---|---|
| `except:` | `except SpecificError as e:` (or `except Exception as e:`) | Bare `except:` catches `SystemExit`/`KeyboardInterrupt` and makes workers unkillable |
| `except Exception: pass` | Log, re-raise, or fail closed (`401`/`403`) | Silent swallowing turns auth/validation failures into silent allow |
| `SECRET_KEY = os.getenv("SECRET_KEY", "dev")` | Required config with startup failure if unset | Hardcoded fallback secrets quietly ship to production |
| `api_key = key or "dummy"` | Raise `401` / fail closed | Fail fast, never fail open with dummy credentials |
| `allow_origins=["*"]` + `allow_credentials=True` | Explicit origin allowlist from env | Open CORS + credentials enables cross-site takeover |
| `f"SELECT * FROM t WHERE id = {x}"` | Parameterized query / bound params | SQL injection |
| `catch (e) { console.error(e) }` | Show explicit error UI & preserve user input | Swallowing write errors misleads users into thinking actions succeeded |
| Commit audit log in a separate transaction | Stage security audit writes inside the caller's transaction | Prevents security-sensitive mutations from succeeding without an audit trail |

## 7. Seven Security Questions Before Merging AI-Written Code

1. What happens when authentication, authorization, or a policy lookup **fails or times out** — does it fail closed?
2. Could an authenticated user from Tenant A read or mutate a resource belonging to Tenant B by changing an ID?
3. Does any new endpoint, parser, or helper accept a URL, file path, shell arg, regex input, or serialized blob from untrusted data?
4. Is there any hardcoded fallback secret, weak crypto primitive, static IV, or `verify=False` introduced anywhere in the diff?
5. If a new package or GitHub Action was added, was its provenance verified and version/SHA pinned?
6. Is there **at least one negative security test** proving an invalid/malicious input is rejected?
7. Did deterministic scanners (SAST / secret scan / `deps security-audit`) actually run with exit code `0` (not skipped)?
