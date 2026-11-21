# 2 分钟接入指南：将 Agentic SDLC 落地到你的 GitHub 与 Coding Agent

**更新日期**: 2026-11-20
**English**: [BOOTSTRAP.md](BOOTSTRAP.md)

你**不需要**安装任何框架或 Python CLI 包即可使用 `OpenAgenticSecurity/agentic-sdlc`。想先看清你当前仓库到底缺什么护栏、存在哪些安全盲区？先跑一遍零依赖只读自检：

```bash
python3 /path/to/agentic-sdlc/scripts/audit-repo.py /path/to/your-repo [--github]
```

随后选择下方任意一种 2 分钟 Bootstrap 方式，再把 GitHub 与你的 Coding Agent 接好即可直接运转。

---

## 先选你的起步档位

| 档位 | 适用场景 | 耗时 | 落地内容 |
|---|---|---|---|
| **`L0`**（`profiles/L0-solo/`） | 个人开发或小仓库 | ~5 分钟 | `AGENTS.md`、`CLAUDE.md`（镜像）、`docs/architecture/STATUS.md`、`docs/VIBE_CODING_CONTEXT.md`、`.github/pull_request_template.md`、worktree `.gitignore` 规则、Fail-Closed 的 `make agent-check` 入口 |
| **`L1`**（`profiles/L1-team/`） | 多人或多 Agent 并行协作 | ~20 分钟 | 包含 `L0` + `.github/ISSUE_TEMPLATE/`、`.github/workflows/candidate-gates.yml`（通用版，或用 `--ci` 选 Python / Node-TS / Rust / Go / Java 模板）、Managed Issue Claim 协作协议 |
| **`L2`**（`profiles/L2-governed/`） | 高安全保证 / 受治理工程 | ~1 小时 | 包含 `L1` + 门禁表面 `.github/CODEOWNERS`、`ruleset-policy.json`、独立机制审查清单、GitHub Ruleset 防自证体检 |

---

## 方式一：零安装 AI Bootstrap Prompt（最快，直接让你的 Coding Agent 帮你接入）

在你的目标仓库切出一个干净的分支或 worktree，把下面这段 Prompt 直接贴给 Claude Code / Cursor / Codex：

```text
请参考 OpenAgenticSecurity/agentic-sdlc（档位：L0，按需可改为 L1 或 L2）为当前仓库完成 Agentic SDLC 初始化。

参考来源：
- 本地克隆路径 /path/to/agentic-sdlc（或 https://github.com/OpenAgenticSecurity/agentic-sdlc）
- 阅读 `profiles/L0-solo/`（如需更高级别再读 `L1-team/` / `L2-governed/`）。

硬性要求：
1. 先检查当前仓库的真实技术栈（package.json、pyproject.toml、Cargo.toml、go.mod、Makefile、.github/workflows/、已有 AGENTS.md/CLAUDE.md）。
2. 绝不静默覆盖已有文件；若目标文件已存在，只输出最小合并建议。
3. 将 `AGENTS.md`、`CLAUDE.md`、`docs/VIBE_CODING_CONTEXT.md` 和 `docs/architecture/STATUS.md` 填成当前仓库真实存在的入口与真实可运行的检查命令——禁止编造命令或遗留占位符。
4. 如 `.gitignore` 尚未忽略多工具 worktree 目录，追加 `.worktrees/`、`.claude/worktrees/`、`.cursor/worktrees/`、`.codex/worktrees/`。
5. 保持 `AGENTS.md` 与 `CLAUDE.md` 行为等价。
6. 实际跑一遍当前仓库的验证命令，报告精确命令和退出码。
```

### Bootstrap 后必做的 4 项人工核对

绝不盲信 Agent 生成的初始化文件：
1. 亲自执行 `AGENTS.md` 里写下的验证命令（如 `make agent-check`），确认它会真实跑测试，且故意弄坏一条测试时会变红（不是 `0 tests collected` 或绿色 `skip`）。
2. 检查 `docs/architecture/STATUS.md`，确认每条标为 `Verified` 的模块在源码中真实存在。
3. 确认 `AGENTS.md` 与 `CLAUDE.md` 没有规则冲突。
4. 确认 `.gitignore` 已忽略 `.worktrees/`、`.claude/worktrees/`、`.cursor/worktrees/`、`.codex/worktrees/`。

---

## 方式二：零依赖确定性脚本（`scripts/bootstrap.sh`）

如果不希望由 LLM 生成文件，可直接跑纯 Bash 脚本安全落盘（默认**绝不覆盖**已有文件，除非显式传 `--force`；已有的 `Makefile` 在任何情况下都不会被修改）：

