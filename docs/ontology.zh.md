# Agentic SDLC 本体论：九大一等实体与五条公理

**状态**: foundational reference
**更新日期**: 2026-11-21
**English**: [ontology.md](ontology.md)

Coding Agent 反复翻车，很少是因为“没记住某条文档步骤”。回顾 **15,384 条真实
Claude Code 与 Codex 工程对话**以及累计 **2000+ 亿 Token** 的多仓实战，绝大多数事故都源于**本体混淆（Category Errors）**——持续把本质完全不同的工程对象混为一谈（把会话记忆当成代码现实、把单文件修改当成耦合变更完成、把一段总结当成证据、把代码默认值当成线上运行配置）。

本页用 **9 个一等实体**和 **5 条本体公理**，把 `OpenAgenticSecurity/agentic-sdlc`
中的全部标准、清单、Skills 与确定性脚本收拢为一张统一、跨语言的概念总图。

---

## 1. 九大一等实体（First-Class Entities）

| # | 本体实体 | 它的真实本质 | Agent 常把它混淆成什么 |
|---|---|---|---|
| 1 | **`Intent & Scope`（意图与边界）** | 经批准的目标、`in_scope`、`out_of_scope`、受保护主流程与停止条件 | 随口聊天 Prompt 或顺手扩大重构范围 |
| 2 | **`RealityAnchor`（世界事实源）** | 可核验现实：精确 40 位 Git SHA、真实 DB Schema、`STATUS.md`、只读运行态探针 | 模型先验、过时设计文档或会话上下文记忆 |
| 3 | **`Workspace & Revision`（工作空间与修订）** | 主 Checkout vs 隔离任务 Worktree、工作树脏字节 vs 已提交 `HEAD` 对象 | 单纯的分支名（`main` 或 `feat/...`） |
| 4 | **`ArtifactGraph`（耦合工件图）** | 源码通过显式边耦合单测、契约、三层配置、文档与 `STATUS.md` | 孤立的单文件 diff |
| 5 | **`Execution & Effect`（执行与副作用）** | 受策略/Grant 约束的副作用动作，具备 `RESULT_UNKNOWN`、TTL 与补偿路径 | 纯模型推理或乐观“发完即成功” |
| 6 | **`Evidence`（原始观测证据）** | 可复现一手观测：精确命令、退出码、原始输出、SHA-256 摘要、独立回读 | Agent 自我总结或裸布尔 `"done": true` |
| 7 | **`Gate & Verifier`（门禁与校验器）** | 独立校验机制：带固定版本、覆盖边界、合法非绿态与负向变异证明 | 候选产出方或可自证的 PR 检查 |
| 8 | **`Authority & Decision`（权威与裁决）** | 授权主体或受保护 GitHub Ruleset 推进 `Merge`、`Release` 或 `Waiver` | 模型置信度或本地测试绿灯 |
| 9 | **`Lesson & Rule`（演化规则）** | 经真实事故沉淀出的失败负向变异测试与确定性门禁 | 沉在聊天记录里的复盘或口头约定 |

---

## 2. 五条本体公理（Ontological Axioms）

### 公理 1 · 事实压倒记忆（`RealityAnchor > SessionMemory`）
当对话历史、旧文档或模型先验与 `RealityAnchor`（新鲜拉取的 `origin/<default>`、真实调用链与构造点、`STATUS.md` 或线上只读回读）冲突时，后者拥有绝对权威。

- **本仓落地**：`standards/ai-coding-context.zh.md`、`skills/multi-agent-git-flow`、
  `skills/audit-production-readiness`（7 条证据纪律与三层默认值核查）。

### 公理 2 · 耦合变更闭包（`ArtifactGraph`）
修改 `ArtifactGraph` 中的任意主节点（源码、API 路由、Schema、配置模板或门禁脚本），在其必填耦合边（单测/反向安全单测、消费方契约、三层配置说明、文档与 `STATUS.md`）全部同步或附带可审计豁免之前，任务在本体上只能处于 **`PARTIAL`**，**绝不允许跃迁到 `DONE`**。

- **本仓落地**：`scripts/check-change-sync.py`、`profiles/L1-team/agentic-sync.example.json`、
  `standards/testing-strategy/affected-closure-contract.zh.md`、`checklists/handoff.template.md`。

### 公理 3 · 状态不可有损折叠（Non-Collapsing State Machine）
`PASS`、`FAIL`、`NOT_RUN`、`UNKNOWN`、`RESULT_UNKNOWN`、`FLAKY`、`CONFLICT`、
`ERROR`、`NOT_APPLICABLE`、`NOT_EVALUATED` 与 `HITL` 是互斥的一等状态。将任何非绿状态静默压缩为布尔 `true` 或逼真假默认值（`?? 0`、`|| []`、`0 tests collected` 退出码 0）均属本体违规。

- **本仓落地**：`skills/done-claim-verify`、`checklists/fake-done-dereference.zh.md`、
  `scripts/audit-repo.py`（`OAS-JS-02`、`OAS-SVC-01`、显式 `NOT_RUN`）、
  `standards/reliable-and-performant-coding.zh.md`。

### 公理 4 · 主体与裁判分离（Non-Self-Attestation）
产出 `Patch` 的执行主体永远不具备签发最终 `Decision` 或认证自身 `Gate` 变更的权威。任何触及工作流、`action.yml`、Schema、校验器、`CODEOWNERS`、测试或 Agent 指令的 PR，都必须经外部受保护边界独立裁决。

- **本仓落地**：`profiles/L2-governed/github-ruleset.import.json`、
  `scripts/observe-github-ruleset.py`、`scripts/audit-repo.py --github`、
  `profiles/L2-governed/mechanism-review-checklist.md`。

### 公理 5 · 不对称知识演化（Asymmetric Knowledge Evolution）
每次生产事故或审计发现都必须升级为可复现的负向变异测试或确定性门禁。自动学习或规则沉淀**只能收紧约束、补充上下文或暴露盲区**，绝不允许自动放宽权限、取消审批、降级门禁严重度或写入永久白名单。

- **本仓落地**：`checklists/production-readiness-audit.zh.md`、`evals/`、
  `scripts/run-evals.py`、`CONTRIBUTING.md`。

---

## 3. 诚实边界（`does_not_prove`）

本体论让隐蔽边界显性化，但术语本身不能替代工程执行。如果不配合确定性检查（`audit-repo.py`、`check-change-sync.py`、Fail-Closed CI、受保护 GitHub Ruleset 与真实集成测试），上述五条公理仍停留在纸面。
