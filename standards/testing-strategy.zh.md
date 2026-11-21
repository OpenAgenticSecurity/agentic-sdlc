# Agentic 测试策略

**状态**: accepted baseline
**更新日期**: 2026-11-20

## 目标

测试应保护业务行为、跨仓库契约、部署路径和治理文档不发生漂移。

## 测试层次

| 层次 | Owner | 目的 |
|------|-------|------|
| Unit tests | 所属仓库 | 验证函数、类、本地模块 |
| Integration tests | 所属仓库 | 验证子系统和 adapters |
| Contract tests | producer 和 consumer 仓库 | 验证跨服务 payload 和兼容性 |
| End-to-end tests | 所属或交付仓库 | 验证面向用户的工作流 |
| Deployment smoke tests | 所属或交付仓库 | 验证安装、启动、健康检查和最小工作流 |
| Security tests | 所属仓库 | 验证 auth、isolation、redaction、permissions |
| Documentation checks | 治理与所属仓库 | 验证链接、必需文档和占位符 |

## 跨产品契约测试

每个已实现集成都应有：

- golden payload fixtures
- schema validation
- consumer parsing tests
- idempotency tests
- unauthorized 或 invalid payload tests
- supported versions 的 backward compatibility tests

## 按受影响闭包选择门禁

测试选择应依据实际 diff、导入/依赖闭包和契约边界，而不是只依据文件所在的
`frontend` 或 `backend` 目录。默认规则如下：

- 仅改变 frontend presentation、样式或局部交互，且没有改变
  公开 contract/API、schema、generated client、auth/permission、feature flag、共享状态、serialization
  格式、WebSocket contract、SSR/BFF 行为或共享构建配置：运行 frontend lint/type、
  聚焦 unit/component 测试和适用的 UI Assurance obligation；不要求仅因目录标签而
  机械地跑完整 backend unit suite。
- 仅改变 backend 内部实现，且没有改变上述任何共享边界：运行聚焦 backend unit
  与相关 backend integration；不要求仅因目录标签而机械地跑完整 frontend suite。
- frontend 或 backend 任一侧改变上述共享边界时，把两侧视为同一个 affected
  closure；运行相关 producer/consumer contract、backend parser/service unit 或
  integration、frontend consumer unit/component/integration，以及至少一个
  browser/API journey。
- 无法确定闭包、涉及安全边界或发布路径时，运行两侧完整 affected suite；不能用
  “目录看起来独立”代替依赖证据。

跨层测试至少要覆盖 schema validation、consumer parsing、版本兼容、idempotency
以及 unauthorized/invalid payload。缺少 browser、fixture service 或依赖时必须
报告 `NOT_RUN` 并让 candidate command 非零退出，不能把环境缺失伪装成绿色 skip。

测试成本优化可以分层，但不能减少边界证明：每个昂贵的真实 evaluator、source
closure 或 browser journey 至少保留一个端到端 wiring proof；其余只验证正交组合的
测试可以使用显式、确定性的窄 fixture。替身必须声明适用范围，并由真实 runner、
依赖完整性和代表性 mutation test 独立守护。

按路径选择只能作为 PR 的快速反馈优化。定期完整套件和发布兼容门仍然是强制项，
不能由 affected-path filtering 取代。

### 分类器与 shadow 模式契约

产品仓库可以实现确定性的 affected-closure 建议，但分类器本身也是 assurance
mechanism，必须同时满足以下规则：

- 范围只能来自解析后的精确 base/head commit ID，以及 NUL 分隔、禁用 rename 的
  name-status diff。Agent 说明、PR label、commit message、环境提示和未提交工作树都不能
  缩小结果。
- 未知或畸形 path/status、空 diff、安全、migration、governance、CI、部署或发布边界
  必须 fail closed 到完整 affected suite。更窄分类必须有显式且经过测试的规则；未分类
  路径不能默认继承 frontend 或 backend。
- 输出必须是稳定的机器可读输出，changes/reasons 顺序固定，且不能包含
  时间戳、用户名、主机名或机器本地路径。无效 Git 输入必须输出有界的
  full-closure error result，并以
  非零退出。
- 每个推荐 suite 标识必须解析到仓库真实入口。分类器只推荐 closure，不能复制第二套
  pytest、build、integration 或 browser selector 实现。
- Shadow 模式只能观察：不得选择或跳过测试，不得向现有 job 注入缩小范围的 condition，
  也不得改变 required status、branch protection、bypass、review 或 merge authority。
- Shadow 建议不能替代定期完整套件或发布兼容门。晋级前必须具备代表性的违规与合法对照
  mutation、实测 false-negative/false-positive 样本、独立审查的路径覆盖，以及单独的
  trusted-enforcement 决策。
