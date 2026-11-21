# 多人多 AI Git 工作流标准

**状态**: accepted baseline
**更新日期**: 2026-11-20

## 目标

当多个工程师和多个 AI coding tools 同时工作时，本标准用于保持 `main` 稳定，并保持 PR 可评审。

## 核心规则

1. `main` 是 integration branch，不是开发工作区。
2. 一个任务必须绑定一个 branch、一个 worktree、一个 owner 和一份明确 scope。
3. scope 必须说明 in-scope 文件/模块、out-of-scope 文件/模块、验证命令和依赖。
4. 一个 branch 同一时间只有一个 owner。
5. 不同 AI tools 不得 push 到同一个 branch。
6. PR 必须足够小，能被评审。
7. 每个 PR 描述必须包含验证证据。
8. 破坏性 Git 命令需要明确人工确认。
9. 存放多个独立仓库的 workspace 根目录不应初始化为 Git 仓库，除非明确设计成 meta-repo。
10. 新任务 worktree 必须基于 `origin/<default>`，即使本地 default checkout 是 clean 的。
11. 绑定 GitHub issue 的实现工作，必须在编辑代码前发布 managed issue claim comment。

## Pull Policy

推荐产品仓库配置：

```bash
git config pull.rebase true
git config pull.ff only
git config branch.main.rebase false
```

含义：

- `main` 只允许 fast-forward。
- 非共享 feature branch 可以 rebase 到最新 `origin/main`。
- 共享 branch rebase 前必须协调。

## Worktree 布局

每个 AI tool 应使用自己的 worktree namespace：

```text
repo/
  .claude/worktrees/
  .cursor/worktrees/
  .worktrees/              # Codex 或通用 worktrees
```

本地 worktree 目录应通过仓库 `.gitignore` 或 `.git/info/exclude` 忽略：

```gitignore
.worktrees/
worktrees/
.claude/worktrees/
.cursor/worktrees/
```

## 分支命名

推荐模式：

```text
docs/<topic>
feat/<topic>
fix/<topic>
chore/<topic>
test/<topic>
audit/<topic>
plan/<topic>
release/<topic>
batch/<topic>
merge/<topic>
backup/<topic>-<date>
```

共享 PR 分支名必须表达工作内容，不表达工具来源。不要把 `codex/`、
`claude/`、`cursor/` 作为正常 PR 分支前缀；agent/tool 归属应写入 PR
描述、handoff 报告、任务记录或 branch owner 字段。

`codex/`、`claude/`、`cursor/` 只允许作为本地临时隔离分支命名空间使用，
并且默认不推送、不打开 PR。若临时分支要进入共享流程，先重命名为
`docs/`、`feat/`、`fix/` 等语义前缀。

避免 `update`、`fixes`、`wip`、`test`、`new-code` 这类模糊名称。

## 开始工作

AI tool 编辑前：

```bash
git fetch origin --prune
git status --short --branch
git rev-list --left-right --count HEAD...@{u}
```

如果 default branch checkout 是 clean 且只落后 remote，先 fast-forward：

```bash
git merge --ff-only @{u}
```

如果 default branch checkout 有未提交内容，不要直接 pull 或 reset。默认创建基于最新 remote 的 clean worktree：

```bash
git worktree add .worktrees/<task-name> -b <branch-name> origin/<default>
```

进入 worktree 后：

```bash
git status --short --branch
git branch -vv
```

开始状态必须是 clean。

该规则同样适用于 PR merge 后或跨仓库同步后准备继续开发的场景：主 default checkout
在安全时应保持 clean/latest，但任务 worktree 仍从 `origin/<default>` 创建。如果当前主
checkout 被本地 WIP 或另一个 agent 阻塞，使用 clean latest worktree 继续，而不是隐式
stash、覆盖或重置主 checkout。

在多仓库工作区中，可使用本仓库内置 helper：

