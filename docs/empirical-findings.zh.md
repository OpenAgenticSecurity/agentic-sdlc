# 实证发现：为什么 Coding Agent 会在真实代码库里翻车

**状态**: empirical evidence summary
**更新日期**: 2026-11-21
**English**: [empirical-findings.md](empirical-findings.md)

`OpenAgenticSecurity/agentic-sdlc` 中的每一条标准、清单、Skill 与 Fail-Closed
脚本，均提炼自真实多仓 AI 辅助生产工程实践，而非凭空构想的 Prompt 建议。

在累计 **2000+ 亿 Token** 的持续多仓 Agentic 工程开发（Claude Code、Cursor、Codex
并发协作，覆盖 Python、TypeScript、React 与 Rust 服务）基础上，我们完成了
**四项边界清晰、分母明确的专项量化研究**，并沉淀了多起高成本运维事故。本文汇总原始数据、失效机制、本仓库对应的可执行控制措施，以及这些观测数据**不能证明的边界**。

---

## 1. 实证总览（严格区分分母）

为遵守本仓库自己的原则（`假完成断点 #4：分母口径一致`），下方每组指标都严格绑定其对应研究样本，不将单一子研究数据直接外推到全部 2000+ 亿 Token：

| 专项研究 / 真实事故 | 精确样本与分母 | 核心量化结论 | 本仓库对应控制措施 |
|---|---|---|---|
| **1. 会话生存与七宗罪** | 443 次追踪会话 / 84 亿 Token 样本集 | `<5K` 行自主模式成功率 ~100%，`>10K` 行无结构开发跌至 ~55%；超过 200 条消息后失败率从 `<10%` 飙升至 **35.7%** | [vibe-coding-seven-sins.zh.md](../checklists/vibe-coding-seven-sins.zh.md)、[ai-coding-context.zh.md](../standards/ai-coding-context.zh.md) |
| **2. 前端缺陷审计** | ~10 万行 React/TS 前端 454 个去重缺陷（321 个明确根因；216 个明确发现渠道） | 单元测试、`tsc` 与 CI 合计仅抓出 **7%**；前 4 类根因占 **84%** | [frontend-vibe-coding-review.zh.md](../checklists/frontend-vibe-coding-review.zh.md)、[`audit-pr-diff`](../skills/audit-pr-diff/SKILL.md) |
| **3. 后端性能审计** | ~38 万行 FastAPI + SQLAlchemy + Celery + K8s 100+ 项真实修复 | 仅 **16%** 为主动发现；仅 **5%** 由 CI 捕获 | [backend-performance-review.zh.md](../checklists/backend-performance-review.zh.md)、[ci-python.yml](../profiles/L1-team/workflows/ci-python.yml) |
| **4. 假完成与 Review 复核** | 24 条 AI Review 复盘；15 条旧门禁样本；43 条反证复核；33 张架构图 | **24 → 2** 真实阻断项；**15/15 → 0/15** 旧门禁漂移；**43 → 29** 反证后缩减；**0/33** 架构图无条件准确 | [fake-done-dereference.zh.md](../checklists/fake-done-dereference.zh.md)、[`done-claim-verify`](../skills/done-claim-verify/SKILL.md)、[observe-github-ruleset.py](../scripts/observe-github-ruleset.py) |
| **5. 多仓与子 Agent 运维事故** | 真实多 Worktree 与子 Agent 生产运行 | Fork 子 Agent **1 小时烧掉 ~2.6 亿 Token**；审计归档 **7.8 GB vs 240 KB**；Worktree 静默跑错主仓代码 | [agent-ops-and-workspace-hygiene.zh.md](../checklists/agent-ops-and-workspace-hygiene.zh.md)、[link-shared-node-deps.mjs](../scripts/link-shared-node-deps.mjs)、[workspace-git.py](../scripts/workspace-git.py) |

---

## 2. 研究一：1 万行代码相变临界点与上下文悬崖

在 443 次会话 / 84 亿 Token 的追踪样本中：

