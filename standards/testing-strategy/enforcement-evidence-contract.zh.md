# 外部 Enforcement Evidence Candidate 契约

**状态**：candidate 契约；只读观察；不是 trusted enforcement

**更新日期**：2026-11-21

本契约关闭一个不能靠本地测试变绿、CI job 存在或 `CODEOWNERS` 条目来关闭的治理证据
盲区。它定义独立观察 GitHub ruleset 的稳定机器载体，用于诊断仓库预期保护是否真的
出现在被观察的 ruleset 中，同时明确停留在 trusted-enforcement 边界之外。

## 范围与 report identity

Schema 是
[`enforcement-evidence.v1.schema.json`](enforcement-evidence/schema/enforcement-evidence.v1.schema.json)。
每个 report 必须固定 `authority=candidate` 与 `trusted=false`，并绑定：

- repository 与 default branch；
- 精确 ruleset API reference，以及由外部 observer 提供的 `sha256:` response digest；
- 规范化的 policy expectation 与被观察的 active branch ruleset。

Checker 不请求 API，也不重新计算外部 response digest。只读获取、原始 response 的保存、
以及 API response 到本规范化结构的映射，都归外部 observer 负责。`observed_at` 只是描述性
证据，不证明该状态仍然是当前状态。

表示集合的数组必须确定性排序且唯一。尤其是 policy status context、observed status
context、branch include/exclude pattern 与 bypass actor tuple，不能通过顺序变化或重复 key
规范化来隐藏不同观察结果。

## 必需保护语义

只有以下比较全部满足时，规范化 observation 才能被接受：

| 边界 | 必需 observation |
|------|------------------|
| Source binding | Repository、ruleset ID 与 API reference 指向同一个对象 |
| Scope | active branch ruleset 覆盖 default branch，且没有排除它 |
| Status | policy 要求的每一个 status context 都出现在 observed pull-request rule 中 |
| Status source | 当 `require_status_check_source_binding=true` 时，每个必需状态检查必须绑定正整数 `integration_id`（禁止 `null` / 任意来源） |
| Review | observed approving-review count 不低于 policy minimum |
| Review integrity | code-owner review、stale-review dismissal 与 last-push approval 都开启 |
| Bypass | 禁止无条件（`always` / `exempt`）bypass；任何 `pull_request` bypass 主体必须显式列在 `policy.allowed_pull_request_bypass_actors` 中 |

缺少 required status、状态检查来源未绑定（`integration_id=null`）、关闭 last-push approval、
存在无条件或未列入白名单的 `pull_request` bypass actor、ruleset 非 active 或 target 错误、
source/repository 不匹配、default branch 未被覆盖，都必须 fail closed。畸形 report、重复
JSON key、不安全 reference、无效 RFC 3339 时间戳或非确定性集合也必须失败。

提交的 mutation fixture 分别隔离这些失败模式：`missing-required-status.json`、
`unbound-status-source.json`、`last-push-disabled.json`、`unconditional-bypass.json`、
`unapproved-pr-bypass.json` 与 `source-mismatch.json`。valid
fixture 只证明 checker 的回归行为，不表示任何 repository 当前远端 ruleset 的状态。

## Authority 与非目标

这是 candidate evidence 契约，不会：

- 请求 GitHub、修改 ruleset、授予 bypass 或授权 merge/release；
- 选择、跳过或缩小产品测试 suite；
- 证明 required status、受保护执行、CODEOWNER approval、独立 mechanism review 或 admin-bypass
  independence；
- 把 exact-head CI 成功、job presence、本地 fixture 或 `CODEOWNERS` match 变成 trusted
  enforcement。

外部 observer、architecture/contract owner 与独立 mechanism reviewer 仍是分离的治理要求。
产品 adapter 可以把该证据发布为 shadow/advisory data，但必须保留自己的真实 API 获取与
repository wiring proof。缺少 observer 或 raw response 时是 `NOT_RUN`，不是成功的 skip。

## 本地契约门禁

Checker 有意保持无网络且有界：

```bash
set -euo pipefail
make governance-enforcement-evidence-check
```

`make check` 会调用同一个 target，因此 docs-only 变更不需要机械运行 frontend 或 backend
全量 suite。[测试策略](../testing-strategy.zh.md)中的 affected-closure 规则仍决定 shared
contract、schema、generated client、auth/permission、serialization、WebSocket、SSR/BFF 或
shared-build 变更何时把 frontend 与 backend 纳入同一闭包。本契约不会替代产品本地测试，
也不会替代定期 full 与 release suite。

修改该 schema、checker、fixture、Make 接线或治理文字都属于 enforcement-surface change，
需要 architecture/contract owner 与第二位独立 mechanism reviewer；本文自身不能提供任一
审批。