```bash
python3 scripts/workspace-git.py audit --root /path/to/workspace --all-repos --fetch
python3 scripts/workspace-git.py clean-defaults --root /path/to/workspace --all-repos --no-fetch --occupied <active-repo>
python3 scripts/workspace-git.py agent-start --root /path/to/workspace --repo <repo> --task <task-name> --branch <branch-name> --create-worktree
```

`workspace-git.py clean-defaults` 默认只做 dry-run。只有在已列出 occupied repositories，且 dry-run 输出证明某个 checkout 可以在不 switch、不 stash、不 reset、不触碰 local WIP 的情况下 fast-forward 时，才传入 `--apply`。

## 任务分配契约

每个 AI 工作分配必须包含：

- branch name
- worktree path
- owner
- owned files or directories
- out-of-scope files or directories
- expected test command
- AI 是否可以 commit
- AI 是否可以 push
- dependency PRs or branches

## Issue Claim Comments

当任务绑定 GitHub issue 时，负责的人类或 AI agent 必须在编辑代码前发布一条
managed issue comment。Issue body 是稳定 scope 记录；动态协作状态必须放在
comments 中。

该规则适用于本地 Codex session、Claude Code session、Cursor session 以及
CI/自动化机器人任务。即使这些 agent 共用同一个 GitHub actor，也必须发布
managed comment。

managed comment 必须包含：

- automation identity 和 GitHub actor
- agent/tool 和 session id
- repo、branch、worktree 和 owned paths
- out-of-scope paths、affected contracts 和 dependencies
- lease 或 heartbeat timestamp
- next action，以及关联 PR 或 handoff 状态

对简单本地 session，最低必需字段是：marker、status、automation identity、
GitHub actor、agent、session id、task id、repo、branch、适用时的 worktree、
claim issue、owned paths、updated timestamp、活跃工作所需的 lease expiry、
current summary 和 next action。PR URL、out-of-scope paths、affected contracts
和 dependencies 在不存在时可以暂时为空，但 comment 应显式写 `TBD`、`none`
或 `-`，不要静默省略。

使用隐藏 marker，方便工具更新同一条 comment，避免重复刷屏：

```text
<!-- agent-claim:<owner/repo#number>:<task-id> -->
```

`task-id` 表示同一个 owner 在同一个 branch 上的一次实现尝试。默认格式是
lowercase kebab-case `<scope>-<YYYYMMDD>`，例如 `model-route-20260625` 或
`api-w1-consume-route-20260625`。同一 owner 恢复同一 branch 或更新同一
PR 时，继续复用同一个 `task-id`。当 owner 转移、branch 改变、原 branch
放弃，或失败后开始新的实现尝试时，生成新的 `task-id`。handoff 时，原 owner
应把旧 claim 置为 `released`、`blocked`、`failed` 或 `waiting_review`；新
owner 发布新的 claim comment，并在 summary 里引用旧 `task-id` 或 PR。
自动化队列生成的持久 queue id 只有在队列本身已经保证唯一、且 issue comment
仍记录 branch 和 session 时，才可以省略日期。

managed comment 状态应按以下生命周期流转：

| Status | 含义 |
|--------|------|
| `claimed` | owner 在编辑前预留 issue scope。 |
| `running` | 正在实现、验证或更新 PR。 |
| `waiting_review` | PR 或 handoff 已就绪，agent 不再编辑该 branch。 |
| `blocked` | 缺少明确依赖或人工决策，无法继续。 |
| `completed` | 验收标准已满足，关联 PR 或证据完整。 |
| `released` | agent 主动释放 claim，但未完成任务。 |
| `failed` | 尝试已放弃，并附带具体失败证据。 |

活跃工作用 `heartbeat` 更新；终态交接用 `release` 更新。过期 comments
可以保留在 timeline 中，但其他 agent 接手前应检查对应 branch/worktree。

当 lease 已过期，且没有 PR、check 或运行证据表明当前仍在活动时，claim
视为 stale。不要删除 stale comments。若原 owner 仍可更新，应把同一条
managed comment 更新为 `released`、`blocked` 或 `failed`；否则新 owner
发布新的 managed comment，并说明为什么上一条 claim 已 stale。

