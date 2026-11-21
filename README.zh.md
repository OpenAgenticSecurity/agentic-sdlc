# OpenAgenticSecurity — Agentic SDLC

[![CI](https://github.com/OpenAgenticSecurity/agentic-sdlc/actions/workflows/ci.yml/badge.svg)](https://github.com/OpenAgenticSecurity/agentic-sdlc/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Maturity: L0–L2 Spec & Scripts](https://img.shields.io/badge/Maturity-L0%E2%80%93L2%20Spec%20%26%20Scripts-emerald.svg)](MATURITY.zh.md)

[English](README.md) | **中文** | [项目官网](https://openagenticsecurity.github.io/agentic-sdlc/)

**别让 Coding Agent 既当选手又当裁判。**

给“代码由 Coding Agent 来写”的仓库准备的一套护栏：Agent 会读的规则、它跳不过的本地检查，以及它无法自己批准自己的 GitHub 合并边界。

这里的全部内容都是纯 Markdown、YAML 和独立脚本，直接拷进你自己的仓库即可。无框架绑定，不需要安装任何 CLI 包。

提炼自 **2000+ 亿 Token** 真实多仓 AI 辅助工程实践，并由分母明确的专项量化研究支撑：**443 次追踪会话（84 亿 Token 样本集）**、**454 个真实前端缺陷（CI 仅捕获 7%）**、**100+ 项后端性能事故（CI 仅捕获 5%）**、**24→2 条 AI Review 取证复盘**（[完整实证数据](docs/empirical-findings.zh.md)）。

---

## 60 秒直接上手

三选一即可。完整接入指南（含 Claude Code / Cursor / Codex 与 GitHub 配置）见 [**BOOTSTRAP.zh.md**](BOOTSTRAP.zh.md)（[English](BOOTSTRAP.md)）。

### 方式 A：一行装进你的 Coding Agent（6 个独立自包含跨语言 Skills）

```bash
# Claude Code 2.1.275+ 原生一键插件安装（无需第三方 npm）：
/plugin install agentic-sdlc --marketplace OpenAgenticSecurity/agentic-sdlc

# 跨工具 CLI（Claude Code / Cursor / Codex；需要锁定版本时可用 npx skills@1.9.0 add ...）：
npx skills add OpenAgenticSecurity/agentic-sdlc
```

仓库同时内置 `.claude-plugin/`、`.cursor-plugin/` 与 `.codex-plugin/` 原生插件清单。6 个 Skills **100% 独立自包含且脱离具体编程语言**（装入任意外部项目零缺文件）：

| Skill | Agent 在什么时候会用到它 |
|---|---|
| **`bootstrap-agentic-sdlc`** | 仓库还没有 `AGENTS.md`、`STATUS.md`、PR 模板或 CI 门禁时 |
| **`secure-vibe-coding`** | 编写或审查涉及鉴权、租户范围、SQL、Shell、路径、URL、密钥、密码学、依赖或 CI 的代码时 |
| **`audit-pr-diff`** | 被要求在合并前审查分支 diff 或 Pull Request 时 |
| **`audit-production-readiness`** | 需要判断一个 AI 构建的系统到底是“生产级”还是“Demo 级”时（五维审计、三层默认值、数据活性、H1/H2 裁决） |
| **`done-claim-verify`** | 准备说出“完成了”“修好了”“测试通过”之前 |
| **`multi-agent-git-flow`** | 在其他人或其他 Agent 也在改的仓库里开始工作时 |

### 方式 B：零安装一句话（直接贴给任意 Coding Agent）

```text
请先阅读 https://github.com/OpenAgenticSecurity/agentic-sdlc/blob/main/llms.txt ，
按本仓库的真实构建与测试命令为当前仓库完成 L0（或 L1/L2）档位初始化，且不要覆盖已有文件。
```

### 方式 C：纯 Bash 确定性脚本（零依赖、无 LLM）

```bash
git clone https://github.com/OpenAgenticSecurity/agentic-sdlc.git

# 先干跑预览（--dry-run 不写入任何文件）：
bash agentic-sdlc/scripts/bootstrap.sh --profile L0 --target /path/to/your-repo --dry-run

# 一键落地 L0 个人基线 + 6 个 Agent Skills：
bash agentic-sdlc/scripts/bootstrap.sh --profile L0 --target /path/to/your-repo --with-skills

# 一键落地 L1 团队基线（可选 python | node-ts | rust | go | java CI 模板）+ 实证排雷清单：
bash agentic-sdlc/scripts/bootstrap.sh --profile L1 --ci python --target /path/to/your-repo --with-checklists
```

脚本不会覆盖已有文件，结束时会打印与所选档位匹配的后续检查命令，并留下一个 `make agent-check` 入口——**在你把它指向真实的 lint、类型检查和测试命令之前，它会一直 Fail-Closed 报错**。

---

## 10 秒实证体检：直接对你自己的仓库跑一遍（零 `pip install`）

严格只读、纯 Python 3.11+ 标准库、不改任何文件——1 秒看清**你自己的仓库**在 Python / JS / TS / Go / Rust / Java、GitHub Actions 与 GitHub Ruleset 上存在哪些盲区：

```bash
git clone https://github.com/OpenAgenticSecurity/agentic-sdlc.git

# 1. 零安装、只读体检你自己的本地仓库（<1 秒）：
python3 agentic-sdlc/scripts/audit-repo.py /path/to/your-repo

# 2. 同时只读审计你仓库线上的 GitHub Branch Ruleset（需已登录 `gh` CLI）：
python3 agentic-sdlc/scripts/audit-repo.py /path/to/your-repo --github

# 3. 实跑 14 用例多语言植入陷阱评测集（12/12 陷阱拦截，0 误报）：
python3 -S agentic-sdlc/scripts/run-evals.py
```

也可以在任意仓库 CI 里直接接入 4 行可复用 GitHub Action（`action.yml`，按 40 位 SHA 锁定）：

```yaml
- uses: OpenAgenticSecurity/agentic-sdlc@<40-char-commit-sha> # v0.2.0
  with:
    target: .
```

或离线验证本仓库自身的负向变异门禁套件（安装后零联网）：

```bash
cd agentic-sdlc
python3 -m pip install --require-hashes --only-binary=:all: -r requirements-test.txt

# 1. 现场拦截存在“批准后还能被 AI 推新代码”和“无条件绕过”漏洞的 GitHub Ruleset：
make demo-catch-bugs

# 2. 运行本仓库全套确定性验证：
make verify-all
```

---

## 三层防线

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ 第一层 · Agent 内环（零摩擦易用性，显式非权威）                            │
│   skills/（6 个独立 Skills）· llms.txt · 统一 AGENTS.md（+ @CLAUDE 指针）  │
├────────────────────────────────────────────────────────────────────────────┤
│ 第二层 · 本地确定性护栏（默认生效，可用 --no-verify 绕过；硬边界在第三层） │
│   audit-repo.py（多语言）· workspace-git.py（pre-commit/pre-push 钩子）    │
│   deps（AaC 棘轮 · 依赖版本 API 守卫 · 密钥审计 · Agent 生命周期钩子）     │
│   link-shared-node-deps.mjs · sealed-data（只看 Data Card，不碰真数据）    │
├────────────────────────────────────────────────────────────────────────────┤
│ 第三层 · GitHub 合并边界（不可自证的外部强制）                             │
│   L1 Fail-Closed CI（Python/TS/Rust/Go/Java）· 可复用 action.yml           │
│   CODEOWNERS · 可导入 Branch Ruleset · observe-github-ruleset.py（--live） │
└────────────────────────────────────────────────────────────────────────────┘
```

> **既有安全工程原则并没有因为 AI Agent 的出现而过时；真正变化的是执行主体、信任边界和速度。**
> **“完成”是由精确版本与可核验证据派生出的事实，而不是 Agent 自己写回的布尔值。**

### 与 `superpowers` 等 Prompt 技能包的关系：上下互补

| 维度 | `superpowers` / 同类 Prompt 技能包 | `OpenAgenticSecurity/agentic-sdlc`（+ `deps`） |
|---|---|---|
| **关注层级** | **内环工作流**：教单个 Coding Agent 如何 brainstorm、写 plan、做 TDD 和 debug | **外环安全边界**：在多 Agent 并发高速写代码时，守住代码安全、`main` 主干与“真完成” |
| **信任模型** | 依赖模型在 Prompt 窗口内自觉遵守 | **默认零信任 + 不可自证**：靠 Git Hooks、`deps` 生命周期钩子、精确 SHA CI 与外部 GitHub Ruleset 兜底 |
| **实证深度** | 通用开发工作习惯 | 真实 AppSec 红线、454 前端 Bug、8 类后端性能陷阱、4 个假完成断点、多 Worktree 共享依赖与 2.6 亿 Token 熔断 |

两者最佳搭配：用 `superpowers` 让 Agent 写代码更有章法，用 **`agentic-sdlc` + `deps`** 确保它不会顺手上线高危漏洞、写脏 `main` 或自改测试绿灯自证。

---

## 在真实 AI 开发流里怎么用（不要全仓照搬）

无需替换 Claude Code、Cursor、Codex 或 `superpowers`——`agentic-sdlc` 像刹车系统一样卡在日常 AI 开发的 **5 个高危交接点**（[完整 4 层工具栈与痛点映射](docs/workflow-integration.zh.md)）：

```text
[1. 接单开工]   Issue -> Worktree   --> 嵌入点 ①：AGENTS.md + STATUS.md + multi-agent-git-flow + Git 钩子
[2. 规划写码]   编码内环执行        --> 嵌入点 ②：非平凡任务阈值 + secure-vibe-coding（可选叠加 deps）
[3. 喊“完成”前] Agent 汇报通过      --> 嵌入点 ③：done-claim-verify + audit-pr-diff -> DoneClaim + does_not_prove[]
[4. 开 PR 与 CI] GitHub Actions     --> 嵌入点 ④：Fail-Closed CI + 4 行 action.yml + OAS-* 规则编号
[5. 合并与上线] 生产合并门禁        --> 嵌入点 ⑤：GitHub Ruleset + CODEOWNERS + audit-production-readiness（H1/H2）
```

**不要**把整套 `standards/` 拷进业务仓库，也不要让 Agent 每次会话去联网读浮动的 `main` 分支。每类资产只放回它最合适的位置：

| 放在哪里 | 放什么 / 怎么用 | 为什么这样分工 |
|---|---|---|
| **本机全局 Coding Agent**（Claude Code / Cursor / Codex） | 一次性装好 6 个 **`skills/`**（`/plugin install` 或 `npx skills add`） | 全部是**脱离具体编程语言**的安全红线、PR 排雷、五维生产就绪审计、假完成核验与多 Agent Git 护栏（不含代码风格/格式规范），按需触发，零常驻上下文消耗。 |
| **你的业务仓库**（按项目拷一次、改成真实命令） | 唯一一份 **`AGENTS.md`** + 极薄 `@AGENTS.md` **`CLAUDE.md`** + `STATUS.md` + PR/CI 模板（`scripts/bootstrap.sh`） | Cursor、Codex、Claude Code 统一读根目录 `AGENTS.md`（无需再维护重复的全局 `.mdc`）；在栈槽位里填入本仓真实命令与语言规范，顶部留 `<!-- OpenAgenticSecurity/agentic-sdlc@v0.2.0 -->`。 |
| **本地终端 / CI**（按需或每次 PR 运行） | **`scripts/audit-repo.py`**（或 4 行 **`action.yml`**）+ **`scripts/workspace-git.py guardrails`** | 零依赖确定性拦截未锁 SHA 的 Actions、多语言高危 Sink、`--passWithNoTests` 以及 Agent 直提交 `main`。 |
| **PR Review 与 GitHub 设置** | 引用稳定规则编号（**`OAS-CI-01`**、**`OAS-SVC-01`**、**`OAS-GH-02`**）+ **`DoneClaim`** + 导入 `github-ruleset.import.json` | `standards/` 与 `checklists/` 像 OWASP ASVS 一样供人查阅与评审引用，真正的硬合并边界交给 GitHub Ruleset。 |

---

## 仓库目录全景

| 路径 | 提供的能力 | 入口 |
|---|---|---|
| **`llms.txt`** | 约 1K-token 的 Coding Agent 专用一页路由表 | [llms.txt](llms.txt) |
| **`action.yml`** | 零依赖 Composite GitHub Action，在任意仓库 CI 里运行 `audit-repo.py` | [action.yml](action.yml) |
| **`skills/`** | 6 个零重叠独立跨语言 Agent Skills + `.claude-plugin/` / `.cursor-plugin/` / `.codex-plugin/` | [skills/README.zh.md](skills/README.zh.md)（[English](skills/README.md)） |
| **`checklists/`** | 8 套实证、安全、运维与生产就绪清单 + `DoneClaim` / `Handoff` 模板 | [checklists/README.zh.md](checklists/README.zh.md)（[English](checklists/README.md)） |
| **`profiles/`** | **`L0-solo`**（统一 `AGENTS.md` + 极薄 `@AGENTS.md` `CLAUDE.md`）、**`L1-team`**（Python/TS/Rust/Go/Java Fail-Closed CI）、**`L2-governed`**（可导入 GitHub Ruleset JSON） | [profiles/README.zh.md](profiles/README.zh.md)（[English](profiles/README.md)） |
| **`examples/`** | 可直接运行的后端契约门禁（`pytest`）与 Playwright 三层前端 E2E 骨架 | [examples/README.zh.md](examples/README.zh.md)（[English](examples/README.md)） |
| **`evals/`** | 14 用例多语言植入陷阱评测（`scripts/run-evals.py`）+ Skill 评测集 | [evals/README.zh.md](evals/README.zh.md)（[English](evals/README.md)） |
| **`standards/`** | 9 篇双语核心标准（含安全、可靠/性能与版本发布标准）+ 2 套轻量闭合契约（`affected-closure`、`enforcement-evidence`） | [standards/README.zh.md](standards/README.zh.md)（[English](standards/README.md)） |
| **`scripts/`** | 9 个接入/评测脚本（`audit-repo.py`、`check-change-sync.py`、`run-evals.py`、`bootstrap.sh`、`workspace-git.py`、`agent-claim.py`、`observe-github-ruleset.py`、`link-shared-node-deps.mjs`、`check-product-compliance.sh`）+ 3 个契约/文档校验器 | [BOOTSTRAP.zh.md](BOOTSTRAP.zh.md) |
| **`docs/`** | Agentic SDLC 本体论（9 实体 / 5 公理）、工作流嵌入全景、实证数据与安全工程总纲宣言 | [ontology.zh.md](docs/ontology.zh.md) · [workflow-integration.zh.md](docs/workflow-integration.zh.md) · [empirical-findings.zh.md](docs/empirical-findings.zh.md) · [manifesto.zh.md](docs/manifesto.zh.md) |
| **`site/`** | 零依赖双语 GitHub Pages 静态官网与规范 JSON Schema 托管 | [site/index.html](site/index.html) · [在线官网](https://openagenticsecurity.github.io/agentic-sdlc/) |

### 运行环境要求

| 想使用 | 需要准备 |
|---|---|
| Skills、清单、档位模板、标准 | 无需任何环境——纯 Markdown、YAML 与 JSON |
| `bootstrap.sh`、`check-product-compliance.sh` | macOS 或 Linux 上的 Bash 3.2+ 与 Git（Windows 未经测试，请使用 WSL） |
| `audit-repo.py`、`check-change-sync.py`、`workspace-git.py`、`agent-claim.py`、`observe-github-ruleset.py` | Python 3.11+ 标准库；`--github`、`--live` 与 `publish` 还需要 `gh` CLI |
| `observe-github-ruleset.py --validate`、`make verify-all` | `requirements-test.txt` 中带哈希锁定的依赖 |
| `link-shared-node-deps.mjs` | Node.js 18.3+ 与 npm |

---

## OpenAgenticSecurity 生态协作

| 仓库 | 定位 |
|---|---|
| **`agentic-sdlc`**（本仓） | 方法论、Secure Vibe Coding 安全红线、8 套清单、6 个独立 Skills、可复用 `action.yml`、L0–L2 启动包与 Git/Ruleset 脚本 |
| **`deps`** *（即将开源于 [OpenAgenticSecurity](https://github.com/OpenAgenticSecurity)）* | 第二层可选单二进制 Rust **工程承载**：Tree-sitter `deps context`/`locate`、`deps aac init`/`check`、`deps lineage-audit`、`deps security-audit`/`security-filter`、Claude Code 与 Codex 生命周期钩子（`deps agent-hook install`）、`deps agent-verify --receipt` |
| **`sealed-data`** *（即将开源于 [OpenAgenticSecurity](https://github.com/OpenAgenticSecurity)）* | 可选 Rust CLI：让 Agent 只基于审批后的 Data Card 开发和运行数据管道（`sealed-data seal`），不读取真实数据集 |
| **`assurance-contracts`** *（即将开源于 [OpenAgenticSecurity](https://github.com/OpenAgenticSecurity)）* | 可选的企业级 L2 协议套件：面向自建 Guardian 的 UI Assurance（8 Schema）与 Code Health（10 Schema）闭合契约与校验器 |

`deps` 与 `sealed-data` 均为可选同级生态仓（计划陆续发布至 [OpenAgenticSecurity](https://github.com/OpenAgenticSecurity)），接入方式见 [BOOTSTRAP.zh.md](BOOTSTRAP.zh.md#可选进阶用-deps-与-sealed-data-做本地确定性强制)。

---

## 信任边界声明

本仓库中的所有 candidate 检查均从 PR 受控源码运行，属于 **advisory / 不可自证** 证据。详见 [**MATURITY.zh.md**](MATURITY.zh.md)（[English](MATURITY.md)）、[**CONTRIBUTING.md**](CONTRIBUTING.md)、[**CODE_OF_CONDUCT.md**](CODE_OF_CONDUCT.md)、[**SECURITY.md**](SECURITY.md) 与 [**LICENSE**](LICENSE)。

### 适用对象与诚实边界

`agentic-sdlc` 主要面向在真实生产或多仓代码库中使用 Coding Agent 的**软件工程师、技术负责人、安全工程师与 AI-Native 研发团队**。

- **如果你是零开发经验的个人 Vibe Coder**：采用 `L0` 与 `skills/` 依然可以帮你挡住约 80% 的常见致命失误（密钥泄漏、缺鉴权、假数据、写脏 `main`），并让代码保持干净、随时可供专业工程师接手；**但没有任何 SDLC 模板或 AI Skill 可以替代生产商业化所需的人类工程判断**。在涉及支付计费、认证授权、多租户敏感数据或生产运维（备份恢复、限流、费用封顶与故障响应）正式向客户收费前，仍需要具备工程经验的人员进行独立审查。
