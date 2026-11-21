# AI Coding Context 标准

**状态**: accepted baseline
**更新日期**: 2026-11-20

## 决策

每个采用本标准的仓库都应提供一组轻量 AI-coding context 文件，让 Claude Code、Codex、Cursor、Gemini CLI 及其他 Coding Agents 从同一份项目事实开始工作。

共享标准定义结构；各业务仓库负责维护自身具体内容。

## 产品仓库必备上下文文件

| 文件 | 要求 | 用途 |
|------|------|------|
| `AGENTS.md` | 推荐作为唯一仓库根规范 | 工具中立的 Agent 指令与仓库边界（Cursor、Codex 等主流工具均原生读取） |
| `CLAUDE.md` | 极薄 `@AGENTS.md` 指针（与 `AGENTS.md` 行为等价） | Claude Code 入口，直接引用 `AGENTS.md`，避免维护两份重复规则 |
| `docs/VIBE_CODING_CONTEXT.md` | 活跃产品仓库必需 | 两分钟工作记忆：什么存在、什么已删除、当前 sprint、技术栈、代码模式 |
| `docs/architecture/STATUS.md` | 活跃产品仓库必需 | implemented、partial、deleted、design-only、planned modules 的单一事实源 |
| `docs/todo/TECH_DEBT_TRACKER.md` | 推荐 | 当前技术债 inventory 和可见状态 |
| `docs/todo/VIBE_CODING_DEBT_PROTOCOL.md` | 推荐 | 从历史 AI coding 错误中学习出的预防规则 |
| `.cursor/rules/*.mdc` | 可选（仅用于按 `globs:` 路径触发的局部规则） | Cursor 已原生读 `AGENTS.md`，避免再用 `alwaysApply: true` 重复一份全局规则 |

## Session Start 顺序

AI coding session 应按顺序阅读产品本地上下文：

1. `docs/VIBE_CODING_CONTEXT.md`
2. `docs/architecture/STATUS.md`
3. `CLAUDE.md` 或 `AGENTS.md`
4. 如果任务触及已知技术债，读 `docs/todo/TECH_DEBT_TRACKER.md`
5. 如果存在，读 `docs/todo/VIBE_CODING_DEBT_PROTOCOL.md`
6. 如果任务跨仓库，读组织内的共享架构与契约文档

如果 `STATUS.md` 与其他文档冲突，以 `STATUS.md` 作为实现现实的事实源。

## VIBE_CODING_CONTEXT 模板

`docs/VIBE_CODING_CONTEXT.md` 应回答：

- 这个产品是什么？
- 代码里实际存在什么？
- 什么已经删除，agent 不应假设它还存在？
- 什么只是 design-only？
- 精确技术栈是什么？
- 当前 sprint 或 release boundary 是什么？
- 新代码应该放在哪里？
- agent 编辑前必须读哪些文件？
- 声称完成前必须运行哪些检查？
- 需要保护的主流程是什么？
- 本次任务影响哪些产品边界？
- UI scope 是 in-scope 还是 out-of-scope？

## STATUS 文件要求

`docs/architecture/STATUS.md` 应包含：

| 状态 | 含义 |
|------|------|
| `Verified` | 源码存在，并接入 runtime |
| `Partial` | 源码存在，但不完整、被 flag 关闭或未接入 |
| `Deleted` | 曾经存在，现在已删除 |
| `Design` | 只有设计文档，没有实现 |
| `Planned` | 计划中的工作，不是当前行为 |
| `Gap` | 文档声称超过了代码现实 |

任何创建、删除、恢复或显著改变模块的产品本地 coding session，都应更新 `STATUS.md`。

## CLAUDE.md / AGENTS.md 要求

Agent 指令文件应包含：

- 非平凡任务的强制 workflow
- session start 阅读顺序
- quick commands
- architecture entrypoints
- 仓库职责与服务边界
- code conventions
- banned patterns
- verification gate
- Git 和 PR 规则
- 跨产品工作时指向平台文档的链接
- 稳定性优先、产品边界和 UI scope 规则

如果 `CLAUDE.md` 和 `AGENTS.md` 同时存在，两者必须行为等价：

- workflow、Git 规则、验证门禁、安全规则和跨产品边界必须一致。
- 可以针对具体工具增加命令映射或使用提示。
- 不能一个文件要求严格保护用户改动、运行验证、使用 worktree，另一个文件弱化或省略这些要求。
- 更新其中一个文件的行为规则时，必须同步更新另一个文件，或把其中一个明确写成指向 canonical 文件的镜像。

不要在 agent 指令文件中放 secret、客户数据或长历史 changelog。

Agent 指令文件还应让流程可执行，而不只是描述原则。建议包含一段强制 checklist：