并发 claim 按 scope 处理，而不是只按 comment 时间先后处理。如果两个 active
claims 在同一仓库声明了重叠 owned paths，两个 agents 都必须停止编辑，直到重叠
范围只保留一个 owner。尚未开始改代码的一方应先释放 claim。如果双方都有本地
变更，保留两个 worktrees，并请 human/product owner 指定单一 owner，然后才能
push 或 rebase 任一 branch。如果两个 claim 绑定同一个 issue 但 owned paths
不重叠，只有在各自 comment 明确列出 owned paths 和 out-of-scope paths 时，
双方才可以继续。

如果 agent 异常退出且无法释放 claim，新 owner 只有在记录旧 claim 为什么 stale
之后才能接手：lease 已过期、没有新的 PR/check/run 活动，并且在可访问时已检查
branch 或 worktree 状态。接手 comment 必须使用新的 `task-id`，引用旧 `task-id`
或 PR，并在 `Current summary` 写明恢复原因。除非原 owner 或仓库 maintainer
明确关闭 stale attempt，否则不要编辑、删除或重写旧 comment。

不要把 owner、heartbeat、branch、PR 或 handoff 这类易变状态写进 issue
body。Issue body 只保存稳定 scope、验收标准、验证计划、依赖和 canonical
plans 链接。

本仓库提供独立参考脚本（`scripts/agent-claim.py`）：

```bash
python3 scripts/agent-claim.py render \
  --issue '<owner/repo#number>' \
  --task <task-id> \
  --status running \
  --identity 'Claude Code' \
  --actor <github-handle> \
  --agent <claude-code|codex|cursor> \
  --session <session-id> \
  --repo <repo> \
  --branch <branch> \
  --worktree .claude/worktrees/<task> \
  --lease-expires 2026-11-20T18:00:00Z \
  --owned-path <path> \
  --output claim.md

python3 scripts/agent-claim.py check-overlap claim.md other-claim.md
python3 scripts/agent-claim.py publish claim.md
```

等价 comment 遵循以下标准格式（见 `profiles/L1-team/issue-claim.example.md`）：

```markdown
<!-- agent-claim:org/service#42:auth-guard-20261120 -->

### Agent Claim

- Status: `running`
- Automation identity: `Claude Code`
- GitHub actor: `alice`
- Agent: `claude-code`
- Session: `claude-20261120-a`
- Task: `auth-guard-20261120`
- Repo: `service`
- Branch: `fix/auth-guard`
- Worktree: `.claude/worktrees/auth-guard`
- Claim issue: `org/service#42`
- PR: `none`
- Lease expires: `2026-11-20T18:00:00Z`
- Updated: `2026-11-20T16:00:00Z`

Owned paths:
- `src/auth/guard.py`
- `tests/test_auth_guard.py`

Out of scope:
- `frontend/`

Dependencies:
- `none`

Current summary:
Implementing fail-closed token audience check with negative mutation tests.

Next action:
Run make agent-check and open PR linked to org/service#42.
```

不通过 `scripts/agent-claim.py` 更新时，应先找到包含该 marker 的已有 comment，并 patch
那条 comment，而不是再发一条新的。直接使用 `gh api` 的更新路径如下：

```bash
ISSUE_REPO="org/service"
ISSUE_NUMBER="42"
TASK_ID="auth-guard-20261120"
MARKER="<!-- agent-claim:${ISSUE_REPO}#${ISSUE_NUMBER}:${TASK_ID} -->"
BODY_FILE="claim.md"

COMMENT_ID="$(
  MARKER="$MARKER" gh api "repos/${ISSUE_REPO}/issues/${ISSUE_NUMBER}/comments" |
    python3 -c 'import json, os, sys
marker = os.environ["MARKER"]
comments = json.load(sys.stdin)
print(next((str(c["id"]) for c in comments if marker in (c.get("body") or "")), ""))'
)"

if [ -n "$COMMENT_ID" ]; then
  gh api "repos/${ISSUE_REPO}/issues/comments/${COMMENT_ID}" \
    --method PATCH \
    -f "body=$(cat "$BODY_FILE")"
