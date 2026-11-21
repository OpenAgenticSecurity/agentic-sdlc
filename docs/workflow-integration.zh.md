# Agentic SDLC 如何嵌入现代 AI 研发工作流

**状态**: adoption architecture guide
**更新日期**: 2026-11-21
**English**: [workflow-integration.md](workflow-integration.md)

`OpenAgenticSecurity/agentic-sdlc` **不要求**你替换 Claude Code、Cursor、Codex、`superpowers`、现有 Linter 或 GitHub Actions。它套在现有编码内环之外，充当**外环验证与安全边界**。

---

## 1. AI 研发 4 层工具栈与痛点映射

| 工具栈层级 | 当下主流工具 | 缺少外环护栏时的典型翻车 | `agentic-sdlc` 提供的解法 |
|---|---|---|---|
| **1. 规格与上下文** | GitHub Issues、Linear、Plan Mode、`superpowers`、Spec-Kit | 跨会话漂移；基于已删除模块瞎写；大改动跳过设计直接铺代码 | 统一根 `AGENTS.md`（含非平凡任务阈值与栈槽位）+ 极薄 `@AGENTS.md` `CLAUDE.md` + `STATUS.md` + `handoff.template.md` |
| **2. 编码执行内环** | Claude Code、Cursor、Codex、Windsurf、MCP | 多 Agent 直写污染 `main`；顺手引入 `except: pass`、兜底密钥、SSRF 或幻觉依赖包 | `multi-agent-git-flow` + `secure-vibe-coding` Skills；本地确定性 Git 钩子（`workspace-git.py`）；可选 L2 Rust 本地钩子 `deps` 与 `sealed-data` |
| **3. 本地验证与自检** | `ruff`、`eslint`、`tsc`、`pytest`、`vitest`、`go test`、`cargo test`、Playwright | 只测 P50；`0 tests collected` 或 `--passWithNoTests` 混绿灯；单测漏掉 93% 前端 Bug 与 95% 后端性能坑 | `done-claim-verify` + `audit-pr-diff` Skills；零依赖多语言 `audit-repo.py`；开箱即用的 Playwright 与后端契约门禁骨架（`examples/`） |
| **4. PR、CI 与生产准入** | GitHub PR、GitHub Actions、AI Review Bot、GitHub Rulesets | PR 同时改代码和门禁自证绿灯；Ruleset 允许批准后继续 push 或 `integration_id: null` 伪造状态检查；Demo 级系统冒充生产级上线 | Fail-Closed 多语言 CI 模板（Python/TS/Rust/Go/Java）、可复用 `action.yml`、`CODEOWNERS`、`github-ruleset.import.json`、`observe-github-ruleset.py` 与五维 `audit-production-readiness` Skill |

---

## 2. AI 编码真实的一天：5 个无痛嵌入点

```text
[1. 接单开工]       Issue / Linear -> 基于 origin/main 开隔离 Worktree
      ├─ 嵌入点 ①：AGENTS.md + STATUS.md + multi-agent-git-flow Skill
      │            + workspace-git.py pre-commit/pre-push 钩子（物理拦住直提交 main）
      ▼
[2. 规划与写码]     Claude Code / Cursor / Codex（可搭配 superpowers）
      ├─ 嵌入点 ②：非平凡任务阈值（>3 文件 / >50 行 -> 先 Plan + 先失败测试）
      │            + secure-vibe-coding Skill（可选 L2：叠加 deps PreToolUse 钩子）
      ▼
[3. 喊“完成”前]     Agent 准备汇报“已修好 / 测试通过”
      ├─ 嵌入点 ③：done-claim-verify + audit-pr-diff Skills
      │            -> 4 个假完成断点、带 does_not_prove[] 的 DoneClaim、file:line 排雷
      ▼
[4. 开 PR 与 CI]    GitHub PR + Actions
      ├─ 嵌入点 ④：Fail-Closed CI 模板 + 4 行可复用 action.yml（运行 audit-repo.py）
      │            -> 40 位 Action SHA 锁定、多语言静态陷阱、PR Review 引用 OAS-* 编号
      ▼
[5. 合并与上线]     GitHub 合并边界 -> 上线前生产就绪判定
      └─ 嵌入点 ⑤：github-ruleset.import.json + CODEOWNERS + observe-github-ruleset.py
                   + audit-production-readiness Skill（上线前五维 H1/H2 生产审计）
```

---

## 3. 渐进式落地阶梯（切忌第一天全量照搬）

| 阶段 | 耗时 | 实际动作 |
|---|---|---|
| **0. 只读体检** | 10 秒 | 运行 `python3 scripts/audit-repo.py /path/to/your-repo --github`（零 `pip install`，绝不写盘）。 |
| **1. 个人日常** | 1 分钟 | 在本机 Claude Code / Cursor / Codex 全局装好 6 个跨语言 Skills。 |
| **2. 仓库基线（`L0`）** | 5 分钟 | 运行 `scripts/bootstrap.sh --profile L0 --target <repo>`（落地统一 `AGENTS.md`、极薄 `@AGENTS.md` `CLAUDE.md`、`STATUS.md`、`.gitignore` 与 Fail-Closed `make agent-check`）。 |
| **3. 团队 CI（`L1`）** | 20 分钟 | 使用 `--profile L1 --ci <python\|node-ts\|rust\|go\|java>`，在 CI 中接入 4 行 `action.yml` 体检，开启 `workspace-git.py guardrails --apply`。 |
| **4. 生产治理（`L2`）** | 1 小时 | 导入 `github-ruleset.import.json`，配置真实 `CODEOWNERS`，用 `observe-github-ruleset.py` 验真，发版前跑 `audit-production-readiness`，按需叠加 `deps` / `sealed-data`。 |

---

## 4. 0 / 30 / 60 / 90 天存量团队迁移与权威框架映射

在存量研发组织推广 `agentic-sdlc` 时，只基于核验后的退出证据逐步扩大自治范围；不达标时保持或收紧权限，绝不放宽门禁：

| 里程碑 | 扩大自治前必须满足的退出证据 |
|---|---|
| **Day 0** | 盘点现有 Agent、工具与数据密级；记录当前缺陷/返工/Review 耗时基线；选定一个可回滚、低敏感试点并明确责任人 |
| **Day 30** | 落地 `L0`/`L1` 基线；植入违规能打红 CI；`check-change-sync.py` 与反向安全单测跑通；无未知权限路径 |
| **Day 60** | 启用 `L2` GitHub Ruleset 与 `CODEOWNERS`；独立机制审查落地；重放/吊销/隔离测试通过；量化 Review 耗时与 Reopen 率 |
| **Day 90** | 行为变更清单与消费端溯源验签落地；完成五维 `audit-production-readiness` 审计；高影响动作保持人类审批门 |

### 与主流安全工程框架对照（参考映射）

| 行业框架 | 本仓对应的核心控制面 |
|---|---|
| **NIST SSDF / SP 800-218A** | 精确修订 CI、40 位 Action SHA 锁定、哈希锁定依赖、反向安全单测、SLSA 构建与消费端验签（`standards/versioning-and-releases.zh.md`） |
| **OWASP SAMM & Agentic Top 10** | Fail-Closed 鉴权/租户/Sink 不变量、原子单次参数绑定审批、防只读外泄、防幻觉包投毒（`standards/secure-vibe-coding.zh.md`） |
| **NCSC / CISA Agentic AI 指南** | 分级自治边界、主体与裁判不可自证分离、带外急停、行为组件变更准入（`docs/ontology.zh.md`、`profiles/L2-governed/`） |