```bash
# 先干跑预览（--dry-run 不写入任何文件）：
bash /path/to/agentic-sdlc/scripts/bootstrap.sh \
  --profile L0 \
  --target /path/to/your-repo \
  --dry-run

# 一键落地 L0 个人基线 + 6 个 Agent Skills：
bash /path/to/agentic-sdlc/scripts/bootstrap.sh \
  --profile L0 \
  --target /path/to/your-repo \
  --with-skills

# 一键落地 L1 团队基线（带语言 CI 模板）+ 实证排雷清单：
bash /path/to/agentic-sdlc/scripts/bootstrap.sh \
  --profile L1 \
  --ci python \
  --target /path/to/your-repo \
  --with-skills \
  --with-checklists

# 只读检查仓库是否具备完整的 Agentic SDLC 入口信号。--profile 要与初始化时一致；
# 脚本结束时会原样打印这条命令：
bash /path/to/agentic-sdlc/scripts/check-product-compliance.sh --profile L1 /path/to/your-repo
```

脚本跑完之后你会得到：

- **`make agent-check` 已存在，并且 Fail-Closed。** `AGENTS.md`、`CLAUDE.md` 与通用版 L1 工作流都调用它。仓库没有 `Makefile` 时，脚本会创建一个；其中 `agent-check` 在你把最后一行换成真实的 lint、类型检查与测试命令之前，会以非零退出码报 `agent-check is not configured`。仓库已有 `Makefile` 时，脚本完全不动它，只在旁边放一份 `Makefile.agent-check.snippet` 供你手动合并。
- **`--ci` 决定安装到 `.github/workflows/candidate-gates.yml` 的 L1 工作流**：`generic`（默认，执行 `make agent-check`）、`python`（Ruff `F`/`B`/`S`/`ASYNC` + pytest）、`node-ts`（`npm ci`、lint、`tsc --noEmit`、测试）、`rust`（fmt、clippy `-D warnings`、测试）、`go`（`gofmt`、`go vet`、`go test -race`）或 `java`（Gradle/Maven wrapper）。
- **`--with-skills` 默认写入 `.agents/skills/`。** Claude Code 请加 `--skills-dir .claude/skills`，Cursor 请加 `--skills-dir .cursor/skills`。

可选：安装本地 Git 护栏（默认拦截 AI Agent 在 `main` 或主 checkout 上提交，以及直推 `main`，同时完整保留并转发 `commit-msg`、`post-checkout` 等既有钩子；注意本地钩子仍可被 `--no-verify` 绕过，真正的硬合并边界在 GitHub Ruleset）：

```bash
# 单仓库（在仓库内执行，绝不会动到兄弟仓库）：
cd /path/to/your-repo
python3 /path/to/agentic-sdlc/scripts/workspace-git.py guardrails --apply

# 随时干净卸载（恢复原有 core.hooksPath）：
python3 /path/to/agentic-sdlc/scripts/workspace-git.py guardrails --remove

# 多仓工作区（--root 是包含各个仓库的上级目录，不是某个仓库本身）：
python3 /path/to/agentic-sdlc/scripts/workspace-git.py guardrails \
  --root /path/to/parent-workspace \
  --apply
```

---

## 接入你的 Coding Agent

| Coding Agent | 自动加载的文件位置 | 推荐配置 |
|---|---|---|
| **Claude Code** | `CLAUDE.md`（极薄 `@AGENTS.md` 指针）、`.claude/skills/*/SKILL.md` | 原生一键安装：`/plugin install agentic-sdlc --marketplace OpenAgenticSecurity/agentic-sdlc`（或 `npx skills add OpenAgenticSecurity/agentic-sdlc`）；根目录以 `AGENTS.md` 作为唯一根规范。 |
| **Cursor** | `AGENTS.md`（原生自动读取）、`.cursor/skills/*/SKILL.md` | 通过 `npx skills add` / `.cursor-plugin/` 安装 6 个 Skills；根目录保留 `AGENTS.md`（无需再维护一份重复的全局 `.mdc`）。 |
| **Codex / 通用 Agent** | `AGENTS.md`、`.agents/skills/*/SKILL.md`、`llms.txt` | 通过 `npx skills add` / `.codex-plugin/` 安装（或直接让 Agent 读 `llms.txt`）；根目录保留权威 `AGENTS.md`。 |

> **边界提醒**：`skills/`、`AGENTS.md`、`CLAUDE.md` 都只是**显式非权威的易用性投影**。只要一条规则必须每次都守住，就要把它下沉成 Lint、测试或 GitHub Ruleset——纯文字规则在上下文压缩后会丢失。

日常使用实证与安全排雷清单：
- 合并涉及安全面的 PR 前（鉴权、租户隔离、路径、SSRF、密码学、依赖变更）：贴入 [`checklists/secure-vibe-coding-review.zh.md`](checklists/secure-vibe-coding-review.zh.md) 并要求至少一条反向安全单测。
- 前端 PR 验收前：把 [`checklists/frontend-vibe-coding-review.zh.md`](checklists/frontend-vibe-coding-review.zh.md) 贴进评审提示词。
- 后端 PR 验收前：把 [`checklists/backend-performance-review.zh.md`](checklists/backend-performance-review.zh.md) 贴进评审提示词。
- 非平凡任务交付前：按 [`checklists/done-claim.template.md`](checklists/done-claim.template.md) 填写证据与 `does_not_prove`。

