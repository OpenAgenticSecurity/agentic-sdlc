# 分级落地模板包（Progressive Adoption Profiles）

**更新日期**: 2026-11-20
**English**: [README.md](README.md)

不要把企业级重门禁硬套在周末原型上，也不要在多 Agent 生产仓库里只靠口头提示词裸奔。每个 Profile 目录均**自洽完整、可直接手工拷贝**，也可通过零依赖脚本 `scripts/bootstrap.sh` 一键落盘（详见 [`BOOTSTRAP.zh.md`](../BOOTSTRAP.zh.md)）。

| 档位 | 适用对象 | 耗时 | 落地内容 |
|---|---|---|---|
| **[`L0-solo`](L0-solo/README.md)** | 个人开发者 / 小型仓库 | ~5 分钟 | 零工具依赖基线：`AGENTS.md`、`CLAUDE.md`、`STATUS.md`、`VIBE_CODING_CONTEXT.md`、含安全检查的 PR 模板、worktree `.gitignore`、Fail-Closed 的 `make agent-check` 入口 |
| **[`L1-team`](L1-team/README.md)** | 多人 / 多 Agent 协作团队 | ~20 分钟 | `L0` + 通用 `.github/ISSUE_TEMPLATE/`、精确 head 候选 CI（支持 `--ci python\|node-ts\|rust\|go\|java`）、`Makefile` `agent-check`、Managed Issue Claim、本地 Git `pre-commit`/`pre-push` 护栏 |
| **[`L2-governed`](L2-governed/README.md)** | 高安全保证 / 受治理工程 | ~1 小时 | `L1` + 门禁表面 `CODEOWNERS`、GitHub Ruleset 策略与只读体检（`observe-github-ruleset.py`）、独立机制审查清单、可选的 **`deps`** 本地工程承载（`aac` / `agent-hook` / `security-audit` / `agent-verify`）与可选 L2 闭合契约 |
