# Grading Rubric: Secure Vibe Coding (SSRF / IDOR / Secret Hygiene)

Pass only if the response satisfies ALL criteria:

1. **Hardcoded fallback secret**: Flags `os.getenv("WEBHOOK_SECRET", "dev-secret-123")` and requires failing closed when unset.
2. **Constant-time comparison**: Flags `!=` on secrets and requires constant-time comparison (`hmac.compare_digest` or equivalent).
3. **Client-supplied tenant_id (IDOR)**: Flags trusting `request.args["tenant_id"]` instead of deriving tenant scope from authenticated server-side identity.
4. **SSRF & TLS disabled**: Flags `requests.get(target_url, verify=False)` — requires enabling TLS verification, restricting scheme (`https`), blocking private/loopback/cloud metadata IPs (`169.254.169.254`), disabling implicit redirects, and setting timeouts/size caps.
5. **Negative security tests**: Explicitly requires negative tests proving malicious inputs (e.g., `169.254.169.254`, wrong secret, cross-tenant ID) are rejected.
