---
name: secure-vibe-coding
description: Use when writing or reviewing code that touches authentication, authorization, tenant or owner scoping, SQL, shell commands, file paths, outbound URLs, secrets, cryptography, new dependencies, CI workflows or LLM tool boundaries, and when debugging environment variables or credentials.
---

# Secure Vibe Coding Guardrails (Standalone Skill)

> **Non-Authoritative Projection**: This skill enforces secure coding defaults
> inside the editing loop; back critical boundaries with SAST/secret scanners,
> negative security tests, and `deps`.

## Mandatory Coding Invariants (Language-Agnostic)

1. **Fail closed on auth, authz, and tenant boundaries**: Default deny on
   missing/invalid credentials, errors, or unknown roles. Filter every query by
   server-side authenticated tenant/owner scope. Never swallow errors silently on
   security paths (e.g., bare `except Exception: pass`, empty `catch {}`, or
   discarded `err` in Go); stage security audit writes inside the caller's
   transaction.
2. **Defend dangerous sinks deterministically**:
   - Parameterized queries only (zero string-formatted SQL/NoSQL).
   - Argument-array process execution (`shell=False` / `execFile` / `exec.Command`
     without `sh -c`); never `eval`/`exec`/`new Function`.
   - Resolve file/archive paths under a fixed root and reject `..` and escaping
     symlinks.
   - Guard outbound URLs against SSRF (allow `https`, block private/loopback/
     metadata `169.254.169.254`, disable implicit redirects, set timeouts/size
     caps).
   - Never use unsafe deserialization (`pickle`, unsafe `yaml.load`, Java
     `ObjectInputStream`) or unsanitized HTML injection; keep regexes
     linear-time with input length caps.
3. **Zero hardcoded fallback secrets & safe crypto**:
   - Never fall back to hardcoded dev secrets (e.g.,
     `os.getenv("SECRET_KEY", "dev-secret")` / `process.env.JWT_SECRET || "dev"`)
     or log/expose secrets.
   - Never invent custom crypto, reuse keys/nonces, use static IVs, use
     non-CSPRNG randomness for security tokens, or disable TLS verification
     (`verify=False`, `InsecureSkipVerify: true`, `danger_accept_invalid_certs`).
   - Use AEAD / Encrypt-then-MAC and constant-time comparison (e.g.,
     `hmac.compare_digest`, `crypto.timingSafeEqual`, `subtle.ConstantTimeCompare`).
4. **Verify supply chain before adding dependencies**: Confirm every new
   package exists and is trustworthy (anti-slopsquatting); pin versions/hashes
   and pin GitHub Actions to 40-char commit SHAs.
5. **Prove rejections with negative security tests (Red-before-Green)**: Every
   change touching auth, tenant isolation, file paths, SSRF, crypto, or tool
   boundaries must add at least one negative test asserting the attack/invalid
   input is rejected (`401`/`403`/`ValueError`).
6. **Keep sensitive data & live secrets out of agent context**:
   - When debugging env/secret issues, check **existence only**
     (`[ -n "${VAR:-}" ] && echo present`) — never echo/print secret values;
     isolate tests with `env -u VAR`.
   - Use synthetic fixtures or sealed data workflows (`sealed-data seal` for
     datasets, `deps security-audit` for secret literals, when those tools are
     installed) instead of reading raw production datasets or secret files.
7. **Defend agent tool boundaries**: Default every tool to `mutating` (never
   classify read-only by name substring like `read`/`get`/`check`), route
   side-effecting LLM output through a closed validated IR, and isolate
   outbound web/fetch tools on sessions that read sensitive internal data
   (prevents read-only exfiltration).

*Optional full standard & checklist*: `https://github.com/OpenAgenticSecurity/agentic-sdlc` (`standards/secure-vibe-coding.md`, `checklists/secure-vibe-coding-review.md`).
