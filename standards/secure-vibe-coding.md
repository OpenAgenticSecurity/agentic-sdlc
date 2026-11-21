# Secure Vibe Coding Standard

**Status**: accepted baseline
**Updated**: 2026-11-20
**Chinese**: [secure-vibe-coding.zh.md](secure-vibe-coding.zh.md)

## Goal

Vibe Coding accelerates code generation, which also accelerates shipping
predictable security vulnerabilities. Most AI-introduced vulnerabilities are not
exotic zero-days — they are fail-open fallbacks, missing authorization/tenant
checks, unsafe sinks, hardcoded dev secrets, broken cryptography defaults,
hallucinated dependencies, and unguarded LLM/tool boundaries.

This standard defines the **non-negotiable secure-by-default coding invariants**
for AI-assisted code, how to prove them with negative tests, and how to enforce
them deterministically with static gates and **`deps`** as the local engineering
carrier.

---

## 1. AuthN, AuthZ & Fail-Open Prevention

- **Default deny on every boundary**: Missing credentials, expired tokens,
  unknown roles, lookup errors, or unrated actions must fail closed (`401`/`403`
  or explicit rejection) — never fall through to an allow branch.
- **No silent exception swallowing on security paths**: Never write bare
  `except Exception: pass` or fallback values (`?? true`, `|| []` treated as
  "no restrictions") around auth, policy, validation, or tenant checks.
- **Enforce tenant and object ownership server-side (anti-IDOR)**: Every read,
  write, update, and delete on tenant- or user-owned resources must filter by
  authenticated principal/tenant scope in the data query itself — never trust
  client-supplied `tenant_id` / `user_id` or UI-only hiding.
- **Strict token validation**: Verify cryptographic signature, explicit allowed
  algorithms (reject `alg=none` and symmetric/asymmetric confusion), `exp`,
  `nbf`, `iss`, and `aud`; use constant-time comparison (`hmac.compare_digest`
  or equivalent) for tokens and MACs.
- **Safe web defaults**: Never combine `Access-Control-Allow-Origin: *` with
  `Access-Control-Allow-Credentials: true`; enforce CSRF protection on
  cookie-authenticated state changes; set `HttpOnly`, `Secure`, and `SameSite`
  on session cookies.

## 2. Injection, SSRF, Path Traversal & ReDoS

- **Parameterized queries only**: Never build SQL, Cypher, LDAP, or NoSQL
  queries with string formatting or concatenation.
- **No shell interpolation**: Prefer argument arrays (`subprocess.run([...],
  shell=False)`); never pass untrusted input into `shell=True`, `eval`, `exec`,
  or template engines without strict escaping.
- **Canonical path containment (anti-traversal / zip-slip)**: Resolve target
  paths (`Path.resolve()`), verify containment under the intended root, and
  explicitly reject `..`, absolute paths, control characters, and symlinks
  escaping the root before reading, writing, or extracting archives.
- **SSRF & DNS rebinding defense**: Never pass user- or LLM-controlled URLs
  straight to `requests.get` / `httpx` / `fetch`. Enforce scheme allowlists
  (`https`), resolve DNS before connecting, block loopback / RFC1918 / link-local
  / cloud metadata IPs (`169.254.169.254`, `fd00::/8`, etc.), disable implicit
  HTTP redirects, and enforce strict connect/read/total timeouts and response
  size caps.
- **Safe deserialization & rendering**: Never use `pickle`, `marshal`, or
  unsafe `yaml.load` on untrusted data (use `yaml.safe_load` / JSON with strict
  schema validation); forbid raw HTML/SVG injection (`dangerouslySetInnerHTML`,
  unsanitized Markdown HTML).
- **Linear-time regexes & input caps**: Avoid nested quantifiers and overlapping
  alternations in parsers and redactors (prevent catastrophic ReDoS); cap input
  length before matching.

## 3. Secrets & Applied Cryptography Operations

- **Zero hardcoded fallback secrets**: Never write patterns like
  `os.getenv("SECRET_KEY", "dev-secret")` or commit real credentials, private
  keys, or `.env` files. Missing required secrets must fail startup cleanly.
- **Never expose secrets in sinks**: Credentials, tokens, and private keys must
  never be logged, placed in error messages, stored in plaintext DB columns,
  baked into Docker layers, or injected into LLM prompts.
- **Never roll your own crypto**: Do not invent custom ciphers, custom AK/SK
  substring schemes, or hand-written crypto primitives. Use vetted standard
  libraries (`cryptography`, WebCrypto, libsodium, RustCrypto).
- **Operational cryptography invariants**:
  - **Value parity**: Protect keys with the same rigor as the highest-value data
    they guard; store private keys in KMS / HSM / Vault, not local plaintext
    files.
  - **No static IVs/nonces**: Generate fresh cryptographically random nonces
    (`secrets` / CSPRNG — never `random`) per encryption operation (e.g.,
    AES-GCM / ChaCha20-Poly1305 with authenticated AAD).
  - **Strict key separation & lifecycle**: Never reuse one key across distinct
    purposes (e.g., signing vs. encryption, prod vs. test), never reuse a nonce,
    and enforce rotation/expiry rather than permanent keys.
  - **Encrypt-then-MAC / AEAD**: Authenticate ciphertext, never MAC plaintext
    alone.
  - **TLS & certificate verification**: Never disable TLS verification
    (`verify=False`); verify CA trust, hostname/subject identity, expiry, and
    avoid long-lived self-signed or overly broad wildcard certificates in
    production.