- 显式 gate 缺少 Node/npm、browser、fixture service、本地依赖或其他 mandatory
  prerequisite 时，必须非零退出，并给出有界的缺失项清单。preflight 通过后，仓库真实
  命令仍是执行权威；禁止用成功的 skip 文本伪装门禁通过。

分类器输出、job presence 和 exact-head success 仍是 candidate 或 PR-controlled
evidence，不是 trusted enforcement。修改机制的 PR 需要 architecture/contract owner
和第二位独立 mechanism reviewer。

该建议的平台载体是闭合的
[Affected-Test Closure Candidate 契约](testing-strategy/affected-closure-contract.zh.md)。
它固定 exact-revision/error 语义、稳定分类、确定性排序，以及 `docs_only` 不得扩展到
frontend/backend 或 full suite 的规则。产品仓库仍必须提供真实 Git diff 与测试入口 wiring
proof；平台 checker 不复制这些 selector。

## Code Health candidate 层

Code Health candidate contract 与 UI Assurance、Product Architecture 是独立的
assurance domain。`make code-health-test` 运行共享原语 characterization tests 以及
closed schema/semantic fixture suite，并关闭环境 pytest 选项和 plugin autoload；
`make code-health-check` 是不写入的 bundle drift
和 mutation gate。`bundle-generate` 是 maintainer 操作，不是 CI 的通过/失败捷径。

F1 checker 证明 canonical identity、closed record、显式 runtime-path/feature-flag
lifecycle、append-only retirement/waiver chain 和派生 receipt summary；F2 增加有界的
exact base/head Git observer、exact-tree policy/baseline loading、产品拥有的 registry
loading、typed impact/obligation compilation、candidate-receipt replay check 和确定性的
module-context projection，并输出 `authority=candidate`、`trusted=false`。它不提供
trusted baseline、product adapter、required status、merge/release authority，也不能授权
跳过 periodic/full/release suite。通用 Git/registry observation 可以 evaluated，但
Python/TypeScript route/schema adapter、generated-client analysis、migration、
duplicate/dead-code discovery 和任意 plugin loading 仍是明确的 adapter gap，必须为
`NOT_EVALUATED`，不能生成空的绿色结果。缺少 adapter、dependency、browser、fixture
service 或其他 mandatory prerequisite 仍然是非绿色结果。

纯 backend 内部实现且没有 public contract、schema、generated client、auth/permission、
feature flag、共享状态、serialization、WebSocket、SSR/BFF 或共享构建影响时，聚焦的
backend unit 和相关 integration 足够，不机械要求完整 frontend suite；纯 presentation
frontend 变更对称适用。触及任何共享边界，或闭包不确定/安全敏感/release scope 时，形成
一个 frontend/backend affected closure，必须有 producer/consumer contract、backend
parser/service、frontend consumer 测试和至少一个 browser/API journey；无法界定闭包时
升级为两侧完整 affected suite。

Docs-only 变更运行 `make check`，不机械运行完整 frontend 或 backend
套件。如果文档变更同时编辑 schema、generated contract、architecture/enforcement surface、
shared build 或 release input，则由实际共享边界而不是 `.md` 后缀决定 affected closure
和额外确定性门禁。仓库本地文档如果改变 executable configuration、generated output 或
public contract，也遵循同一闭包规则。

## 按变更类型的最低门禁

| 变更类型 | 必需门禁 |
|----------|----------|
| Docs-only 变更 | `make check` |
| 仓库本地代码变更 | unit tests 和相关 integration tests |
| 跨仓库契约变更 | producer 和 consumer contract tests |
| 部署变更 | smoke test 或部署验证 |
| 安全敏感变更 | 相关 auth、isolation、redaction 或 permission tests |
| Release candidate | 完整测试套件 + release smoke checks |

## UI Assurance 风险与证据契约

UI Assurance 根据 actual diff、dependency closure、registered Surface，以及 declared 与
derived risk 中较高者，编译最低证据：

| 风险 | 最低 candidate categories |
|---|---|
| `C0` | scope diff 加适用的 repository lint/type checks |
| `C1` | `C0` 加聚焦的 unit 或 component presentation checks |
| `C2` | 适用的正向 structure、component states、browser journey、visual assertion、accessibility 与 keyboard/focus |
| `C3` | `C2` 加 critical journeys，以及 feature flag、role、permission、tenant 与 license visibility matrix |
| `C4` | 完整 affected closure、违规与合法对照 mutation、exact-head 独立 mechanism review，以及 independently pinned 或 protected evaluator |

