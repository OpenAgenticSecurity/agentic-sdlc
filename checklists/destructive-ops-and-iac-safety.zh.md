# 破坏性运维、数据库迁移与 IaC 安全防呆清单

**状态**: accepted baseline
**更新日期**: 2026-11-22
**English**: [destructive-ops-and-iac-safety.md](destructive-ops-and-iac-safety.md)

> **为什么需要这份清单**：公开的 AI 破坏生产系统事故反复暴露四类共性根因：（1）本地 `.env` 直连生产库，Agent 执行强制 schema push 或清理脚本直接清空生产表；（2）文字禁令或 `/careful` 模式拦不住失控命令；（3）禁止改 `terraform/production/*` 后，Agent 转而修改跨环境共享模块 `terraform/modules/shared/` 绕过路径黑名单；（4）销毁资源时把同账号云快照一并删除，或迁移只核对数据库行数却漏删对象存储文件。

---

## 1. 环境与凭证物理隔离

- [ ] **Coding Agent 环境零生产凭据**：开发机、本地 `.env` 与 Agent 沙箱中绝不存放生产库连接串、云管理员密钥或生产部署 Token。
- [ ] **生产写操作必须经 Agent 无法自取的独立角色**：生产部署、删表与集群变更只能由人类触发或独立高权角色执行，Agent 自身不具备凭证路径。
- [ ] **禁止非临时环境执行破坏性快捷命令**：禁止 Agent 对任何持久环境运行 `db push --force-reset`、`DROP TABLE`、`DROP COLUMN`、`TRUNCATE`、`terraform destroy` 或 `kubectl delete`。

## 2. IaC 与共享模块爆炸半径护栏

- [ ] **共享 IaC 模块按最高环境级别纳管**：跨环境复用的 Terraform/Helm 共享模块（如 `terraform/modules/shared/**`）必须与 `production/` 享受同等 `CODEOWNERS` 与双人审查门禁。
- [ ] **保护有状态资源免遭激进漂移重建**：数据库、对象存储桶与 KMS 密钥必须配置 `lifecycle { prevent_destroy = true }`；Terraform Plan 中出现任何 `-/+ replace` 或 `destroy` 强制人工签字。
- [ ] **强制 Staging 观察窗口（Bake Window）**：禁止 Agent 在 Staging 刚变绿后 0 分钟自动提生产自动合并 PR；把观察窗口编码成 CI/CD 门禁而非停留在 Wiki 文字里。
- [ ] **核验容器加固基线**：拒绝部署清单中的 `privileged: true`、浮动 `:latest` 镜像标签，以及缺失 `read_only`、`no-new-privileges`、`cap_drop: ALL` 的配置。

## 3. Agent 不可达的独立备份与全资产核验

- [ ] **备份必须物理脱离 Agent 凭证可达范围**：权威备份与快照存放于独立账号、隔离 Vault 或不可变 Object Lock 存储桶，确保失控 Agent 无法连坐删除快照。
- [ ] **删旧资源前核验全部存储平面**：绝不只凭数据库行数一致就批准删除旧环境——必须同步核验对象存储/文件资产、校验和并完成抽样恢复演练。
- [ ] **独立核实 Agent 关于删除与回滚的宣称**：当 Agent 声称“可安全删除”或“无法回滚”时，必须由人类通过只读探针、Git 历史与备份快照独立复核后再做决定。
