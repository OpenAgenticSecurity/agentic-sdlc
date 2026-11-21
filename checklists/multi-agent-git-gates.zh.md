# 多 Agent Git 与 Worktree 三道关卡清单

**状态**: accepted baseline
**更新日期**: 2026-11-20
**English**: [multi-agent-git-gates.md](multi-agent-git-gates.md)
**实证来源**: [《多 Agent 协作时代的 Git 规范》](https://fz.cool/Multi-Agent-Git-Workflow/)、[《Agentic Assurance Engineering》](https://fz.cool/agentic-software-engineering-real-sdlc/)
**权威规范与 CLI**: [standards/multi-ai-git-workflow.zh.md](../standards/multi-ai-git-workflow.zh.md)、[`scripts/workspace-git.py`](../scripts/workspace-git.py)、[`scripts/agent-claim.py`](../scripts/agent-claim.py)

> **核心原则**：AI 写代码越快，破坏性 Git 动作就越必须放慢，责任边界就越必须清晰。**一个任务 = 一个 branch + 一个 worktree + 一位活跃 writer + 一份明确 scope**。

---

## 1. 先把模糊的 “Owner” 拆成四个独立问题

| 问题 | 工程载体 |
|---|---|
| 谁决定目标、共享事实与优先级？ | 权威文档、ADR、Task Issue Owner |
| 谁批准这一类变更？ | `CODEOWNERS`、分支/Ruleset 保护、Reviewer 规则 |
| 谁此刻拥有该 branch/path 的写入权？ | 活跃 Managed Issue Claim、租约、分支、隔离 Worktree |
| 谁实际执行了动作？ | Automation identity、GitHub actor、Agent/session、事件溯源 |

## 2. 启动任意 Agent 前的最小任务契约

| 字段 | 示例 |
|---|---|
| `branch` | `fix/auth-rotate-key` |
| `owned_paths` | `src/auth/`、`tests/auth/` |
| `out_of_scope` | `src/billing/`、`migrations/` |
| `test_command` | `pytest tests/auth -x` |
| `can_commit` / `can_push` | `yes` / `no` |
| `dependencies` | `#1024`（需在其合并后再启动） |

- [ ] 并发多 Agent 动手前，用 `python3 scripts/agent-claim.py check-overlap ...` 确认 `owned_paths` **完全不重叠**。
- [ ] 谨记：`git worktree` 只隔离 Git checkout / index / branch / WIP，**不隔离** OS 权限、网络、环境变量与密钥。

## 3. 三道必过关卡

### 关卡一：编辑前（绝不在 `main` 或脏默认 checkout 上直接开发）

```bash
git fetch origin --prune
git status --short --branch
git branch -vv
git rev-list --left-right --count HEAD...origin/main
git worktree add .worktrees/<task-name> -b <type>/<topic> origin/main
```

- [ ] 本地安全配置到位：`pull.rebase=true`、`pull.ff=only`、`branch.main.rebase=false`。
- [ ] worktree 目录已加入 `.git/info/exclude`（`.worktrees/`、`.claude/worktrees/`、`.cursor/worktrees/`、`.codex/worktrees/`）。
- [ ] 固定阅读顺序：`AGENTS.md` / `CLAUDE.md` → `STATUS.md`（实现现实单一事实源）→ `VIBE_CODING_CONTEXT.md` → 跨仓权威文档 → 当前 Issue/Claim → 远端 Git 状态。

### 关卡二：Commit 前（范围与整洁度核对）

```bash
git status --short
git diff --stat
git diff --check
git diff --name-only
git diff --cached --name-only
```

- [ ] 所有 staged 文件都在 `owned_paths` 范围内（零越界“顺手重构”）。
- [ ] `git diff --check` 无空白/格式错误，零密钥、零本机绝对路径。

### 关卡三：PR 前（小到人类 Reviewer 真正能读完）

```bash
git fetch origin --prune
git log --oneline origin/main..HEAD
git diff --name-only origin/main...HEAD
git diff --check
```

- [ ] PR 描述完整写明：改动摘要、依赖 PR 与合并顺序、**实际运行过的验证命令**与新鲜结果、执行 Agent/工具与 Owner、回滚路径。
- [ ] 跨仓改动按显式依赖拓扑依次推进：共享契约 → 向后兼容的 producer/consumer → 集成回放 → 文档索引与清理。

## 4. 破坏性 Git 动作“慢动作刹车表”

| 动作 | 风险 | 执行前必须完成的刹车动作 |
|---|---|---|
| `git stash` | 把别人或另一个 Agent 的未提交改动藏起来 | 先跑 `git status --short`、`git diff --stat`、`git worktree list` 确认 100% 归属 |
| `git reset --hard` | 永久丢失未提交本地工作 | 先建 `backup/<topic>-<date>` 分支或已核实 stash，并经人类显式确认 |
| `git push --force` | 覆盖远端评审历史或他人提交 | 确认分支 Owner、保留备份分支/Tag，并经人类显式确认 |
| 删除 branch | 丢失 Review 上下文或未合并提交 | 确认无 open PR 依赖且有效提交已合并 |
| 删除 worktree | 丢失本地未推送工作 | 通过下方 5 项全检——**不确定一律保留** |

## 5. 删除 Worktree 前五项全检

只有**全部五项**确认通过才允许删除 worktree：

```bash
git status --short                              # 1. 工作区完全干净
git branch -vv                                  # 2. 无未推送 commits
git worktree list                               # 3. 确认无人/无活跃会话正在使用
gh pr list --state open --head <branch-name>    # 4. 无 open PR 依赖该分支
git log --oneline origin/main..<branch-name>    # 5. 所有有价值 commits 已 push 或 merge
```
