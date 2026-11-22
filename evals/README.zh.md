# 确定性护栏与 Skill 有效性评测套件（Evals）

**更新日期**: 2026-11-21
**English**: [README.md](README.md)

绝不凭宣传文字信任任何护栏或 Skill。本目录提供两条互补的公开可复现评测通道：

## 1. 确定性护栏评测（零联网、零 `pip install`）

针对 `scripts/audit-repo.py` 运行离线多语言植入陷阱基准（纯 Python 3.11+ 标准库，约 1 秒完成）：

```bash
python3 -S scripts/run-evals.py
# 或通过 Makefile：
make eval-deterministic
```

评测动态构造 19 个隔离用例——**17 个植入违规陷阱**（缺失上下文/Worktree 忽略、`AGENTS.md`/`CLAUDE.md` 隐藏 Unicode 与端点劫持/静默执行投毒、`.vscode/tasks.json` `folderOpen` 与 `bypassPermissions`、Comment-and-Control CI 注入与 `pull_request_target` 检出 PR Head、未锁 40 位 SHA 的 GitHub Actions、缺失 `permissions` / `persist-credentials: false`、`@org/` 占位符 CODEOWNERS、Python/JS/TS/Go/Rust/Java Day-0 冒烟陷阱，以及允许批准后推提交或 `integration_id: null` 的弱 GitHub Ruleset）加 **2 个干净多语言对照组**——断言 100% 陷阱召回率与 0% 误报率。

## 2. Agent Skill 评测集（`evals/skills/`）

采用 `prompt.md` + `graders/rubric.md` 结构，可直接用于配对 A/B 评测（如 `claude plugin eval`）：

| 用例 | 目标 Skill | 核心考察能力 |
|---|---|---|
| [`fake-done-dereference`](skills/fake-done-dereference/prompt.md) | `done-claim-verify` | 拒绝把 `0 tests collected` 与未测环境报绿；输出带 `does_not_prove[]` 的 `DoneClaim` |
| [`three-layer-default-and-liveness`](skills/three-layer-default-and-liveness/prompt.md) | `audit-production-readiness` | 抓出生产路径无写入方的“死守卫”与三层默认值漂移（代码 `False` vs `.env.default` 为 `1`） |
| [`secure-vibe-coding-ssrf-idor`](skills/secure-vibe-coding-ssrf-idor/prompt.md) | `secure-vibe-coding` | 强制服务端租户隔离、拦截 `169.254.169.254` SSRF、杜绝硬编码兜底密钥并补齐反向安全单测 |

## 3. 评测边界（区分 `pass@k` 与 `pass^k` 及 Holdout 集）

- **绝不把 `19/19` 确定性评测等同于“通用 Agent 可靠性”**：轨道一证明的是确定性检查器在植入反例上 100% 变红且对照组 0 误报，不代表概率性 Agent 在开放任务上无错，也不替代深度数据流 SAST。
- **区分单次碰运气（`pass@k`）与多次稳定一致（`pass^k`）**：运行端到端 Agent 评测时，记录多轮重复一致性（`pass^k`），保留不参与 Prompt 调优的 Holdout 测试集，基于最终真实状态/副作用而非纯对话稿评分，且严禁产码 Agent 修改自己的验收 Oracle。