---

## 可选进阶：用 `deps` 与 `sealed-data` 做本地确定性强制

`L0`–`L2` 提供的是规则、模板与 GitHub 合并边界。[OpenAgenticSecurity](https://github.com/OpenAgenticSecurity) 的另外两个可选兄弟项目（即将陆续公开）负责在开发者本机、Agent 自己的编辑循环里做强制：

- **`deps`**：单二进制 Rust CLI（`agentic-sdlc` 的工程承载），提供 Architecture-as-Code 棘轮、依赖版本 API 守卫、密钥卫生审计、面向 **Claude Code 与 Codex** 的生命周期钩子，以及供其他支持 MCP 的 Agent 使用的固定配置 stdio MCP 服务（`deps mcp`）。
- **`sealed-data`**：让 Agent 只基于审批后的 Data Card 开发和运行数据管道，不读取真实数据集。

```bash
# 安装 `deps` 后在目标仓库运行：
cd /path/to/your-repo

# 1. 以当前模块耦合为基线；此后新增的跨边界 import 会失败：
deps aac init .
git add .deps/architecture.bundle.json

# 2. 为你使用的 Agent 安装编辑前钩子与 Stop 钩子：
deps agent-hook install . --host claude --host-version "$(claude --version)" --enforce
deps agent-hook install . --host codex --with-mcp

# 3. 在本地或 CI 运行同一套门禁，并保留可复验回执：
deps security-audit .
deps agent-verify . --receipt .deps/receipt.json --remediate
```

安装 `sealed-data` 后，运行 `sealed-data seal` 与 `sealed-data hook install .` 即可让真实数据集不进入 Agent 上下文。

---

## 接入 GitHub（`L1` -> `L2`）

1. **模板与候选 CI**：
   - 落地 `.github/pull_request_template.md`、`.github/ISSUE_TEMPLATE/` 与 `.github/workflows/candidate-gates.yml`（Action 锁定到 40 位 commit SHA、精确检出 `${{ github.event.pull_request.head.sha || github.sha }}`、`persist-credentials: false`）。
   - 如果启用了 GitHub **Merge Queue**，需在 `on:` 下额外添加 `merge_group:` 并将检出 SHA 改为 `${{ github.event.merge_group.head_sha || github.event.pull_request.head.sha || github.sha }}`（默认模板仅配置 `pull_request`）。
   - PR 侧 CI 明确标为 **candidate / advisory**，绝不自证。
2. **门禁表面 `CODEOWNERS`（`L2`）**：
   - 将 `.github/`、`Makefile`、`AGENTS.md`、`CLAUDE.md`、Schema 与校验脚本纳入 `.github/CODEOWNERS` 审查边界（见 `profiles/L2-governed/CODEOWNERS.example`）。务必把 `@org/...` 占位符替换为真实 team/用户 handle——`check-product-compliance.sh --profile L2` 发现 `@org/` 会直接 fail closed（GitHub 会静默跳过无效所有者）。
3. **配置 GitHub `main` 分支 Ruleset（`L2`）**：
   直接在 GitHub 页面导入 `profiles/L2-governed/github-ruleset.import.json`（**Settings -> Rules -> Rulesets -> New ruleset -> Import a ruleset**），把其中的 `agent-check` / `security-scan` 替换为你的真实 CI job 名（如未使用 GitHub Actions，请同步替换 `integration_id: 15368`）——默认强制开启 `~DEFAULT_BRANCH`、`>=2` 审批、`require_code_owner_review`、`dismiss_stale_reviews_on_push`、`require_last_push_approval`、绑定来源的 `required_status_checks`，并禁止任何无条件（`always`/`exempt`）或未列入白名单（`allowed_pull_request_bypass_actors`）的 `pull_request` bypass 主体。
4. **只读体检你的线上 Ruleset**：
   需要已登录的 `gh` CLI；`--validate` 还需要哈希锁定依赖文件里的 `jsonschema`：
   ```bash
   python3 -m pip install --require-hashes --only-binary=:all: \
     -r /path/to/agentic-sdlc/requirements-test.txt

   python3 /path/to/agentic-sdlc/scripts/observe-github-ruleset.py \
     --live \
     --repo owner/your-repo \
     --ruleset-id <RULESET_ID> \
     --default-branch main \
     --policy /path/to/your-repo/.github/ruleset-policy.json \
     --output ruleset-evidence.json \
     --validate
   ```
   退出码 `0` 表示远端 Ruleset 满足策略全部不变量；退出码 `2` 会直接报出具体漏洞（缺少 required status、关闭 last-push approval 或存在无条件 bypass）。
