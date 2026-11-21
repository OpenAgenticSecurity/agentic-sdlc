# Agentic SDLC 标准

**状态**: accepted baseline
**更新日期**: 2026-11-20

该 SDLC 面向单仓或多仓 Vibe Coding 项目，适用于人类工程师与 Coding Agents 协同开发。

## 生命周期

1. Intake
2. Design
3. 必要时 ADR
4. Implementation plan
5. Branch setup
6. Test-first 或 test-pinned implementation
7. Review
8. Release
9. Post-release verification
10. Retrospective

## Intake

每个非平凡任务应明确：

- business goal
- protected primary flow
- affected repositories
- affected contracts
- affected product boundaries
- owner
- expected verification
- rollback 或 stop condition

## Design

以下变更必须先设计再实现：

- 影响多个仓库
- 改变架构或产品边界
- 改变契约
- 改变部署或运营行为
- 触及安全、隐私或客户证据

小型产品本地变更可以使用产品本地 issue 或 PR 描述。

设计阶段必须遵守核心工程边界：运行期行为优先使用显式配置，持久异步工作使用受管队列语义，稳定性优先于未要求的功能扩张，将服务/仓库边界视为执行约束，UI 变更必须有明确 scope，可算法化实现优先于 LLM 判断，LLM 输出进入执行路径前必须经过闭合 Schema 验证与策略门禁。

## ADR Gate

当决策影响两个或两个以上仓库，或改变平台权威边界时，必须写 ADR。

## Implementation Plan

实施计划应拆成可独立评审的任务。每个任务应说明：

- touched files
- tests added or changed
- commands to run
- expected result
- documentation update

## Testing Gate

没有新鲜验证证据，变更不能视为完成。最低要求：

- 产品本地变更跑产品本地测试
- 跨产品契约变更跑 contract tests
- 文档变更跑 documentation checks
- 发布和交付变更跑 smoke 或部署验证

见 [testing-strategy.zh.md](testing-strategy.zh.md)。

Code Health candidate 工作遵循同一 test-first 边界：先发布 closed contract 和
negative fixture，再做产品 adapter；candidate check 必须不写入，并继续保留
periodic/full/release compatibility suite。F2 评估 exact base/head pair，从 exact tree
读取 policy/baseline，并将不支持的语言 adapter 报告为 `NOT_EVALUATED`。Docs-only PR
运行 `make check`，不机械运行完整 frontend/backend suite；如果实际触及 shared contract、
architecture/enforcement、build 或 release boundary，仍必须扩大 closure。纯 backend 内部
变更不会机械触发完整 frontend suite，除非 affected-contract closure 穿越共享边界。

## 受治理 UI 交付门

接入 UI Assurance 的产品使用六个单调门：

| 门 | 决策边界 |
|---|---|
| `A0 Task Admission` | 批准 task、base、scope、Surface、risk floor、context 与 stop conditions |
| `A1 Local Feedback` | 提供快速 advisory feedback，不签发 merge authority |
| `A2 PR Candidate` | 重算 actual diff 与 obligation，并保留 candidate evidence |
| `A3 Trusted Merge Guardian` | 按 protected policy 与 review 独立评估 exact PR-head 和 merge-group revision |
| `A4 Preview and Release` | 测试并准入同一个 immutable artifact digest |
| `A5 Post-release` | 追加 canary、escape、blockage、flake、latency 与 effectiveness observation |

不可用语义必须单调：已 enforced 的 `A3` 阻断，而不回退 candidate CI；`A4` 阻断，而不发布
未经测试的 rebuild。新 push 会使旧 head evidence 失效。修改自身 validator、workflow、
schema、test、CODEOWNERS、PR template 或 Agent instruction 的 PR 不能自证，必须由
architecture/contract owner 与另一名独立 mechanism reviewer 评审。

## Review Gate

每个 PR 应说明：

- 改了什么
- 为什么改
- 如何验证
- 保护了哪些主流程，以及哪些主流程可能受影响
- 是否改变产品边界、异步任务语义或 UI scope
- 风险与回滚
- 文档更新，或为什么不需要更新

Vibe Coding 工作应包含 agent context 和需要人工复核的生成式假设。

## Release Gate

Release candidate 应包含：

- version 或 tag
- compatibility statement
- release notes
- test evidence
- 契约变化时的 migration notes
- rollback notes

## Definition of Done

任务只有在以下条件满足时才算完成：

- 实现符合 accepted design，或记录了偏离原因
- 测试或检查新鲜通过
- 文档更新在正确权威位置
- 没有未解决占位符
- 风险和回滚路径明确
- owner 接受变更
