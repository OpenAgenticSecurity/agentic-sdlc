# Agentic SDLC 标准

**状态**: accepted baseline
**更新日期**: 2026-11-23
**English**: [sdlc.md](sdlc.md)

传统 SDLC 默认代码由稀缺、缓慢、可追责且受角色分工天然隔离的人类编写。当 Coding Agent 参与写代码后，语法生成成本趋近于零，但**跨会话漂移、欺骗门禁（Reward Hacking）与跨阶段副作用**的速度同步放大了一个数量级。本标准定义面向单仓与多仓工程的**双环 Agentic SDLC**。

---

## 1. 双环 Agentic SDLC 模型

Agent 时代的交付不再是匀速线性瀑布，而是由**慢速确定性外环**约束**高速概率性内环**的双环咬合系统：

```text
+-----------------------------------------------------------------------------+
| 外环 · 确定性治理与权威裁决（人类 Owner + 外部受保护系统）                   |
|                                                                             |
|  [1. 冻结意图、范围、现实锚点（RealityAnchor）与风险底线]                   |
|         |                                                                   |
|         v                                                                   |
|  +-----------------------------------------------------------------------+  |
|  | 内环 · 高速概率性执行（Coding Agent + 隔离沙箱）                       |  |
|  |   独立 Worktree -> 计划 -> 测试先行修改 -> 耦合工件同步                |  |
|  |   -> 产出不可信候选补丁（Patch）+ Candidate 证据 + DoneClaim           |  |
|  +-----------------------------------+-----------------------------------+  |
|                                      |（仅为候选草稿，永不可自证）           |
|                                      v                                      |
|  [2. 外部独立裁判]  受保护 CI · PR-Diff 裁判脚本 · GitHub Ruleset           |
|         |                                                                   |
|         v                                                                   |
|  [3. 不可变发布与运行回读]  制品 Digest + SLSA 双向验签 + 行为变更清单       |
|         |                                                                   |
|         v                                                                   |
|  [4. 不对称反馈闭环]  逃逸缺陷 / 险情 -> 新增必红负向测试与确定性门禁        |
+-----------------------------------------------------------------------------+
```

工程师角色从**逐行敲代码的操作员（Operator）**升级为**定意图、划边界、握裁判权并把事故结晶为门禁的治理者（Governor & Architect）**。

---

## 2. 传统软件工程五层在 Agent 时代的质变

| 工程层级 | 传统 SDLC 隐含假设 | Agent 时代典型失控 | Agentic SDLC 升维形态 |
|---|---|---|---|
| **1. 工作环境**（Repo / IDE / CI） | 单人可信主目录；本机放 `.env`；CI 默认可信 | 多 Agent 写脏 `main`；`AGENTS.md`/`.vscode/tasks.json` 投毒；CI 评论注入窃密；`.env` 误连生产删库 | 一任务一 Worktree、只读共享依赖仓、开发环境物理零生产凭据、指令与 IDE 配置扫描（`OAS-AGT-*`）、PR CI 显式定性为 **candidate** |
| **2. 工作上下文**（代码 / 文档 / Issue） | 人脑能自动过滤过时文档与旧架构图 | 上下文压缩蒸发文字规则；旧文档诱导编造已删模块；改代码漏改测试与文档 | `STATUS.md` 唯一代码真源、极薄统一 `AGENTS.md`、确定性投影驱动文档更新、`ArtifactGraph` 耦合同步门禁（`check-change-sync.py`） |
| **3. 验证体系**（测试 / 扫描） | 测试由人诚实编写，绿灯即代表可信 | **Reward Hacking**：删改失败断言、塞 `# noqa`/`--passWithNoTests`、写永不失败的同义反复测试；单测仅捕 7% 前端 / 5% 后端性能坑 | 生产者与裁判分离、PR-Diff 裁判（`audit-pr-diff.py`）、植入负向变异测试、保留一等 `NOT_RUN`/`UNKNOWN`、三层 E2E 与容量总账契约测试 |
| **4. 交付标准**（构建 / 发布 / 部署） | 合入源码提交即代表交付行为确定 | 批准后 Agent 继续 push；未改代码但改 Prompt/模型导致线上突变；“假完成”汇报 | `Evidence -> VerificationResult -> Receipt -> Decision -> Outcome`、SLSA 签发与消费端验签、行为组件清单、`DoneClaim` + `does_not_prove[]` |
| **5. 运维反馈**（监控 / 故障复盘） | 事后写 Wiki 复盘靠人下次记住 | 告警风暴烧穿预算；`RESULT_UNKNOWN` 盲目重试；同账号备份被连坐删除；Wiki 进不了下次会话 | 多维费用/轮次/扇出硬上限、`safety_epoch` 带外急停、Agent 不可达独立备份、**Incident-to-Gate** 门禁化闭环 |

---

## 3. 双轨安全治理：传统研发安全 vs Agent 原生安全

传统安全漏洞在 AI 高速生成下被放大 10 倍，同时叠加了全新的“糊涂代理人（Confused Deputy）”与欺骗门禁风险，必须分轨治理：

