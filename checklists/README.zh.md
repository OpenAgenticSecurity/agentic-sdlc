# 实证排雷清单与证据模板（Empirical Checklists & Templates）

**状态**: accepted baseline
**更新日期**: 2026-11-20
**English**: [README.md](README.md)

本目录将累计 **2000+ 亿 Token** 真实多仓 AI 辅助工程实践中的专项实证数据（443 次会话 / 84 亿 Token 样本集、24→2 条 AI Review 取证复盘、454 个真实前端缺陷、100+ 项后端性能事故，完整汇总见 [实证发现](../docs/empirical-findings.zh.md)）沉淀为可直接贴进 PR 模板、Code Review 与验收门禁的检查清单与模板。

这些清单与权威规范 [standards/](../standards/README.zh.md) 以及 [scripts/](../scripts/) 中的确定性校验器配套使用。

## 清单与模板总览

| 清单 / 模板 | 实证依据 | 适用环节与等级 | 原文参考 |
|---|---|---|---|
| [vibe-coding-seven-sins.zh.md](vibe-coding-seven-sins.zh.md) ([English](vibe-coding-seven-sins.md)) | 443 次会话、84 亿 Token、3 类失败原型、相变临界点（`<5K` vs `>10K` LOC）、七宗罪 | 会话边界管理、Plan-then-Do、重构防漂移（`L0`–`L1`） | [Vibe Coding 生存指南](https://fz.cool/vibe-coding-complete-guide/) |
| [secure-vibe-coding-review.zh.md](secure-vibe-coding-review.zh.md) ([English](secure-vibe-coding-review.md)) | 真实安全审计、密码学运营实践与 AI 生成代码高发漏洞 | 安全代码审查、反向安全单测（`L0`–`L2`） | [密码学运营必知必会](https://fz.cool/Applied-Cryptography-Operation-Must-Knowns/)、[Secure Vibe Coding 标准](../standards/secure-vibe-coding.zh.md) |
| [multi-agent-git-gates.zh.md](multi-agent-git-gates.zh.md) ([English](multi-agent-git-gates.md)) | Cursor + Claude Code + Codex 并发多仓协作、四类 Owner 拆分 | 编辑前/提交前/PR 前三道关卡、破坏性动作刹车（`L0`–`L1`） | [多 Agent 协作时代的 Git 规范](https://fz.cool/Multi-Agent-Git-Workflow/) |
| [fake-done-dereference.zh.md](fake-done-dereference.zh.md) ([English](fake-done-dereference.md)) | 24→2 条 Review 复盘、15/15→0/15 旧门禁漂移、43→29 反证复核、4 个解引用断点 | 交付验收、安全审计、运行时回读（`L1`–`L2`） | [Agentic Assurance Engineering](https://fz.cool/agentic-software-engineering-real-sdlc/)、[假完成的验证断点](https://fz.cool/agentic-fake-done-breakpoints/) |
| [done-claim.template.md](done-claim.template.md) 与 [done-claim.example.json](done-claim.example.json) | 7 元组 `DoneClaim` + 合法非绿状态机 + `does_not_prove[]` | PR 说明、任务交接、发布签字（`L0`–`L2`） | [假完成的验证断点](https://fz.cool/agentic-fake-done-breakpoints/) |
| [frontend-vibe-coding-review.zh.md](frontend-vibe-coding-review.zh.md) ([English](frontend-vibe-coding-review.md)) | 454 个真实前端问题；前 4 类成因占 84%；CI/单测仅发现 7% | 前端 PR 审查、浏览器巡检、UI 门禁设计（`L0`–`L2`） | [Vibe Coding 的前端生死体验](https://fz.cool/vibe-coding-issues-in-frontend/) |
| [backend-performance-review.zh.md](backend-performance-review.zh.md) ([English](backend-performance-review.md)) | 38 万行后端 100+ 项性能修复；主动发现仅 16%，CI 发现仅 5% | 后端 PR 审查、P99 尾部压测、Agent 循环预算（`L1`–`L2`） | [Vibe Coding 应用性能：能跑和扛得住](https://fz.cool/vibe-coding-backend-performance/) |
| [agent-ops-and-workspace-hygiene.zh.md](agent-ops-and-workspace-hygiene.zh.md) ([English](agent-ops-and-workspace-hygiene.md)) | 多 Worktree 共享依赖三大真坑、2.6 亿 Token 熔断、`tmp/` 与 `audit/EVIDENCE.md`、Stacked PR 陷阱 | 多 Worktree 运维、子 Agent 成本控制、周期审计（`L0`–`L2`） | [`scripts/link-shared-node-deps.mjs`](../scripts/link-shared-node-deps.mjs) 与真实多仓运维复盘 |
| [production-readiness-audit.zh.md](production-readiness-audit.zh.md) ([English](production-readiness-audit.md)) | 五维整仓实现审计、7 条证据纪律、三层默认值、数据活性与 H1/H2 生产 vs Demo 裁决 | 上线前整仓审计、生产就绪度判定（`L1`–`L2`） | [`skills/audit-production-readiness/SKILL.md`](../skills/audit-production-readiness/SKILL.md) |
| [handoff.template.md](handoff.template.md) | 跨会话 / 跨前后端 API、Schema 与三层配置契约交接单 | 60 条消息压缩前交接、前后端/跨仓切换（`L0`–`L2`） | [`skills/multi-agent-git-flow/SKILL.md`](../skills/multi-agent-git-flow/SKILL.md) |

## 升级铁律

Checklist 能快速堵住人和 Agent 的盲区，但纯文本规则扛不住长会话与上下文压缩。**只要同一类根因第二次出现，就必须把它从 Checklist 升级成确定性门禁**（Schema、Lint 规则、查询预算测试、契约测试或 required status check），并故意植入一条违规反例，证明门禁真的会变红且能拦住合并。