## 4. AI-Era Supply Chain & Dependency Hygiene

- **Guard against slopsquatting (hallucinated packages)**: Agents frequently
  invent plausible package names that attackers register. Before adding any new
  dependency, verify the package exists, check publisher reputation and source
  repo, and pin exact versions with cryptographic hashes (`--require-hashes` /
  lockfiles).
- **Pin CI actions to full 40-char commit SHAs**: Never use mutable tags like
  `@v4` or `@main` in `.github/workflows/`; set minimal `permissions: contents: read`
  and `persist-credentials: false`.
- **No runtime network installs**: Install dependencies during build time only;
  forbid `curl | sh` or unpinned package downloads inside container entrypoints
  or agent runtimes.

## 5. Agent & LLM Untrusted-Boundary Code

When the AI-written application itself invokes LLMs, tools, or MCP servers:

- **Prefer deterministic mechanisms & constrained IR over LLM judgment**: Whenever
  behavior can be verified with schemas, parsers, type checks, linters, or policy
  rules, do not delegate enforcement to an LLM. Route every LLM output that triggers
  a side effect through a closed, validated intermediate representation (IR) before
  execution.
- **Explicit configuration precedence**: Resolve security and feature settings in a
  strict hierarchy (`Platform Admin Policy > Tenant/Org Policy > Secret Store >
  Deployment Env Vars > Code Defaults`) — never infer live security posture or
  entitlements from code defaults alone.
- **Treat all external data and LLM output as untrusted**: Never feed tool
  outputs, web pages, emails, or logs directly into SQL, shell, HTTP, or
  file-write sinks without deterministic schema validation and policy checks.
- **Harden untrusted-data framing**: Do not rely on naive string markers alone;
  defend against Unicode invisible characters (`Cf` / default-ignorable code
  points), NFKC folding tricks, and JSON key smuggling when framing external
  content.
- **Bind high-risk actions to canonical arguments**: Approval or authorization
  grants must bind `(action, target, canonical_args_hash)` so a modified
  parameter cannot replay an earlier approval.
- **Pin tool definitions & sandbox execution**: Verify MCP tool catalog digests
  (fail closed on rug-pull/schema drift) and run untrusted code/commands inside
  resource-bounded sandboxes without exposing host credentials.

## 6. Mandatory Security Verification (Red-before-Green)

Prose rules evaporate after context compaction. Every PR touching auth,
permissions, tenant isolation, file paths, outbound HTTP, cryptography,
deserialization, or agent tool boundaries **must** satisfy:

1. **At least one negative security test**: Prove that an invalid token,
   cross-tenant ID, `../` path, symlink escape, private-IP URL, tampered args,
   or missing secret is **explicitly rejected** (`401`/`403`/`ValueError`), not
   silently accepted or coerced.
2. **Deterministic static & secret scanning**: Run language security linters
   (e.g., Ruff `S` rules / Bandit / Semgrep / ESLint security) and secret
   scanning before merge — missing tools must exit non-zero (`NOT_RUN`), never
   green skip.
3. **Never feed live sensitive data to coding agents**: Use approved synthetic
   fixtures, data cards, or sealed execution sandboxes instead of raw
   production databases or secret files.

## 7. Engineering Carrier: Enforcing This Standard with `deps`

This standard defines **what** must hold; **`deps`** (under
[OpenAgenticSecurity](https://github.com/OpenAgenticSecurity))
serves as the local Rust **engineering carrier** that enforces key boundaries in
milliseconds inside the coding-agent loop:

| Security Need in `agentic-sdlc` | Enforced Deterministically by `deps` |
|---|---|
| Keep real datasets & PII out of coding-agent context | **`sealed-data seal`** + MCP `sealed_data_card` / `sealed_data_run` from the sibling project `sealed-data` (writes Claude deny rules & OS-sandbox `denyRead`; agents code against approved data cards and de-valued results) |
| Catch secret literals, Vault ref misuse & prompt-injection patterns | **`deps security-audit`** / **`deps security-filter`** (validates secret references without reading or returning secret values; deterministic injection filter) |
| Prevent unapproved cross-boundary imports & silent architecture drift | **`deps aac check`** / **`deps aac reconcile --strict`** (Tree-sitter AST conformance in milliseconds) |
| Verify API route/call, topic & SQL/ORM lineage against expectations | **`deps lineage`** / **`deps lineage-audit`** (exact evidence-bound `deps.semantic-lineage.v1` IR) |
| Produce replayable, non-self-attesting delivery receipts | **`deps agent-verify --receipt`** (explicit `PASS`/`FAIL`/`NOT_RUN`/`CONFLICT`, `does_not_prove[]`, SHA-256 `receipt_digest`) |

## Related Documents

- Actionable PR checklist: [checklists/secure-vibe-coding-review.md](../checklists/secure-vibe-coding-review.md)
- Non-authoritative agent skill: [skills/secure-vibe-coding/SKILL.md](../skills/secure-vibe-coding/SKILL.md)
- Testing & gate integrity: [testing-strategy.md](testing-strategy.md)
