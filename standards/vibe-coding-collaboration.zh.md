# Vibe Coding 协作标准

**状态**: accepted baseline
**更新日期**: 2026-11-20

Vibe Coding 想要快，前提是上下文、所有权和验证明确。本标准适用于单仓或多仓项目中协作的人类工程师与 Coding Agents。

## 核心规则

- 跨仓库架构与契约决策放在组织共享文档仓（或独立的 `docs/architecture/`）。
- 产品/服务实现细节留在所属业务仓库。
- 不做静默的大范围重构。
- 不在未更新契约文档和测试的情况下改变共享契约。
- 没有新鲜验证输出，不声称完成。
- 优先小 PR，而不是混合大改。
- 保留你没有做出的用户或队友变更。
- 稳定性优先：先保护主流程、已交付功能、部署路径和用户可见行为。
- 服务与平面边界是执行约束：不要把事实存储、建议逻辑、策略控制门禁与外部工具执行揉成同一条无边界路径。
- 未明确纳入 scope 时，不顺手改前端 UI。

## Agent 任务上下文包

每个 agent task 应包含或主动发现：

- repository 和 branch
- 精确目标
- scope 内文件或模块
- scope 外文件或模块
- protected primary flow
- affected product boundaries
- UI scope: in-scope 或 out-of-scope
- 相关产品文档
- 相关平台文档
- expected tests
- stop conditions

仓库本地 coding 工作应先读取 [ai-coding-context.zh.md](ai-coding-context.zh.md) 定义的 AI context 文件。跨仓库工作还应读取共享架构文档、集成契约与 [sdlc.zh.md](sdlc.zh.md)。

## Multi-Agent Work

只有当任务相互独立、写入范围不重叠时，才使用并行 agents。必须明确文件 ownership。

安全拆分示例：

- 一个 agent 更新数据层文档
- 一个 agent 更新 API 适配器测试
- 一个 agent 审查 contract fixtures

不安全拆分示例：

- 两个 agents 编辑同一个 contract file
- 一个 agent 改 schema，另一个 agent 未协调地改 consumers
- 一个 agent 重构产品边界，另一个 agent 根据旧假设写 docs

Multi-agent work 还必须遵循 [multi-ai-git-workflow.zh.md](multi-ai-git-workflow.zh.md)：一个任务、一个 branch、一个 worktree、一个 owner。

## 跨层一致性与共享层修复

Agent 最常反复引入的缺陷不在单个文件里，而在层与层之间，或在一个每次改动都在本地绕过去的共享层里。

- 被禁用或未授权的功能必须在所有层同时禁用：导航入口、直接路由、后端 API，以及任何公开的 feature flag 接口。用一个测试从同一个 flag 或 registry 断言所有层，新增的层才不会漏掉。
- 接线是变更的一部分。新增 API 要连同调用方一起交付，新增设置或开关要连同读取它的运行时代码一起交付。没有调用方的接口、没有读取方的开关，都不算完成。
- 一个展示语义只有一个权威字段。两个视图从不同字段推导同一个状态，或客户端重新推导后端已经决定的结果，即使当前碰巧一致，也是缺陷。
- 同一缺陷第二次出现时，在共享层（请求客户端、序列化、状态存储、基础组件）修复，而不是再加一个本地绕行。同一个 helper 或组件出现第二份拷贝时，在第三份出现前收回共享层。
- 为绕开共享层缺陷而写的解释性注释，记录的是一个未关闭的 bug。关联或新开 issue；注释本身不是修复。
- 同一组件或流程一周内需要第三次修复时，停止打补丁。重新建模它的状态和数据流，并在下一次修复前为这一类失败补上测试。

## 人工评审重点

人工 reviewer 应检查：

- agent 是否尊重 scope
- agent 是否保护主流程并提供稳定性证据
- agent 是否尊重产品边界和 UI scope
- 假设是否符合产品现实
- 测试是否证明了正确行为
- 新增的兜底写法（`?? 0`、`|| []`、默认参数、只打日志的 `catch`）是否会让读取失败看起来像有效数据
- 修复是否在重复一个本应放进共享层的本地绕行
- 文档是否更新在正确权威位置
- 生成式文字是否夸大成熟度

## 禁止模式

- 把单个服务的 runbook 直接塞进共享标准仓库
- 不经抽象就把大段产品实现细节复制到共享治理文档中
- 改动多仓 workspace 根目录的 Git 状态
- 未经 owner review 就把生成文本当成当前事实
- 把商业 pitch 材料和工程权威文档混在一起
- 在修复后端、队列、部署、MCP 或数据模型问题时顺手改 UI
- 把数据事实层、建议推理层、策略控制门禁与外部工具适配混成单一无护栏实现

## Status Truth 规则

判断仓库实现现实时，以本地 `docs/architecture/STATUS.md` 为准，而不是旧 roadmap、旧 architecture 或生成文档。如果模块被标记为 deleted 或 design-only，不要在未读源码前假设它存在。

## Context Drift 规则

如果工作改变了实现现实，任务结束前更新本地 status/context 文件。如果变更影响跨仓库边界，同一批 PR 中同步更新共享文档。

## 结束状态规则

任务完成时，默认交接状态是每个被触及仓库都回到 clean latest default branch。如果 local-only WIP 让切换或 fast-forward 不安全，保留这些 WIP，并报告该 repo 未结束在 default branch 的原因。

## Handoff 格式

跨人或跨 agent 交接时使用：

```text
Goal:
Repos:
Branch:
Files changed:
Contracts affected:
Boundaries affected:
Protected flows:
UI scope:
Tests run:
Docs updated:
Risks:
End state:
Next owner:
```

## 批量迁移验收

替换共享组件、helper 或契约前，列出全部生产消费者、owner、迁移状态、合理例外和验收测试。
新抽象与 leaf 测试通过不等于消费者迁移完成。提取时保持调用时依赖绑定、事务/owner 边界与
失败语义，并验证实际生产调用方。

独立分支还要验证组合后的树，覆盖共享 import、locale、schema、依赖锁和 bundle budget。
分别固定 baseline、review head 与 merged tree。typing/lint/复杂度门不增长不等于存量债务为零。
兼容删除除静态零调用外，还需要外部消费者、运行使用、兼容窗口、数据处置与回滚证明。
本地性能优化使用同一 workload 对照，并与生产 SLO 证据分开。
