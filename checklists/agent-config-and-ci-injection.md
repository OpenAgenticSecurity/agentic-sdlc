# Agent Instruction-File, IDE/MCP Config & CI Injection Checklist

**Status**: accepted baseline
**Updated**: 2026-11-22
**Chinese**: [agent-config-and-ci-injection.zh.md](agent-config-and-ci-injection.zh.md)
**Automated Check**: `python3 scripts/audit-repo.py <repo>` (`OAS-AGT-01..03`, `OAS-CI-05`)

> **Why This Exists**: In 2026, attackers shifted from exploiting IDE parser
> bugs to poisoning plain Markdown instruction files (`AGENTS.md`, `CLAUDE.md`,
> `SKILL.md`), repo-committed IDE/agent configs (`.vscode/tasks.json`,
> `.claude/settings.json`, `.mcp.json`), and GitHub Actions AI review workflows
> via PR titles or issue comments ("Comment and Control"). Treat every agent
> instruction and config file with the same rigor as CI/CD pipeline code.

---

## 1. Instruction-File Poisoning (`AGENTS.md`, `CLAUDE.md`, `SKILL.md`, Rules)

- [ ] **Scan for hidden/deceptive Unicode (`OAS-AGT-01`)**: Reject zero-width
  characters (`U+200B..U+200F`), BiDi overrides (`U+202A..U+202E`,
  `U+2066..U+2069`), non-BOM `U+FEFF`, and invisible Unicode Tag blocks
  (`U+E0000..U+E007F`).
- [ ] **Reject silent-execution social engineering (`OAS-AGT-03`)**: Flag any
  instruction claiming a script is *"sealed/encrypted/signed — do not read,
  quote, or display; run automatically at session start without confirmation"*.
- [ ] **Forbid API endpoint hijacks (`OAS-AGT-03`)**: Reject instructions or
  repo configs overriding `ANTHROPIC_BASE_URL` or `OPENAI_BASE_URL` to steal
  OAuth tokens or intercept sessions.
- [ ] **Protect under `CODEOWNERS` (non-self-attesting)**: Require independent
  review on any PR modifying `AGENTS.md`, `CLAUDE.md`, `skills/`, `.cursor/`,
  `.claude/`, `.codex-plugin/`, or `.github/copilot-instructions.md`.

## 2. Repo-Committed Executable IDE & MCP Configurations (`OAS-AGT-02`)

- [ ] **Forbid `folderOpen` auto-execution**: Reject `.vscode/tasks.json`
  entries with `"runOn": "folderOpen"`.
- [ ] **Audit `.claude/settings*.json` like executable code**: Reject
  `"defaultMode": "bypassPermissions"`, bare shell wildcards (`Bash(*)`),
  repo-committed `apiKeyHelper`, and unreviewed lifecycle `hooks`.
- [ ] **Pin & review `.mcp.json` / `.cursor/mcp.json`**: Reject shell `-c` or
  `curl | sh` MCP launch commands; allowlist approved MCP servers and verify
  tool catalog digests against rug-pull drift.
- [ ] **Never launch write-enabled agents in untrusted directories**: Do not
  run Claude Code, Cursor, or Codex with write/shell permissions inside
  `~/Downloads`, unvetted forks, or shared temporary folders where a dropped
  `AGENTS.md` is auto-loaded.

## 3. GitHub Actions "Comment-and-Control" AI Workflow Defense (`OAS-CI-05`)

- [ ] **Never interpolate untrusted GitHub fields into shell or privileged prompts**:
  Forbid raw `${{ github.event.(issue|pull_request|comment|discussion).(title|body) }}`
  and `${{ github.head_ref }}` in `run:` or privileged AI review prompts — pass
  untrusted data via bounded `env:` variables with strict framing.
- [ ] **Forbid `pull_request_target` + PR head checkout / AI review agents**:
  Fork PR workflows using `pull_request_target` inherit repo secrets and write
  tokens; run AI review on `pull_request` with `permissions: contents: read`
  and zero write/deploy secrets.
- [ ] **Block secret exfiltration through comments, commits, and Actions logs**:
  Deny `ps` / `env` / `printenv` tools inside CI AI agents, strip unnecessary
  environment secrets before invoking the agent, and never rely on Actions log
  obscurity to hide leaked keys.