else
  gh issue comment "$ISSUE_NUMBER" --repo "$ISSUE_REPO" --body-file "$BODY_FILE"
fi
```

推广规则：新的 issue-backed 实现工作必须在编辑前发布 managed comment。已有
open work 应在下一次 heartbeat、PR update、review response 或 handoff 时补充
或刷新 managed comment。不要仅仅因为一个旧 PR 早于本规则就阻塞它合并；但当
活跃 owner 不清楚且需要继续编辑时，必须先补 claim comment。

## 开发检查点

开发过程中运行：

```bash
git status --short
git diff --stat
git diff --check
```

commit 前检查：

```bash
git diff --name-only
git diff --cached --name-only
```

不要提交 generated caches、本地 license archives、本地 worktree folders、debug-only compose overrides、无关 roadmap/status edits。

如果发现无关变更，应拆到另一个 branch，或用清晰 message 暂存到 stash。不要用 stash 把 PR 的 review noise 藏起来。

## 未提交变更处理

sync、reset、删除 worktree 或切换 owner 前，先检查：

```bash
git status --short
git diff --stat
git diff --name-only
```

如果变更有价值但还不适合 commit：

```bash
git stash push -u -m "wip/<scope>-before-sync-<date>"
```

如果变更可能属于另一个 AI tool，先停止并识别 owner：

```bash
git worktree list
git branch -vv
```

如果同一个文件被多个 agent 修改，先指定单一 owner，再继续。

## Main 分叉处理 SOP

当本地 `main` 和 `origin/main` 分叉，或集成期间 `origin/main` 前进时，使用此流程：

1. 诊断：

```bash
git fetch origin --prune
git status --short --branch
git rev-list --left-right --count main...origin/main
git log --oneline origin/main..main
git log --oneline main..origin/main
```

2. 创建隔离集成 worktree：

```bash
git worktree add .worktrees/<task-name> -b merge/<task-name> origin/main
```

3. 合并目标 branch，但先不提交：

```bash
git merge --no-ff --no-commit <feature-branch>
```

4. 只解决当前任务相关冲突。

5. 验证：

```bash
git diff --check
```

再运行本次变更的定向产品测试。

6. 如果 `origin/main` 再次前进，把集成 worktree reset 到最新 `origin/main`，重放 merge，并重新验证。

7. 必要时保留旧本地状态：

```bash
git branch backup/main-before-sync-<date> <old-main-sha>
```

8. 只有验证和人工确认后才 push。

默认不 force push。Force 只能作为明确评审过的历史修复动作。

## PR 要求

每个 PR 应包含：

```markdown
## Summary
- what changed

## Dependency
- dependency PRs, branches, or versions

## Test Plan
- [x] command actually run

