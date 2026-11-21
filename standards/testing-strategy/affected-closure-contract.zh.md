# Affected-Test Closure Candidate 契约

**状态**：candidate 契约；仅 shadow/advisory

本契约为产品仓库提供统一的 affected-test 建议机器载体。它不拥有产品的
path map、import graph、测试入口、CI condition、required status 或 merge authority。
这些仍是产品本地实现事实，必须在产品仓库独立审查。

## Report identity

Report 使用闭合 schema
[`affected-closure-report.v1.schema.json`](schema/affected-closure-report.v1.schema.json)，
并固定 `schema_version=openagenticsecurity.testing.affected-closure-report.v1`。每个 report 都必须是
`authority=candidate`、`trusted=false`。Report 绑定完整小写 base/head Git SHA-1；如果发生
错误，则两个 revision 都必须为 `null`，并携带有界错误。变更路径来自禁止 rename 的
NUL 分隔 name-status diff，必须是仓库相对安全 POSIX path，并按 path/status 排序。

分类只有 `docs_only`、`frontend_only`、`backend_only`、`shared_boundary` 与 `full`。Reason
和 recommended suite ID 必须稳定且唯一。产品 adapter 必须把每个 recommended suite 解析到
真实仓库入口；本契约不会嵌入第二套 pytest、build、integration、browser 或 selector 实现。

## Fail-closed 与 shadow 规则

- `shadow` report 设置 `shadow_only=true`；`pull_request_fast_path` 设置
  `shadow_only=false`，但两者都仍是 candidate evidence。
- 无效 Git 输入、空 diff、未知/unmerged status、畸形或未分类 path，以及 security、migration、
  governance、CI、deployment 或 release 边界，都必须归为 `full`。错误 report 不得声称
  revision 或变更，并且必须包含 `full_boundary:git_error`。
- `docs_only` 不得推荐包含 frontend、backend、integration、browser、E2E、agent 或 full 的
  suite。产品文档 allowlist 必须显式登记；仅凭 `.md` 后缀永远不够。
- Report 不能选择或跳过测试，不能改变 required status、branch protection、review 或 bypass，
  也不能授权 merge/release。Periodic、full 和 release compatibility suite 仍是独立后盾。
- 时间戳、用户名、主机名、本地绝对路径、PR label、commit message、环境提示和 dirty working
  tree 字节都不能影响 report。

## 本地契约门禁

提交的 valid/invalid fixture 与 mutation proof 不启动产品 runtime 即可检查：

```bash
make affected-test-closure-check
```

该检查验证 schema 闭合、重复 key 拒绝、确定性排序、exact revision/error 语义、shadow-only
边界及 docs-only 防扩张规则。它不声称产品 adapter 的 suite 名称或 path rule 正确；每个产品
仍必须增加自己的真实 Git diff 与真实入口 wiring proof。

提交的 suite catalogue 至少必须包含一个稳定 suite ID，并且每个 ID 都要有非空的产品自有入口
描述。Checker 只检查 recommended ID 在 catalogue 中存在且可解析；不会解释或执行该描述。

各仓库本地的 classifier 仍是采用方自有的 candidate adapter。采用本共享 carrier、发布
真实 PR shadow observation 以及测量 false positive/negative 是独立步骤。本文及 checker
不会创建 trusted enforcement 或测试跳过权威。
