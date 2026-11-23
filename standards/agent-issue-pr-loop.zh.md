# AI Agent Issue 到 PR 闭环标准

**状态**: accepted baseline
**更新日期**: 2026-11-20

## 目标

本标准把 AI coding agent 发现问题、制定优化计划、本地实现、PR 合并和 issue 关闭串成可审计闭环，适用于任意采用本标准的单仓或多仓协作项目。

闭环的目的不是制造流程负担，而是保证可行动问题不会只留在聊天记录、本地笔记或 PR prose 中；同时防止 AI agent 把未经归属、未经验收、未经验证的想法直接变成代码。

## 标准闭环

1. **发现或计划**：agent 发现 bug、安全缺口、技术债、文档漂移、缺失测试、能力缺口，或提出可执行优化计划。
2. **归属判断**：在归属仓库建单；跨仓库工作建立 parent issue 和分仓 child issues。
3. **查重和建单**：先搜索已有 issue；已有则更新或引用，没有则创建新 issue。
4. **范围冻结**：issue 必须写清 in-scope、out-of-scope、验收标准、验证计划、风险、依赖和 owner。
5. **设计门禁**：跨仓库变更、共享契约调整或安全边界修改应先开设计/计划 PR；小型单仓库修复可直接进入实现。
6. **可见 claim**：编辑前发布或更新 [multi-ai-git-workflow.zh.md](multi-ai-git-workflow.zh.md) 定义的 managed issue claim comment（可用 `scripts/agent-claim.py`）。
7. **隔离开发**：按 [multi-ai-git-workflow.zh.md](multi-ai-git-workflow.zh.md) 创建一个任务、一个 branch、一个 worktree、一个 owner。
8. **实现和验证**：只修改 scope 内文件，运行 issue 或 plan 中声明的验证命令，并记录新鲜输出。
9. **PR 关联**：PR 必须引用 closing 或 related issue、plan/RFC PR、依赖 PR，并包含验证证据、风险和回滚说明。
10. **Review 和合并**：通过 required checks 和 owner review 后合并；默认 squash merge。
11. **关闭 issue**：只有验收标准满足、验证证据存在、文档同步完成、依赖解决或 superseded 后才关闭 issue。
12. **同步和交接**：PR merge 后将被触及仓库回到 clean latest default branch；交接中报告 PR URL、merge 状态、issue 状态、验证命令和本地 checkout 状态。

## 什么时候必须开或更新 Issue

AI agent 或人类发现以下事项时，交接前必须创建或更新 GitHub issue：

- 可复现 bug、异常路径、silent failure、数据损坏或用户可见错误。
- 安全缺口、权限边界、secret 处理、客户证据、远程执行或审计问题。
- 技术债会影响主流程、部署、测试、迁移、契约或后续开发。
- 文档与实现现实不一致，且会误导跨仓库决策、销售、交付或 agent task。
- 缺失测试会让已修复或已交付行为无法防回归。
- 优化计划已经能写出明确 owner、scope、验收标准和验证计划。
- 当前任务发现了 out-of-scope 但可行动的问题。

如果 GitHub 不可用，handoff 必须给出目标仓库、建议标题、完整 issue body、labels、查重结果和未建单原因。

## 什么时候不要开 Issue

以下情况不应强制建单：

- 只是聊天中的初步想法，尚无明确影响、owner 或验收标准。
- 一次性本地实验、临时调查记录或不可复现现象。
- 已在当前 PR scope 内完成，且 PR body 已完整说明、无需后续追踪的小型机械修复。
- 纯个人偏好、代码风格意见，且未违反现有标准。
- 已有 issue 覆盖的问题；应更新或引用已有 issue，避免重复。

不能因为“不想开 issue”而把可行动问题藏在 final answer、PR 描述或本地 todo 里。

## Issue 质量门槛

实现类 issue 必须至少包含：

- 归属仓库和发现来源。
- 背景、影响、当前行为或证据。
- in-scope 和 out-of-scope。
- 方案或待评审方案。
- 可观察验收标准。
- 可运行验证计划。
- 风险、依赖和关联文档。

优化计划类 issue 还必须包含 owner、阶段、stop condition，以及哪些内容不允许在未验证前作为 GA、销售承诺或默认客户体验。

## PR 质量门槛

关闭或推进 issue 的 PR 必须包含：

- `Closes #N`、`Fixes #N` 或 `Related #N`。
- 对跨仓库 issue 使用仓库全名引用，例如 `org/service-a#12`。
- 实际运行过的验证命令，而不是计划运行的命令。
- docs、contracts、status/context 文件是否已同步。
- 风险、回滚、依赖顺序和剩余 follow-up。
- AI-assisted work 的 agent/tool、branch owner 和 worktree。

PR 不能只给 `/pull/new/...` 创建入口链接；必须是真实存在的 PR URL。

## Issue 关闭规则

Issue 只能在以下条件满足后关闭：

- issue 中的验收标准已满足，或明确被更新为 superseded。
- closing PR 已 merge，或 closing comment 附有可审计验证证据。
- 必要文档已更新到正确权威位置。
- 跨仓库 child issues 已关闭、转移或明确阻塞状态。
- 非目标没有被偷偷纳入范围。
- 交接报告说明本地仓库是否回到 clean latest default branch。

未实现而关闭时，使用 `superseded by #N`、`duplicate of #N` 或 `won't do because ...`，不能静默关闭。

## 让采用方仓库合规落地

每个采用本标准的仓库应具备以下入口和自动化信号：

- `AGENTS.md` 和 `CLAUDE.md` 明确要求遵守本标准，并保持行为等价。
- `.github/ISSUE_TEMPLATE/issue.md` 和 `epic.md` 包含范围、验收标准、验证计划、归属仓库和依赖字段。
- `.github/pull_request_template.md` 要求 issue links、verification、risk/rollback、docs updates 和 AI assistance。
- 至少一个 CI workflow 在精确 PR head 上运行仓库检查。
- `Makefile` 提供 `agent-check` 或等价本地命令，供 AI agent 在交接前运行。
- 仓库本地 `docs/VIBE_CODING_CONTEXT.md` 和 `docs/architecture/STATUS.md` 说明当前实现现实、主流程和验证入口。

可用内置只读自检脚本检查任意仓库的档位合规状态：

```bash
python3 scripts/audit-repo.py --profile L1 /path/to/your-repo
```

或执行 `make product-compliance REPO=/path/to/your-repo`。该检查不能替代 code review，但可以暴露哪些仓库尚未把闭环规则接入入口文件、模板和本地检查。

## 与其他标准的关系

- 多人多 AI worktree 实践与 Managed Claim：见 [multi-ai-git-workflow.zh.md](multi-ai-git-workflow.zh.md)。
- Agent context 和 status 文件要求：见 [ai-coding-context.zh.md](ai-coding-context.zh.md)。
- 生命周期与交付门禁：见 [sdlc.zh.md](sdlc.zh.md)。
- 测试与验证规则：见 [testing-strategy.zh.md](testing-strategy.zh.md)。
