# Agent Skills（6 个独立自包含的非权威投影）

**更新日期**: 2026-11-21
**English**: [README.md](README.md)
**绑定权威源**：[`standards/`](../standards/README.zh.md) 与 [`checklists/`](../checklists/README.zh.md)（`v0.3.0`）

> **信任边界声明**：本目录下 6 个 `SKILL.md` 全部**独立自包含**（用 `npx skills add` 装到任意外部仓库零缺失文件即可直接工作），且均为**显式非权威投影**。Skill 让 Coding Agent 承担日常执行与检查工作，真正的信任边界由 Prompt 窗口之外的机制守住：本地 Git Hooks（`scripts/workspace-git.py`）、**`deps`** 生命周期钩子，以及受保护 GitHub Ruleset（`scripts/observe-github-ruleset.py`）。

## 安装到你的 Coding Agent

```bash
# 通用 Skills CLI（支持 Claude Code / Cursor / Codex 等）：
npx skills add OpenAgenticSecurity/agentic-sdlc

# 或通过零依赖脚本拷贝到目标仓库：
bash /path/to/agentic-sdlc/scripts/bootstrap.sh --profile L0 --target /path/to/your-repo --with-skills
```

仓库根目录同时提供 `.claude-plugin/`、`.cursor-plugin/` 与 `.codex-plugin/` 原生插件清单。

> **范围与语言无关性声明**：这 6 个 Skills 沉淀的是**脱离具体编程语言的安全红线、验收核查、PR 排雷、五维生产就绪审计与多 Agent Git 工程不变量**，**不包含**具体编程语言的代码风格或框架开发规范（格式化、命名、目录约定与语言 Lint 属于各业务仓自己的 `AGENTS.md` 与 Linter）。Skill 中偶尔出现的语言写法仅作为通用失效模式的举例。

## 包含的 6 个零重叠 Skills

| Skill | 适用场景 / 守住的红线 | 权威依据 |
|---|---|---|
| [`bootstrap-agentic-sdlc`](bootstrap-agentic-sdlc/SKILL.md) | 按目标仓库真实技术栈安全落地 `L0`/`L1`/`L2`（含可选 `deps`）与 4 项验收 | `BOOTSTRAP.zh.md`、`profiles/` |
| [`secure-vibe-coding`](secure-vibe-coding/SKILL.md) | 默认安全编码：鉴权/租户防 Fail-Open、安全 Sink、密钥与密码学、防幻觉包、强制反向安全单测 | `standards/secure-vibe-coding.zh.md`、`checklists/secure-vibe-coding-review.zh.md` |
| [`audit-pr-diff`](audit-pr-diff/SKILL.md) | 基于 `file:line` 按安全、前端 454 Bug、后端 8 类性能、七宗罪与机制审查清单审 diff/PR | `checklists/` |
| [`audit-production-readiness`](audit-production-readiness/SKILL.md) | 整仓五维生产就绪实现审计（架构/设计/功能/性能/安全）：7 条证据纪律、三层默认值、数据活性与 H1/H2 生产 vs Demo 裁决 | `checklists/production-readiness-audit.zh.md` |
| [`done-claim-verify`](done-claim-verify/SKILL.md) | Fail-Closed 验收：五层事实链、4 个假完成断点、合法非绿状态、反向 Mutation、不可自证与 `DoneClaim` | `checklists/fake-done-dereference.zh.md`、`standards/testing-strategy.zh.md` |
| [`multi-agent-git-flow`](multi-agent-git-flow/SKILL.md) | `STATUS.md` 真源、远端刷新、Worktree 隔离、Managed Issue Claim、跨会话交接、禁 Stacked PR、共享依赖与 5 项安全清理 | `standards/multi-ai-git-workflow.zh.md`、`standards/agent-issue-pr-loop.zh.md`、`standards/ai-coding-context.zh.md` |