| 治理轨道 | 威胁模型 | 核心工程解法 |
|---|---|---|
| **轨道 A · AI 放大的传统研发安全** | 执行者无恶意但高速产出 SQLi、SSRF、IDOR、兜底密钥、幻觉包或破坏性 IaC | 写码前加载 `secure-vibe-coding` 不变量、CI 接入专业 SAST/密钥扫描、**安全相关改动强制配反向安全单测**、锁定依赖哈希与 40 位 Action SHA、共享 IaC 模块按生产同级 `CODEOWNERS` 管控（[secure-vibe-coding.zh.md](secure-vibe-coding.zh.md)） |
| **轨道 B · Agent 时代原生安全** | 开发态或运行态 Agent 被仓库配置/PR 评论注入劫持，或主动改弱门禁自证通过 | 扫描并用 `CODEOWNERS` 锁死 `AGENTS.md`/`.claude/`/`.mcp.json`/`workflows/`、禁用 `pull_request_target` 检出 PR Head 与不可信字段裸插值、用 `audit-pr-diff.py` 拦截删断言/塞抑制注释、外部 GitHub Ruleset 锁死 `require_last_push_approval` 与绑定 `integration_id`、服务端 `SecretRef` + 原子单次审批 + 防只读外泄 |

---

## 4. 核心生命周期与单调交付门

### 准入与范围冻结（Intake）

所有非平凡任务（触及 `>3` 个文件、`>50` 行代码，或涉及启动、鉴权、共享契约、数据库迁移、部署）在改生产代码前必须冻结：
- 业务目标与受保护主流程；
- 显式 `in_scope`、`out_of_scope` 与 UI 范围（默认 `out-of-scope`）；
- 受影响仓库/契约及三层配置影响（代码默认值 vs 部署模板 vs 线上实际值）；
- 唯一人类责任 Owner、可运行验证命令及回滚/停止条件。

### 设计与 ADR 门禁

跨仓库、改架构/契约、改有状态部署行为或触及安全隐私边界的变更必须先设计再编码；影响两个及以上仓库或改变权威边界时必须写 ADR。凡能用确定性 Schema、编译器与状态机表达的逻辑绝不交给 LLM 判断；触发副作用的 LLM 输出必须先进入闭合校验的中间表示（IR）。

### 实现与耦合变更闭包

基于新鲜 `origin/<default>` 创建隔离分支与 Worktree（[multi-ai-git-workflow.zh.md](multi-ai-git-workflow.zh.md)）。改行为前先写会失败的测试（安全边界必含反向安全单测），写码当下遵守前置可靠性与容量不变量（[reliable-and-performant-coding.zh.md](reliable-and-performant-coding.zh.md)），并在同一 PR 中同步更新耦合测试、契约、文档与 `STATUS.md`（由 `scripts/check-change-sync.py` 守门）。

### 独立验证与单调交付门（A0–A5）

高保证交付遵循六道单调递增门禁：

| 门禁 | 裁决边界 |
|---|---|
| `A0 Task Admission` | 冻结任务、精确 Base SHA、范围、风险底线与停止条件 |
| `A1 Local Feedback` | 本地快速反馈（`make agent-check`、Git 钩子、`deps`）——仅作提示，永不签发合并权限 |
| `A2 PR Candidate` | 基于精确 PR Head 运行 Fail-Closed CI 与 `audit-pr-diff.py` 裁判（`authority: candidate`） |
| `A3 Protected Merge Boundary` | 外部 GitHub Ruleset 独立核验精确 PR Head / `merge_group`、`CODEOWNERS`、门禁面双人审查与来源绑定状态检查 |
| `A4 Release & Provenance` | 对同一不可变制品 Digest + 行为变更清单完成构建、测试、SLSA 签发与消费端验签（[versioning-and-releases.zh.md](versioning-and-releases.zh.md)） |
| `A5 Post-Release & Feedback` | 核验线上运行回读，监控 Reopen/改判率/Canary 探针，并将逃逸缺陷闭环沉淀为门禁 |

门禁不可用时必须单调失败关闭：`A3`/`A4` 故障时直接阻断，绝不降级回退到候选 CI 或未测重编包；任何新 push 自动作废旧审批与旧证据；任何修改工作流、`action.yml`、Schema、校验器、测试、`CODEOWNERS` 或 Agent 指令的 PR **绝不可自证**。

### 评审与发布门禁

每个 PR 必须写明变更原因、精确验证命令与退出码、未运行/`NOT_RUN` 项、受保护主流程、风险与回滚路径，以及人类责任 Owner 与 AI 工具/模型归属（[testing-strategy.zh.md](testing-strategy.zh.md)）。

---

## 5. 事故到门禁（Incident-to-Gate）不对称反馈闭环

写在外部 Wiki 里的复盘对下一次 Agent 会话等于不存在。每一次生产逃逸缺陷、高危险情或第二次重复出现的审查问题，都必须按 [`checklists/incident-to-gate.template.md`](../checklists/incident-to-gate.template.md) 完成闭环：

1. 锚定逃逸提交/配置与违背的本体公理（[docs/ontology.zh.md](../docs/ontology.zh.md)）；
2. 补一条在漏洞版本上**必红**、在相邻合法对照上**保持绿灯**的负向测试或确定性规则；
3. 严守**不对称演化铁律**：经验沉淀只能收紧约束、补反向测试或补充上下文，绝不允许自动扩大权限或放宽既有门禁。

---

## 6. 完成定义（Definition of Done）

“完成”是由证据派生出的事实，绝不是 Agent 自填的布尔值：
- 实现符合准入范围，且耦合工件（`tests`、`docs`、`STATUS.md`）已同步闭环；
- 新鲜验证通过，无隐藏的 `NOT_RUN`、`ERROR`、`UNKNOWN` 或欺骗门禁的抑制注释；
- 评审、回执、合并裁决与发布制品摘要绑定**同一精确修订版本**；
- `DoneClaim` 如实声明 `does_not_prove[]` 边界、回滚路径与人类 Owner 签字确认。