1. 阅读本仓库 agent context 和相关共享工程标准
2. 编辑前运行 `git status --short --branch`
3. 非平凡工作使用 topic branch / worktree，并声明 owner 与 scope
4. scope 必须说明 protected primary flow、affected product boundaries 和 UI scope
5. 默认保护主流程；不为未明确要求的功能扩张牺牲稳定性
6. 除非 UI 明确 in-scope，不在后端、队列、部署、MCP、provider、数据模型或测试修复中改 UI
7. 声称完成前运行定向验证，并说明稳定性证据
8. 受保护分支走 PR，并等待 required checks
9. 任务完成或 PR merge 后，回到本地 default branch；如果 checkout clean，则 fetch/prune 并 fast-forward 到 `origin/<default>`
10. 如果 default checkout 有 local-only WIP，默认创建基于 `origin/<default>` 的 clean latest worktree，不隐式覆盖、reset 或宽泛 stash
11. 明确报告仍保留的 local-only WIP，以及仓库是否结束在 clean latest default branch，不把它藏起来

为了更强自动化，产品仓库应加入 PR template 和 branch protection，要求 validation evidence。有本地 `make` 入口的仓库应暴露轻量 `make check` 或 `make agent-check` 命令，供 agents 在打开 PR 前执行。

### 规则放在哪里才守得住

Agent 能稳定重读的只有工具每次 session 都会加载的指令文件。链接出去的指南、长设计文档和之前的对话，在上下文压缩后经常丢失。必须每次都成立的规则，因此只能放在两处之一：

- `CLAUDE.md` / `AGENTS.md` 里一条简短、直接的规则；或
- 规则被违反时会失败的 lint、类型检查或测试。

能机械检查的规则优先用第二种；文字规则在赶工时会输。需要登记的场景（路由、feature flag、UI surface、API client），优先用 registry 加针对 registry 的正向断言，或用脚手架自动生成登记，而不是要求每个新文件记住一个手动步骤。

## 结构化 Authorized Context 规则

自然语言 `AGENTS.md` 与 `CLAUDE.md` 只是面向 Agent 易用性的 projection，不是 enforcement
identity。启用 UI Assurance 后，确定性 enforcement 消费密封的 `CodingTaskManifest`、
不可变 `AuthorizedDevContextSnapshot` 与实际 repository state。

结构化 context 绑定 repository、base revision、worktree、allowed/protected surfaces、
policy、registry、toolchain、dependency lock、admitted waiver、risk floor、validation
categories、classification 与 validity interval。Prompt projection 可以解释这些字段，
但不能覆盖它们。Context 缺失、过期、repository/base 错误或 digest 不匹配时，governed
task 必须停止；不得用 PR prose 静默修复。

## 跨仓库交叉引用规则

参与多仓库协作时，仓库内的 `CLAUDE.md` 或 `AGENTS.md` 应链接组织级共享架构/契约文档，以及适用的 Agentic SDLC 核心标准（`sdlc.zh.md`、`vibe-coding-collaboration.zh.md`、`multi-ai-git-workflow.zh.md`、`testing-strategy.zh.md`，以及适用时的 `ui-assurance/README.zh.md`）。

## Code Health context projection

接入 Code Health candidate contract 的仓库可以在 context 中投影任务所需的当前
component、public-surface、runtime-path、flag、hotspot 和 retirement ID。F2 projection
绑定精确 base/head revision、policy/schema digest、evaluator closure digest 和 candidate
coverage result。Policy 与 baseline bytes 从 exact evaluated tree 读取；product registry
revision 是 provenance，必须是 evaluated revision 的 ancestor。Projection 只用于解释：
actual diff、编译的 obligation、waiver、baseline 和 trusted receipt 仍在 Agent authority
之外。通用 Git/registry metric 可以 evaluated，但 language-specific route、schema、
generated-client、migration、duplicate/dead-code 和任意 plugin adapter 在真实 adapter
接入前必须明确为 `NOT_EVALUATED`。只有 affected closure 允许时才使用聚焦
frontend/backend tests；触及共享 contract 或无法确定/安全/release 边界时，两侧和
browser/API journey 都必须运行。

## 技术债学习闭环

当 AI coding session 发现或修复技术债：

1. 在产品仓库记录或更新 debt item。
2. 如果错误可能重复发生，抽象出 prevention rule。
3. 把 prevention rule 加到产品本地 debt protocol。
4. 只有当规则适用于多个仓库时，才提升到共享工程标准中。

## 批量修复经验与入口维护

强制规则保持简短，AGENTS/CLAUDE 采用一个 canonical 文件与明确指针，避免两份独立维护。
前端任务加载布局/交互规范，后端任务加载执行/事务/兼容规范；编辑器规则引用同一来源，
不再维护另一套硬编码模块清单。

按“失败案例 → 根因 → 适用边界 → 预防规则 → 回归测试 → 当前状态”沉淀。产品实现细节留在
产品指南，跨产品规则提升到共享标准；可机器判断的稳定约束优先变成检查。先扩充现有标准，
再考虑新增文档。新鲜源码/测试与 STATUS 冲突时，应修正文档；旧文字不覆盖实际实现证据。
