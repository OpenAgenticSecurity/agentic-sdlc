# 「假完成」解引用审计与证据清单

**状态**: accepted baseline
**更新日期**: 2026-11-20
**English**: [fake-done-dereference.md](fake-done-dereference.md)
**实证来源**: [《Agentic Assurance Engineering》](https://fz.cool/agentic-software-engineering-real-sdlc/)、[《Agent 是如何失败的：“假完成”的验证断点》](https://fz.cool/agentic-fake-done-breakpoints/)
**配套模板**: [done-claim.template.md](done-claim.template.md) | [done-claim.example.json](done-claim.example.json)

> **核心原则**：Agent 交出来的东西，默认只是一份不可信草稿。验收时绝不停留在绿色标签（`active`、`v2`、`HTTP 200`、`all tests pass`）上，而是**顺着标签解引用（dereference）回真实对象、精确版本、用户性质、运行包络与一手来源**。

---

## 1. 四个解引用断点排查表

任何非平凡交付都可能在一片绿灯下从以下四个维度独立断开，交付前逐项核对：

| 断在哪 | 你看到的绿灯 | 必须解引用核对的外部事实 |
|---|---|---|
| **1. 对象身份 `subject identity`**（改的是不是正在干活的那个） | 配置已更新、目录切到新 checkout、服务显示 `active`、版本号正确 | 从存活 PID 反查工作目录与实际加载代码版本，再确认线上请求确实打到这个进程/制品上 |
| **2. 验收语义 `acceptance predicate`**（验的是不是用户要的那件事） | 组件能渲染、单测写了断言、接口返回 HTTP 200 | 沿真实用户路径从头点到尾，核对前后端对同一规则的理解一致（如功能关闭时入口隐藏、直敲 URL 拒绝、后端返回 403/404） |
| **3. 运行包络 `workload / lifecycle`**（测的是不是真实运行世界） | before/after 数字好看、发出了超时/取消信号 | 绑定代码版本 + 环境 + 尾部负载规模，并确认超时/取消后底层 worker 真的停止且释放资源 |
| **4. 结论来源 `claim provenance`**（报告里的话有没有一手证据） | 报告工整、数字齐全、案例列表很长 | 逐条回到一手证据定性、核对统一可比的分母、保留不可变快照、写明什么新证据会推翻该结论 |

- [ ] **First-breakpoint 铁律**：跨阶段链路在第一个可信不变量处失败就停下，后续阶段标为 `not reached`；绝不临时绕过鉴权或拼接不同 trace 凑“端到端闭环”。

## 2. `DoneClaim` 最小七元组

每一项完成主张必须填写以下 7 个要素（直接使用 [done-claim.template.md](done-claim.template.md)）：

```text
DoneClaim = subject + revision + environment + predicate
          + evidence_locator + independent_observer + limits (does_not_prove[])
```

- [ ] 绝不接受裸布尔值（`"done": true`）或没有 `evidence_locator` 和 `does_not_prove[]` 的口头总结。
- [ ] 严格区分 **Seeded Readback**（只证明写入/回读管道通）与 **Native Producer Proof**（必须具备授权执行、`source_commit` + `deployment_digest`、`stable_trace_id`、独立回读与 `bridge_writer: none`）。

## 3. 严禁把合法非绿状态压扁成绿灯

| 状态 | 含义 | 规则 |
|---|---|---|
| `PASS` / `VERIFIED` | 单项检查通过 / 主张在声明边界内得证 | 必须由解引用证据派生，绝不由 Agent 自签 |
| `FAIL` | 观察到不变量被违反 | 必须触发阻断（`failure_effect`） |
| `NOT_RUN` | 检查或依赖未运行 | 严禁改标为 `PASS` |
| `UNKNOWN` | 缺少身份、版本或观测事实 | 严禁编造合理默认值 |
| `CONFLICT` | 多源证据互相矛盾 | 升级 `HITL`，严禁悄悄选更绿的那一个 |
| `ERROR` | 校验器或测试框架自身报错 | 按未通过处理 |
| `NOT_APPLICABLE` | 某维度对当前主张明确不适用 | 必须显式声明，不得静默省略 |
| `HITL` / `FAILED` | 需要人工授权/接受风险，或预算耗尽 | **合法停止出口**——必须允许 Agent 体面停下来 |

## 4. 四层交付证据（严禁越层外推）

| 证据层 | 能证明 | 不能证明 |
|---|---|---|
| **Source** | 代码进入指定 commit SHA | 该 commit 已部署 |
| **CI / Build** | 候选版本通过指定构建与测试 | 运行实例正在跑该产物 |
| **Deploy provenance** | 存活进程/镜像对应具体 commit/digest 与配置 | 真实业务路径被成功触发 |
| **Runtime readback** | 一次授权执行产出对象并被独立回读匹配 | 生产峰值容量、所有环境或无其他回归 |

## 5. 连门禁、Review 与架构图本身也要审计

真实复盘数据提醒我们——**校验器自己也会漂移**：
- **15/15 → 0/15 旧门禁漂移**：绿色 gate 忠实通过了 15 个旧版兼容对象，在当前权威 0.2.3 validator 下全灭。
- **24 → 2 条 AI Review 取证**：没有 PR-head checkout 的分块 diff Review 只能产出 **candidate finding**，未经源码/调用点/历史/测试核实不得升级为 blocking finding。
- **43 → 29 条反证复核**：把 **Fact confidence（代码事实是否存在）** 与 **Impact confidence（在当前部署、鉴权与控制下是否可达）** 拆开评估。
- **33 张架构图 0 张无条件 Accurate**：XML/SVG 合法只证明语法可解析，不证明节点、边、同步/异步和成熟度符合当前代码。

### 门禁与审计自查项

- [ ] 每道阻断门禁显式绑定：`verifier_version`、`subject_version`、`fixture_origin`、可复现 `command`、`failure_effect` 以及带 `owner` + `expires_at` 的临时例外。
- [ ] AI Review 结论默认为 **candidate finding**，升级阻断前必须基于精确 PR-head checkout 给出 `file:line`、调用点、历史和线程核验。
- [ ] 高危审计结论必须经过**独立反证复核**（不同证据源或角色主动寻找部署反例与前置条件）。
- [ ] `STATUS.md` 与架构图必须附带 `verified_at`、`source_commit`、复核命令与 `does_not_prove[]`；过期即降级为历史文档。

## 6. 接受任何 Agent 交付前的七个问题

1. 谁定义了目标和共享事实？
2. Agent 以谁的身份行动、能影响多大范围？
3. 谁此刻拥有活跃写入权？
4. 这项改动最先应该在哪里失败（反向用例 / 故意植入违规）？
5. 当前证据最多只支持 Source、CI、Deploy 还是 Runtime？
6. 什么反例会推翻当前的影响判断？
7. 谁有权接受剩余风险、谁有权提高自治等级？