每条已编译 obligation 只能记录 `PASS`、`FAIL`、`NOT_RUN`、`FLAKY`、`ERROR` 或
`NOT_APPLICABLE`。只有 `PASS` 能满足 mandatory obligation。Dependency、browser、fixture
service 或 environment 缺失时必须为 `NOT_RUN`，candidate command 必须非零退出，不能成功
skip。`NOT_APPLICABLE` 归确定性 compiler 所有，不能由 Agent 或既有 obligation result 声明。

新的 structure rule 必须让代表性违规案例失败，同时让相邻合法对照通过。Source substring
check、failure screenshot、automated axe output 与一次绿色执行都不能独立证明充分性。
Visual baseline 变更需要 exact-diff review，不能由 candidate producer 自批。Release
admission 必须绑定被测试的同一 immutable artifact digest；相同 Git revision 的重建物并不等价。

## 门禁完整性

一个门禁如果存在但不运行、不覆盖被改动的文件，或者可以被悄悄放宽，只会带来虚假的
信心。产品仓库对自己的 lint、type、test 和 budget 门禁适用以下规则：

- 每个门禁都有书面 spec：检查什么、覆盖哪些文件、接受哪些绕过或 suppression、由什么
  事件触发、变红是否阻塞 merge。
- 新增或修改的门禁，要用一个植入的违规案例证明它会变红，并用一个相邻的合法对照证明它
  保持绿色。收集到 0 个测试、全部 skip，或 job 根本没有触发，都不算通过。
- Budget、baseline 和 suppression 列表只减不增。不得为了让变更通过而降低规则的严重级别。
  提高 budget 必须单独开 PR，写明原因和 owner，不能作为功能 PR 的附带改动。
- 必须阻塞 merge 的检查，要在 branch protection 中设为 required status check。没有设为
  required 的绿色 job 只是建议性结果；required context 的观察方式见
  [外部 Enforcement Evidence Candidate 契约](testing-strategy/enforcement-evidence-contract.zh.md)。
- 审计或扫描器发现的问题，在修复或作为缺陷报告前，先在当前代码上复现。

## 前端测试证据

使用手写数据的 unit 和 component 测试，漏掉的恰恰是最常到达用户的缺陷：API 形状不对、
数据量大或数据畸形、跨层状态。前端变更需要补充：

- Fixture 和 mock 按真实 API 形状构造，优先从后端 schema 生成；并包含大数据量、字段缺失
  和畸形值的案例。
- 上传、下载、content-type 或序列化路径上，不 mock 传输层或序列化层。断言实际发送出去的
  内容。
- 用户可见变更需要浏览器验收，并按四个问题说明：
  1. 证明到了哪一级：能渲染、能从真实导航到达、用真实数据正确，还是在生产数据量下仍然
     正确？
  2. 是否在浏览器里沿真实用户路径操作过，而不只是在终端里跑了测试？
  3. 对被禁用或未授权的功能，入口、直接路由、后端 API 和 flag 接口是否全部一致？
  4. 读取失败时，界面显示的是未知或错误，而不是一个看似合理的值？每个展示语义是否只来自
     一个字段？

## Vibe Coding 验证规则

人类和 agents 必须报告证明结论的命令。不能只靠推理报告任务完成。

好的报告：

```text
Ran `make check`; it completed with exit code 0.
```

坏的报告：

```text
Docs should be fine.
```

## 文档检查

本仓库提供轻量文档检查：

```bash
make check
```

该检查验证必需文件、扫描未解决占位符，并检查本地 Markdown 链接。

## 外部 Enforcement Evidence Candidate 契约

[外部 Enforcement Evidence Candidate 契约](testing-strategy/enforcement-evidence-contract.zh.md)
定义独立观察 GitHub ruleset 的只读规范化载体。它明确只属于 candidate：每个 report 都是
`authority=candidate` 与 `trusted=false`，提交的 fixture 或 checker 变绿都不能证明当前远端
ruleset。

当 required status context 缺失、last-push approval 关闭、存在 unconditional bypass actor、
source 与 repository/ruleset 不匹配、default branch 未被覆盖，或 report 畸形/非确定性时，
Checker 必须 fail closed。它不会请求 GitHub、修改保护、选择或跳过产品测试，也不会授权
merge/release。外部 observer 必须保存 raw response 及其 digest；缺少 observation 是
`NOT_RUN`，不是成功的 skip。

使用 `make governance-enforcement-evidence-check` 运行有界的本地契约门禁；`make check` 会调用
同一个 target。Exact-head CI、job presence、`CODEOWNERS` 与 candidate output 仍与 trusted
enforcement 分离，并需要 architecture/contract owner 与独立 mechanism reviewer。