## Risk / Rollback
- risk and rollback path
```

打开 PR 前：

```bash
git fetch origin --prune
git log --oneline origin/main..HEAD
git diff --name-only origin/main...HEAD
git diff --check
```

## Agent 自动遵循模型

流程应该通过五层机制约束，让人类和 AI agents 默认遵循，而不是依赖记忆：

1. **仓库入口**：每个产品仓库的 `AGENTS.md` 和 `CLAUDE.md` 如果同时存在，必须行为等价，并与本标准保持一致，包含启动阅读顺序、Git 规则、验证门禁和 PR 后同步规则。不能一个严格、另一个弱化。
2. **仓库卫生**：`.gitignore` 忽略本地 worktree 命名空间和生成型本地状态，让 review noise 在 PR 前就暴露出来。
3. **PR 契约**：PR template 和 branch protection 要求 summary、dependency、validation evidence、risk/rollback，以及 checks 通过后才能合并。
4. **自动化检查**：CI 或本地 `make check` 类命令检查文档链接、必填元数据和产品测试；agents 必须报告实际运行过的精确命令。
5. **Workspace preflight**：在多仓工作区中，跨仓库工作前应运行 `scripts/workspace-git.py audit --all-repos`，编辑仓库前应运行 `scripts/workspace-git.py agent-start`。被其他 agent 占用的仓库必须通过 `--occupied` 传给清理命令。

当任务跨多个仓库时，agent 应按依赖顺序创建或更新 PR，等待 required checks，通过受保护分支合并，然后让每个被触及仓库回到 clean latest default branch，再报告完成。如果某个 default checkout 因 local-only WIP 无法安全同步，agent 应创建或指向一个基于 `origin/<default>` 的 clean latest worktree，并明确报告原 checkout 未能回到 default 的原因。交接报告必须包含真实 PR URL、merge 状态、本地同步状态，以及每个被触及 repo 是否结束在 clean latest default branch，避免 owner 反复追问 PR 是否存在、是否已合并、本地 checkout 是否已经最新。

## 跨仓库和 Submodule 规则

跨仓库工作必须按依赖顺序 merge：

1. dependency repository PRs
2. product repository integration PRs
3. documentation index or release notes
4. cleanup branches

涉及 submodule pointer 变更时：

1. 先在 submodule 内 commit
2. push submodule branch
3. 打开并 merge submodule PR
4. 保留 parent repo 引用的 commit SHA
5. 更新 parent repository pointer
6. 打开并 merge parent repository PR

merge parent PR 前确认：

```bash
git submodule status <submodule-path>
git -C <submodule-path> rev-parse HEAD
git ls-tree HEAD <submodule-path>
```

如果 parent repo 指向某个 dependency commit，不要用会让该 commit 不可达或难以理解的 squash 方式合并 dependency PR。

## Merge 后清理

任务完成或 PR merge 后，默认习惯是让仓库回到 clean latest default branch：

```bash
git fetch --prune origin
git switch main
git status --short --branch
git rev-list --left-right --count main...origin/main
git merge --ff-only origin/main
git status --short --branch
git branch --merged main
git worktree list
```

默认分支是 `master` 的仓库使用 `master` 和 `origin/master`。如果存在未提交本地工作，只有在确认改动属于当前 agent 且范围小、机械时才用命名 stash 临时保存；否则保留原 checkout，并从 `origin/<default>` 创建 clean latest worktree 继续。

只有在以下条件满足时，才删除本地 branch：

- PR 已 merge 或明确 abandoned
- branch 没有有价值的未合并 commits
- 没有 worktree 仍在使用该 branch

backup branch 删除前必须确认其内容已经不再需要。

## AI Session 退出时的 Worktree 删除策略

如果 AI tool 在 session 结束时询问是否删除 worktree，默认保留，除非任务已经完成且状态已被保存。

删除 worktree 前确认：

```bash
git status --short
git branch -vv
git worktree list
gh pr list --state open --head <branch-name>
git log --oneline origin/main..<branch-name>
```

只有在以下条件全部满足时，才安全删除 worktree：

- worktree 是 clean 的
- 有价值的 commits 已 push、merge 或明确 abandoned
- 没有 open PR 仍需要该 worktree 的修改
- 没有人类或 AI tool 正在使用
- dependency branch 或 submodule work 已 merge 或已在别处保存

不确定时保留 worktree。保留 review context 比清理本地磁盘更重要。

## AI Tool 安全检查清单

AI tool 编辑前：

- [ ] 位于专用 worktree
- [ ] 不在 `main`
- [ ] branch 基于预期 base branch
- [ ] 已知道 owned files
- [ ] 已知道 out-of-scope files
- [ ] worktree 是 clean 的

AI tool commit 前：

- [ ] `git diff --name-only` 只包含预期文件
- [ ] `git diff --check` 通过
- [ ] 已运行相关 tests 或 docs checks
- [ ] commit message 描述一个逻辑变更

AI tool 打开 PR 前：

- [ ] `git log origin/main..HEAD` 只显示预期 commits
- [ ] PR body 包含 dependencies 和 verification evidence
- [ ] 未引入 customer-unsafe debug defaults
- [ ] submodule pointers 指向已 push 的 commits
