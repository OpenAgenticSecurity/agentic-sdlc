# Agent 运维、共享环境与工作区卫生清单

**状态**: accepted baseline
**更新日期**: 2026-11-20
**English**: [agent-ops-and-workspace-hygiene.md](agent-ops-and-workspace-hygiene.md)
**配套脚本**: [`scripts/link-shared-node-deps.mjs`](../scripts/link-shared-node-deps.mjs)

> **为什么需要这份清单**：多 Worktree AI 开发最常在“需求文档里没人写”的运维层悄悄翻车——10 个 worktree 复制出几十 GB 的 `.venv` 与 `node_modules`、嵌套 `fork` 子 Agent 一小时烧穿 2.6 亿 Token、排障脚本 `echo "$TOKEN"` 把真密钥打到终端、Squash 合并删分支把 Stacked PR 自动关掉。下面每一条都来自真实踩坑事故。

---

## 1. 多 Worktree 共享依赖环境（避免磁盘爆掉几十 GB）

在每个任务 worktree 里分别执行 `uv sync`、`pip install` 或 `npm install`，会迅速吃掉几十 GB 磁盘并拖慢每次会话启动。

### 推荐方案

- **Python（`uv`）**：所有 worktree 共用仓库外的一个固定虚拟环境：
  ```bash
  export UV_PROJECT_ENVIRONMENT="$HOME/workspace/.venv"
  ```
  只在主仓库根目录同步一次，绝不在单个 worktree 内重复建 `.venv/`。
- **Node / 前端（`Vite`、`tsc`、`ESLint`）**：**`NODE_PATH` 对 Vite / `tsc` / ESLint 无效**——它们只从本地 `node_modules/` 解析依赖。使用按 lockfile 哈希寻址的外部共享仓脚本 [`scripts/link-shared-node-deps.mjs`](../scripts/link-shared-node-deps.mjs)：
  ```bash
  node /path/to/agentic-sdlc/scripts/link-shared-node-deps.mjs --project-dir ./frontend
  ```
  - 按 `package-lock.json` + `package.json` 依赖字段 + 平台/架构/Node ABI 计算 SHA-256，在外部缓存目录（`~/.cache/shared-node-deps/<hash>/`）一次性原子化 `npm ci`，每个 worktree 内保持真实 `node_modules/` 目录并将各包软链指向共享仓。
  - **单独拷贝 `.package-lock.json`** 而非软链（避免 `npm` 原地改写污染所有 worktree 共享的 store）。
  - `.vite`、`.cache`、`.tmp`、`.turbo`、`.next` 留在各 worktree 本地隔离，且绝不破坏已存在的真实 `node_modules/` 安装。
  - **共享缓存信任边界**：仅在**同一信任域**的本地开发 Worktree 之间共享依赖仓；绝不让互不信任的任务或受保护 Verifier 共用可写依赖仓，处理不受信 lockfile 时建议显式启用 `--read-only-store` 与 `--ignore-scripts`。

### 共享环境的 3 个真实大坑

- [ ] **坑 1 — Worktree 静默跑成主目录旧代码**：新 worktree 里直接运行 `uv run pytest` 时，若 `pytest` 在 dev 依赖中未安装，可能回退到系统 Python 进而加载**主目录 checkout 的旧代码**（静默假绿/假红）。动手前先核对：
  ```bash
  python -c "import your_pkg; print(your_pkg.__file__)"
  ```
  确认输出路径落在**当前 worktree** 内，而不是主目录。
- [ ] **坑 2 — 跨仓共享 venv 被静默降级 + 幽灵 Type Stubs**：在共享 `.venv` 安装某个仓的锁死 `requirements-test.txt` 会静默降级其他仓共用的 `pytest`/`packaging`，多余的 `types-*` 存根还会导致另一仓 `mypy` 误报。优先按 lockfile 分槽，或仅增量安装缺失单包。
- [ ] **坑 3 — 本地 `.env` 污染单测**：开发用 `.env` 中的开关被 `load_dotenv` 吸入 pytest，导致“本地失败、CI 全绿”的伪回归。测试运行应显式隔离环境变量（如 `env -u VAR` / `FLAG=0`）。

---

## 2. 工作区运行暂存（`tmp/`）与安全磁盘回收

把 Agent 产生的日志、长命令输出和临时报告统一放在**业务 Git 仓库外部**的受控暂存目录（如 `<workspace>/.agent-scratch/{logs,tasks}/`），避免污染仓库 `git status` 或误提交。

- [ ] **严禁把密钥、凭据、客户数据或生产 `.env` 写入暂存目录**。
- [ ] **按固定两级目录归档任务暂存（`tasks/<type>/<scope>/<task>/`），并在根目录留一份首行自包含的 `SUMMARY.md`**（第一行写清结论，正文列触及文件/PR 与实跑验证命令），避免后续会话为查内容翻开几十个文件。
- [ ] **清理 `.venv` / `node_modules` / `__pycache__` / `build` / `dist` 的四条安全护栏**：
  1. **绝不递归进入任何 `.git` 仓库内部**（仓内目录可能包含未推送或有价值状态）。
  2. **跳过最近 24 小时内被触碰的目录**，防止把正在运行的 Agent 会话环境删崩。
  3. **先只读审计深埋的 Git 克隆**：删除前按 `RISKY`（脏工作区、未推送 commit、stash、合并中断、无 remote）vs `SAFE` 分类，绝不盲删。
  4. **按内容定性，不按目录名定性**：带随机后缀的 `mktemp` 目录里可能装着唯一一份交付物或敏感凭据。

