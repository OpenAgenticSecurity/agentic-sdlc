# 核心标准（Standards）

**状态**: accepted baseline
**更新日期**: 2026-11-20
**English**: [README.md](README.md)

本目录拥有 9 篇核心 Agentic SDLC 工程标准与 2 套轻量、可直接在任意仓库运行的闭合 JSON Schema 契约。

## Agentic SDLC 核心标准

| 文件 | 用途 |
|------|------|
| [sdlc.zh.md](sdlc.zh.md) | 生命周期、单调交付门（`A0`–`A5`）与 Definition of Done |
| [secure-vibe-coding.zh.md](secure-vibe-coding.zh.md) | Secure Vibe Coding 安全编码不变量（鉴权/防 Fail-Open、注入/SSRF/路径/ReDoS、密钥与密码学运营、供应链、Agent 边界、反向安全单测与 `deps` 工程承载） |
| [reliable-and-performant-coding.zh.md](reliable-and-performant-coding.zh.md) | 写码前可靠性、稳定性与高性能不变量（资源生命周期、`RESULT_UNKNOWN` 与爆炸半径、异步/连接池/超时总账、Schema 单一权威、模型升级回归、隔离式多 Agent 与 Tool Harness） |
| [ai-coding-context.zh.md](ai-coding-context.zh.md) | `AGENTS.md`、`CLAUDE.md`、`VIBE_CODING_CONTEXT.md` 与 `STATUS.md` 事实源规范 |
| [vibe-coding-collaboration.zh.md](vibe-coding-collaboration.zh.md) | 人类与 Coding Agent 协作、跨层一致性与共享层修复规则 |
| [multi-ai-git-workflow.zh.md](multi-ai-git-workflow.zh.md) | 多人多 AI Git/Worktree 隔离、Managed Issue Claim 与主干分叉处理 |
| [agent-issue-pr-loop.zh.md](agent-issue-pr-loop.zh.md) | 从发现问题、范围冻结、PR 关联到 Issue 关闭的审计闭环 |
| [testing-strategy.zh.md](testing-strategy.zh.md) | 测试分层、受影响闭包选择、门禁完整性与前后端测试证据 |
| [versioning-and-releases.zh.md](versioning-and-releases.zh.md) | SemVer 决策流、四类版本本体隔离（发版/摘要/Schema/开关）、防漂移一致性检查与 SLSA 发布门禁 |

## 轻量可执行保证契约（闭合 Schema 与反向 Mutation Fixtures）

| 控制线 | 规范文档 | 确定性校验器 |
|---|---|---|
| **Affected-Test Closure** | [testing-strategy/affected-closure-contract.zh.md](testing-strategy/affected-closure-contract.zh.md) | `scripts/check-affected-closure.py` |
| **External Enforcement Evidence** | [testing-strategy/enforcement-evidence-contract.zh.md](testing-strategy/enforcement-evidence-contract.zh.md) | `scripts/check-enforcement-evidence.py` + `scripts/observe-github-ruleset.py` |

> **需要完整的 L2 协议级 UI Assurance（8 个 Schema）与 Code Health（10 个 Schema）套件？**
> 这两套面向自建 Guardian 与多仓退役账本的重型契约已独立拆至同级仓
> `OpenAgenticSecurity/assurance-contracts`，保持 `agentic-sdlc` 极度精简、开箱即用。

## 规则

采用方仓库可以增加更严格的本地规则，但不应削弱上述核心安全、验证与不可自证不变量。