- **规模相变**：`<5K` 行、1–6 次会话的一次性项目，对话式自主开发成功率接近 100%；一旦代码库跨越 `>10K` 行且经历 50+ 次会话，无结构 Vibe Coding 成功率断崖式跌至 **~55%**，跨会话一致性持续劣化。
- **三类核心失败原型**：
  1. **沙箱墙（~60%）**：写权限、网络或工具环境不匹配，导致 Agent 在权限报错里盲目死循环。
  2. **上下文窗口耗尽（~25%）**：早期失败率 `<10%`，超过 200 条消息后飙升至 **35.7%**。
  3. **能力/过滤天花板（~15%）**：将复杂架构改动派给低推理模式或错误工具形态。
- **高频“七宗罪”**：过早宣布胜利、幽灵模块（写完从未接入调用方）、跨会话缝合怪架构（`async def` 混入同步 DB）、大爆炸式重写、过度逼真的假数据兜底、永不清理的 `DEFAULT = False` 沉睡开关，以及与代码脱节的“进度幻觉文档”。

**本仓库的工程解法**：以 `STATUS.md` 锚定代码现实、60 条消息强制压缩边界、“接线或删除（Wire it or delete it）”硬约束，以及 `scripts/workspace-git.py` 防止多 Agent 写脏 `main`。

---

## 3. 研究二：前端 454 个真实缺陷——为什么绿灯 CI 只抓出 7%

在 ~10 万行 React/TypeScript 前端的 454 个去重问题中（321 个可归因根因，216 个明确发现渠道）：

- **真实发现渠道**：**35%** 由人工实际点击发现，**31%** 由深度审计挖出，单元测试、`tsc` 与 CI 合计仅抓出 **7%**（且其中大部分来自浏览器 QA Agent，而非单元测试）。
- **核心原因**：后端失败会抛 HTTP 500 和堆栈；前端失败往往靠 `?? 0` 或 `|| []` 渲染出一个“看起来完全正常”的错页面。
- **前 4 类根因占全部已归因缺陷的 84%**：
  1. **未断言的跨层边界（39%）**——占契约漂移的 95%、入口/权限不一致的 77%（UI 隐藏了已禁用功能，但直达路由或后端接口仍放行）。
  2. **仅在小规模/演示数据下成立（18%）**——流式 Markdown O(n²) 重渲染、安全证据被静默截断、无节制轮询。
  3. **就近复制粘贴而非修共享层（16%）**——占重复代码的 70%、布局/嵌套滚动陷阱的 55%。
  4. **用逼真假默认值替代显式 `UNKNOWN`/错误态（11%）**——把 `loading`、`error`、`真正为空` 全部混用 `[]`。
  5. **门禁/测试本身失效（4%）**——`0 tests collected` 或缺失依赖时以退出码 0 绿灯跳过。

**本仓库的工程解法**：前端四层验收阶梯（*Rendered → Reachable → Correct → Holds at scale*）、禁用功能三层联测、[`audit-pr-diff`](../skills/audit-pr-diff/SKILL.md) 技能，以及 Fail-Closed 的 [ci-node-ts.yml](../profiles/L1-team/workflows/ci-node-ts.yml)。

---

## 4. 研究三：后端性能——P50 能跑，P99 崩塌

在 ~38 万行 FastAPI + SQLAlchemy + Celery + Kubernetes 后端的 100+ 项真实性能修复中：

- 仅 **16%** 在上线前主动发现；仅 **5%** 被 CI 抓出。
- **核心原因**：Agent 默认在 **P50**（6 条事件、38 行数据、23 秒）自测；生产环境在 **P99**（1,000+ 事件、10 万行、90+ 分钟运行）以及单文件 diff 看不见的**乘数账本**（进程数 × 连接池大小 × 滚动发布倍率）上崩塌。
- **典型陷阱**：`async def` 注入同步 SQLAlchemy `Session`、跨越 `await` LLM 调用一直占着数据库连接、PostgreSQL 外键缺索引与 N+1 查询、超时不等式倒挂（`soft > hard` 或 `hard > visibility_timeout`）、空载时高频 `<60s` Beat 任务持续写结果库、无上限 Agent 工具死循环。

