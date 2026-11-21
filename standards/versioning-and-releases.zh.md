# 版本号管理与发布纪律标准

**状态**: accepted baseline
**更新日期**: 2026-11-21
**English**: [versioning-and-releases.md](versioning-and-releases.md)

## 目标

在 AI 辅助开发仓库中，版本号最容易在三个地方失控：Coding Agent 改了 5 处版本声明里的 1 处忘了其余 4 处、在普通修 Bug PR 里私自把 `0.x` 跳到 `1.0.0`，或者把面向人类的发版 Tag 混同为机器验证所需的不可变摘要。本标准定义清晰的 **SemVer 决策流**、**四类版本本体边界**与**不可自证的发布纪律**。

---

## 1. 严格区分四类版本标识

绝不把本质不同的版本概念混成一个字符串：

| 版本层级 | 格式 | 面向主体 | 硬约束 |
|---|---|---|---|
| **1. 发版版本号（Release Version）** | `vMAJOR.MINOR.PATCH[-pre.N]` | 人类、变更日志、包注册表 | 表达对外兼容性承诺 |
| **2. 不可变修订与制品摘要（Digest）** | 40 位 Git Commit SHA + `sha256:...` | CI、GitHub Actions、容器、回执 | 机器校验与生产部署**只认摘要**，绝不信浮动 tag（`:latest`、`@v4`、`@main`） |
| **3. 线缆 / Schema 契约版本** | `namespace.domain.name.v1` | JSON / API 契约生产者与消费者 | 仅不兼容变更才升 `.v1 -> .v2`，**不随代码发版号机械递增** |
| **4. Feature Flag 暴露态** | 默认 `OFF`（暗发布）vs 默认 `ON`（正式发布） | 平台配置 / 灰度开关 | 藏在默认 `OFF` 开关后的代码可走 `PATCH`；开关默认切 `ON` 必须升 `MINOR` |

---

## 2. SemVer 决策流

```text
本次变更是否仅修复 Bug、安全漏洞或文档/测试错误，且不改变公开 API、CLI 或数据格式？
├── 是 -> PATCH（vX.Y.Z+1）
└── 否 -> 是否新增向后兼容的能力、命令、配置项或增量 Schema/迁移？
      ├── 是 -> MINOR（vX.Y+1.0，PATCH 归零）
      └── 否 -> 是否删除/重命名公开接口、不兼容修改协议/鉴权/迁移或抬高最低运行版本？
            ├── 是 -> MAJOR（vX+1.0.0，MINOR 与 PATCH 归零）
            └── 否 -> 纯内部重构、无外部影响 -> PATCH
```

### 预稳定期（`0.x.y`）与稳定期（`>=1.0.0`）

- **`0.x.y`（预稳定期）**：`MINOR`（`0.1.0 -> 0.2.0`）用于新增能力并允许在附带迁移说明的前提下做结构调整；`PATCH`（`0.1.0 -> 0.1.1`）严格保持兼容修复。
- **`>=1.0.0`（稳定期）**：每次 `MAJOR` 升级必须配套 ADR、迁移指南、明确兼容窗口并提前通知下游消费方。

---

## 3. 面向 Coding Agent 的四条版本铁律

1. **普通功能/修复 PR 严禁私自改版本号**：Coding Agent 不得在日常 PR 中擅自修改版本清单或自造 Tag。版本号变更归属独立 Release Commit/PR，由授权维护者批准（公理 4：主体与裁判分离）。
2. **多文件版本一致性必须由确定性测试守门**：清点仓库中所有承载发版版本号的文件（`pyproject.toml`、`package.json`、`Cargo.toml`、插件清单、Helm `Chart.yaml`、README/官网徽章），用自动化单测保证一处漂移即立刻变红（例如 `tests/test_repo_governance.py::test_plugin_manifest_versions_agree`）。
3. **已发布 Tag 永久不可变**：严禁删除并强推覆盖已发布的 `vX.Y.Z` Tag；若已发布版本有缺陷，一律发布 `vX.Y.Z+1`。
4. **下游引用必须锁定不可变版本**：业务仓拷贝模板或调用可复用 GitHub Action 时，记录精确版本号并锁定 40 位 Commit SHA（绝不指向浮动 `main`）。

---

## 4. 可复现发布门禁

所有带 Tag 的正式发布（`vX.Y.Z`）必须由受保护工作流自动产出，禁止在个人笔记本手工打包上传：

- 在精确 Tag 提交上重跑全套确定性验证（`make verify-all`）。
- 按合并 PR 标签自动生成变更日志（`.github/release.yml`）。
- 同步发布源码/构建压缩包、`SHA256SUMS.txt` 与 **SLSA 构建溯源证明**（40 位 SHA 锁定的 `actions/attest-build-provenance`）。
- 发布闭环必须核验制品与线上回读，不能只看 Tag 已推送。
