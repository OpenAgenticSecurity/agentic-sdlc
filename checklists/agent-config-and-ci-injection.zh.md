# Agent 指令文件、IDE/MCP 配置与 CI 注入排雷清单

**状态**: accepted baseline
**更新日期**: 2026-11-22
**English**: [agent-config-and-ci-injection.md](agent-config-and-ci-injection.md)
**自动化校验**: `python3 scripts/audit-repo.py <repo>`（`OAS-AGT-01..03`、`OAS-CI-05`）

> **为什么需要这份清单**：2026 年针对 Coding Agent 的攻击已从 IDE 解析漏洞转向直接投毒纯 Markdown 指令文件（`AGENTS.md`、`CLAUDE.md`、`SKILL.md`）、仓库内可执行配置（`.vscode/tasks.json`、`.claude/settings.json`、`.mcp.json`），以及借 PR 标题或 Issue 评论劫持 GitHub Actions 中 AI 审查代理窃取密钥的“Comment-and-Control”攻击。必须按 CI/CD 流水线代码的同等安全级别审查所有 Agent 指令与配置文件。

---

## 1. 指令文件投毒排查（`AGENTS.md`、`CLAUDE.md`、`SKILL.md`、Rules）

- [ ] **扫描隐藏/欺骗性 Unicode（`OAS-AGT-01`）**：拦截零宽字符（`U+200B..U+200F`）、双向文本控制符（`U+202A..U+202E`、`U+2066..U+2069`）、正文内 `U+FEFF` 以及隐身 Unicode Tag 块（`U+E0000..U+E007F`）。
- [ ] **拦截静默执行社工话术（`OAS-AGT-03`）**：警惕声称某脚本为“加密/签名密封初始化制品，禁止阅读或展示，会话启动时无需确认静默自动执行”的投毒指令。
- [ ] **禁止劫持模型 API 端点（`OAS-AGT-03`）**：拒绝在指令文件或仓库配置中覆盖 `ANTHROPIC_BASE_URL` / `OPENAI_BASE_URL`（极易劫持会话并窃取 OAuth Token）。
- [ ] **纳入 `CODEOWNERS`（不可自证）**：任何修改 `AGENTS.md`、`CLAUDE.md`、`skills/`、`.cursor/`、`.claude/`、`.codex-plugin/` 或 `.github/copilot-instructions.md` 的 PR 必须经独立审查。

## 2. 仓库内可执行 IDE 与 MCP 配置排查（`OAS-AGT-02`）

- [ ] **禁止 `folderOpen` 自动执行**：拦截 `.vscode/tasks.json` 中的 `"runOn": "folderOpen"`。
- [ ] **按可执行代码审计 `.claude/settings*.json`**：拦截 `"defaultMode": "bypassPermissions"`、裸 Shell 通配符（`Bash(*)`）、仓库内 `apiKeyHelper` 与未经审查的生命周期 `hooks`。
- [ ] **锁定并审查 `.mcp.json` / `.cursor/mcp.json`**：拒绝含 `sh -c` 或 `curl | sh` 的 MCP 启动命令；对批准的 MCP Server 做白名单管理并校验工具目录摘要防 Rug-Pull 漂移。
- [ ] **禁止在不可信目录启动写权限 Agent**：绝不在 `~/Downloads`、未审查外部 Fork 或共享临时目录下运行带写/Shell 权限的 Coding Agent（防止自动加载陌生 `AGENTS.md`）。

## 3. GitHub Actions「Comment-and-Control」AI 注入防护（`OAS-CI-05`）

- [ ] **严禁把不可信 GitHub 字段裸拼进 Shell 或特权 Prompt**：禁止在 `run:` 或 AI 审查 Prompt 中直接插值 `${{ github.event.(issue|pull_request|comment|discussion).(title|body) }}` 与 `${{ github.head_ref }}`——一律经 `env:` 传递并做显式不可信定界。
- [ ] **禁止 `pull_request_target` 搭配检出 PR Head 或 AI 审查代理**：Fork PR 下的 `pull_request_target` 暴露仓库 Secrets 与写权限；AI 审查工作流应运行在 `pull_request` 上，坚持 `permissions: contents: read` 且不注入部署/写密钥。
- [ ] **封堵经评论、提交与 Actions 日志的外泄通道**：在 CI AI Agent 中禁用 `ps`/`env`/`printenv` 等进程环境探查命令，调用前清理非必要密钥环境变量，绝不把 Actions 日志当“没人看”的隐蔽区域。