**本仓库的工程解法**：在 [ci-python.yml](../profiles/L1-team/workflows/ci-python.yml) 内置 Ruff `ASYNC`/`B`/`S` 规则，在 [backend-performance-review.md](../checklists/backend-performance-review.md) 固化连接池与超时不等式契约测试，并在 [`scripts/audit-repo.py`](../scripts/audit-repo.py) 中落地静态高危陷阱扫描。

---

## 5. 研究四：“假完成”与为什么不能让 Agent 自审自批

四次独立取证审计揭示了 AI 研发流程制造“绿灯幻觉”的典型路径：

- **24 → 2 AI Code Review 复核**：分块 diff 审查输出的 24 条自信结论，在核对精确 PR Head 源码、调用链与测试后，仅 **2 条**为真实阻断项。
- **15/15 → 0/15 旧门禁漂移**：一条全绿自动化门禁一直忠实地校验着过时的 Schema（`15/15` 全过），却对真实当前契约 `0/15` 失效。
- **43 → 29 反证复核**：把“事实置信度（代码存在）”与“影响置信度（真实控制下可达）”拆开后，约三分之一的高危结论被证伪。
- **0 / 33 架构图无条件准确**：合法 SVG/XML 只证明语法正确，不证明与代码现实一致。

**本仓库的工程解法**：
1. 严禁把 `NOT_RUN`、`FLAKY`、`ERROR`、`UNKNOWN`、`CONFLICT` 折叠成 `PASS`（[done-claim-verify](../skills/done-claim-verify/SKILL.md)）。
2. 用带 `does_not_prove[]` 的七元组 `DoneClaim` 取代裸布尔 `"done": true`（[done-claim.template.md](../checklists/done-claim.template.md)）。
3. 将 PR 受控 CI 显式定性为 **candidate / advisory（不可自证）**，通过 [`scripts/observe-github-ruleset.py`](../scripts/observe-github-ruleset.py) 与 [`scripts/audit-repo.py`](../scripts/audit-repo.py) 审计外部 GitHub 合并边界——现场拦下批准后仍可推新提交（`require_last_push_approval: false`）、未绑定来源的可伪造状态检查（`integration_id: null`）以及无条件绕过角色。

---

## 6. 10 秒在你自己的仓库上验证它到底有没有用

不要轻信任何文档数字。直接对**你自己的仓库**跑一遍零依赖、严格只读的自检脚本（仅需 Python 3.11+ 标准库，无需 `pip install`，绝不修改任何文件）：

```bash
# 审计本地第一层与第二层风险（Agent 上下文、Worktree 卫生、CI Action SHA 锁定、Python AST 安全陷阱）：
python3 scripts/audit-repo.py /path/to/your-repo

# 同时只读审计你仓库线上的 GitHub Branch Ruleset 是否防得住 AI 批准后推代码与伪造状态检查（需 gh CLI）：
python3 scripts/audit-repo.py /path/to/your-repo --github
```

如需离线验证本仓库自身的负向变异测试门禁确实会在违规输入上变红（零联网）：

```bash
python3 -m pip install --require-hashes --only-binary=:all: -r requirements-test.txt
make demo-catch-bugs
make verify-all
```

---

## 7. 诚实边界（`does_not_prove`）

遵循本仓库自身的取证标准，上述实证数据**显式不能证明**：

- 所有团队或技术栈都会出现与我们 Python/TypeScript/React 多仓体系完全相同的缺陷比例。
- 仅安装 Markdown 清单或 Agent Skills 就能防住蓄意 Prompt Injection，或替代运行时安全测试与人类工程判断。
- `scripts/audit-repo.py` 跑绿不代表仓库“绝对安全”——静态检查只能捕获特定的高信噪比结构与供应链缺陷；运行期语义、业务逻辑越权与生产级峰值容量仍需集成测试与外部强门禁保障。
