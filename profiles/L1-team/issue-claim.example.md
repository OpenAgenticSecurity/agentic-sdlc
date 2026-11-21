<!-- agent-claim:org/service#42:auth-guard-20261120 -->

### Agent Claim

- Status: `running`
- Automation identity: `Claude Code`
- GitHub actor: `alice`
- Agent: `claude-code`
- Session: `claude-20261120-a`
- Task: `auth-guard-20261120`
- Repo: `service`
- Branch: `fix/auth-guard`
- Worktree: `.claude/worktrees/auth-guard`
- Claim issue: `org/service#42`
- PR: `none`
- Lease expires: `2026-11-20T18:00:00Z`
- Updated: `2026-11-20T16:00:00Z`

Owned paths:
- `src/auth/guard.py`
- `tests/test_auth_guard.py`

Out of scope:
- `frontend/`

Dependencies:
- `none`

Current summary:
Implementing fail-closed token audience check with negative mutation tests.

Next action:
Run make agent-check and open PR linked to org/service#42.
