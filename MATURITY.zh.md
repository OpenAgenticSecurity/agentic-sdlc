# OpenAgenticSecurity 成熟度与信任边界说明（Maturity & Trust Boundaries）

**状态**: canonical reference
**更新日期**: 2026-11-21
**English**: [MATURITY.md](MATURITY.md)

OpenAgenticSecurity 遵循一条底线原则：**证据之外的结论不得宣称**。本文如实说明 `agentic-sdlc` 每一类资产当前的成熟度、已验证边界与明确的非目标。

## 成熟度等级定义

| 等级 | 名称 | 含义 |
|---|---|---|
| **L0** | Local Guardrails | 本地工作流、Git/Worktree 隔离、上下文事实源（`STATUS.md`）、Secure Vibe Coding 安全红线、实证排雷清单与最小合规检查 |
| **L1** | Candidate / Advisory Verification | 闭合 JSON Schema、确定性校验器、反向 Mutation Fixture 与精确 head 候选 CI（**绝不自证**） |
| **L2** | Trusted Enforcement Pattern | 仓库外部受保护运行器、不可变分支/Ruleset 保护、双人机制审查，以及 **`deps`** 本地工程承载（生命周期钩子、AaC 棘轮、交付回执）与负责数据集密封的 `sealed-data` |

## 各控制面真实成熟度矩阵

| 能力模块 | 位置 | 当前等级 | 已通过真实自动化证明 | 尚未证明 / 需要采用方自建 |
|---|---|---|---|---|
| **Bootstrap、自检、耦合同步、Action、共享依赖与 Git 护栏** | `BOOTSTRAP.zh.md`, `action.yml`, `scripts/bootstrap.sh`, `scripts/audit-repo.py`, `scripts/check-change-sync.py`, `scripts/run-evals.py`, `scripts/workspace-git.py`, `scripts/agent-claim.py`, `scripts/link-shared-node-deps.mjs` | **L0–L1** | 软链防逃逸初始化（带 fail-closed `make agent-check`）、5 语言 CI 模板（Python/TS/Rust/Go/Java）、零依赖信任边界自检（`audit-repo.py` 覆盖指令文件隐藏 Unicode/端点劫持、IDE/MCP 配置、CI Comment-and-Control 注入、专用 SAST 接入检查与 Day-0 冒烟 + `action.yml` + 19 用例评测）、耦合变更同步门禁（`check-change-sync.py`）、可卸载本地 Git 护栏、只读 lockfile 共享 Node 仓 | 深度跨文件数据流 SAST（交由 Ruff S / Semgrep / CodeQL / gitleaks / `deps`）、远端分支保护、跨主机分布式锁 |
| **实证、安全、运维、IaC 与生产就绪清单** | `checklists/`, `standards/secure-vibe-coding.*`, `examples/` | **L0–L1 基线（+ `deps` 承载）** | 10 套清单（含指令/CI 注入、破坏性 IaC/DB 防呆与反 Reward Hacking）+ `DoneClaim`/`Handoff` 模板 + 可运行 Playwright 与后端契约门禁示例（`examples/`） | 文字规则会随上下文压缩衰减——同类缺陷应下沉为 Lint/单测门禁与 `deps` |
| **Affected-Test Closure 契约** | `standards/testing-strategy/affected-closure-contract.*`, `scripts/check-affected-closure.py` | **L1 Candidate** | 闭合 Schema、确定性排序、fail-closed 边界、`docs_only` 防扩张、接入方 `--report`/`--catalog` CLI 与正反向 Mutation 校验 | 业务仓自身的真实语言导入图与真实测试入口接线 |
| **Enforcement Evidence 与 Ruleset 观察器** | `standards/testing-strategy/enforcement-evidence*`, `scripts/check-enforcement-evidence.py`, `scripts/observe-github-ruleset.py`, `profiles/L2-governed/github-ruleset.import.json` | **L1 Candidate（面向 L2 审计）** | 离线/在线 GitHub Ruleset API 归一化与 SHA-256 绑定、状态检查来源（`integration_id`）与 `pull_request` 绕过白名单校验、可直接导入 GitHub 的 Ruleset JSON、反向 Mutation 套件 | 持续定时受保护采集、自动修复 Ruleset、替代独立机制审查 |
| **AI 工具投影（Skills / Plugins / Evals）** | `skills/`, `evals/`, `llms.txt`, `.claude-plugin/`, `.cursor-plugin/`, `.codex-plugin/` | **Non-Authoritative Projection** | 6 个零重叠独立自包含跨语言 Skills + Skill 评测集 + `llms.txt` 路由表 + 原生多工具插件清单 | **永不具备审批、豁免、降级风险或签发可信凭证的权威** |

> 面向自建 Guardian 与多仓退役账本的企业级 L2 协议套件（**UI Assurance** 8 Schema + **Code Health** 10 Schema）位于同级仓 `OpenAgenticSecurity/assurance-contracts`。

## 不可自证边界（Non-Self-Attestation）

修改 `.github/**`、`action.yml`、`Makefile`、`requirements-test*`、`pyproject.toml`、`scripts/**`、`tests/**`、`standards/**/schema/**`、`skills/**`、`.*-plugin/**`、`llms.txt`、`AGENTS.md` 或 `CLAUDE.md` 时，PR 自身的 CI 绿灯**绝不能自证**，必须在受保护分支策略下由独立机制审查人复核。
