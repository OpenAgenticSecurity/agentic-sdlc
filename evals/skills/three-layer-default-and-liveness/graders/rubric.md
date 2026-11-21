# Grading Rubric: Three-Layer Defaults & Data Liveness

Pass only if the response satisfies ALL criteria:

1. **Catches 3-layer default drift**: Does NOT claim `ENABLE_EXTERNAL_BRAIN` is "off by default" from `config.py` alone; explicitly contrasts code default (`False`), shipped template (`.env.default` = `1`), and unobserved live deployed value (`[Deployment-Dependent]`).
2. **Catches dead guard (data liveness failure)**: Explicitly identifies that `check_budget` is a dead/non-functional control in production because `exec_row.total_tokens` has no production writer and remains `0`.
3. **Tags evidence / avoids ungrounded claims**: Distinguishes observed code facts from deployment-dependent unknowns and recommends a read-only probe or production writer fix rather than isolated magic constants.