---

## 3. 周期性审计档案（`audit/` + `EVIDENCE.md`）

将**周期性审计结论**（持久、可跨轮对比的资产，如 `<workspace>/audit/<YYYY-MM-DD>-<topic>/`）与**审计过程物**（抓包日志、脚本原始输出等，放 `tmp/` 随时可清）彻底分离。

- [ ] **严禁把完整仓库副本冻结进审计目录**：每条发现统一用 `file:line` + 完整 40 位 `commit SHA` 锚定。实测对照：用 commit 锚定覆盖 5 个仓库的审计仅占 **240 KB**，而冻结 6 份完整仓库副本占了 **7.8 GB**（相差约 3 万倍），可追溯性毫无增强。
- [ ] **每轮审计必须包含 `EVIDENCE.md`**：写清范围、精确 commit 基线、复核每条结论的可执行命令、已知缺口与下一轮衔接事项——**只有 `EVIDENCE.md` 立得住，才能放心删掉数 GB 的过程临时文件**。
- [ ] **跨轮增量对照**：新一轮审计开始前先读上一轮 `EVIDENCE.md`，明确报告哪些旧发现已 **Closed**、哪些 **Persisting**、哪些是 **New**——无法和上一轮对比的审计，每一轮都在从零重做。

---

## 4. Subagent Token 预算与并发护栏

嵌套 `fork` 子 Agent 会反复继承并重读完整父会话历史（真实事故：14 MB 对话记录被复制重读 8+ 次，**1 小时烧掉 ~2.6 亿 Token**），高并发还会触发 API 中继 `499` 或连接拒绝。

- [ ] **禁用继承全量历史的 `fork` 子 Agent**：每次派发传极简、自包含 Prompt（绝对 worktree 路径、分支、文件清单、验证命令、完成标准、禁止项），绝不粘贴历史聊天。
- [ ] **禁止子 Agent 嵌套再派子 Agent**：在子 Agent Prompt 中显式写明禁止再调用 Agent/Task 工具。
- [ ] **限制并发数（`<=3`）**：单 Agent 串行能很快做完的小改动不要硬拆并行；要求子 Agent 汇报精简结构化。
- [ ] **长会话与跨层切换主动交接**：上下文膨胀或在前端/后端/兄弟仓之间切换时，按 [`handoff.template.md`](handoff.template.md) 写一份精简 `HANDOFF.md`（目标、已完成、剩余、API/Schema/配置契约变更、验证命令），开全新会话继续。
- [ ] **跨仓改动按依赖顺序推进**：先合入共享协议与底层库，再合入消费方服务，最后同步平台规范，确保下游验证基于已落地的真实契约。

---

## 5. 六条高频排障、Git 与门禁运维陷阱

- [ ] **排障绝不回显密钥明文**：检查环境变量只测存在性（`[ -n "${API_TOKEN:-}" ] && echo present` 或 `env | cut -d= -f1`），绝不运行 `echo "$API_TOKEN"` 或 `env | grep TOKEN`（终端泄密只能立刻吊销重签）；隔离环境直接用 `env -u VAR`。
- [ ] **警惕异常信息泄漏密封数据**：当脚本处理受限/密封数据时，连 `urlsplit ValueError` 都可能把原文片段带到 stdout。对 Agent 可见的 stdout **只打印聚合计数与异常类名**，完整堆栈落不可读日志，测试只用合成数据。
- [ ] **Squash 合并仓库禁用 GitHub Stacked PR Base**：PR #1 用 squash 合并并自动删分支时，GitHub 会**自动关闭**以它为 base 的 PR #2，且已关闭 PR 无法 `gh pr edit --base main`。拆分 PR 一律以 `main` 为 base，PR #1 合并后本地 `git fetch` + `cherry-pick`/rebase 再推 PR #2。
- [ ] **核验已提交对象，不只核验工作树**：先 `git add` 后重新生成 digest/bundle，本地 `make check` 读工作树全绿，推上去 CI 读 `HEAD` 直接全挂。关键产物用 `git show HEAD:<path>` 且在 `git status` 干净时复验。
- [ ] **绝不拿压缩/过滤型 CLI 包装器的输出当事实计数**：过滤日志的包装工具（如把 2,113 条提交截成 50 行的 `git log | wc -l`）会静默扭曲审计数字。需要精确计数一律用原生精确命令（如 `git rev-list --count HEAD`）。
- [ ] **门禁放宽不对称原则与游标后置**：
  - **绝不对“放宽安全/鉴权门禁”的 PR 走 admin-bypass**；对要求独立审批才生效的计划 PR 也绝不走 bypass（否则直接作废计划并陷入无限重跑死循环）。
  - 在轮询/消费循环中，**只在下游副作用成功后再推进去重游标**，绝不只因解析成功就推进（宁可幂等重试，绝不静默丢事件）。
