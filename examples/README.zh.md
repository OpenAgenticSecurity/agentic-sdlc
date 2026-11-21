# 可直接落地的验收门禁示例（Starter Verification Gates）

**更新日期**: 2026-11-21
**English**: [README.md](README.md)

我们的实证审计表明，传统单元测试与类型检查合计只捕获了 **7%** 的真实前端缺陷与
**5%** 的真实后端性能事故（详见 [实证发现](../docs/empirical-findings.zh.md)）。

本目录提供最小化、可直接拷贝改造的门禁骨架，演示如何把高频 Checklist 条目真正“下沉成确定性测试”：

| 示例文件 | 下沉为代码的门禁能力 | 如何使用 |
|---|---|---|
| [`backend-contract-gates.py`](backend-contract-gates.py) | SQL 查询预算上限（防 N+1）、跨进程数据库连接池总账不等式、超时链单调不等式，以及跨租户/路径穿越反向安全单测 | 可直接 `pytest examples/backend-contract-gates.py` 运行；按你真实配置与 ORM 替换参数即可 |
| [`frontend-3layer-gate.spec.ts`](frontend-3layer-gate.spec.ts) | 禁用功能三层一致联测（UI 隐藏 + 直达路由拦截 + 后端 `403`/`404`）、`loading`/`error`/`empty` 三态分离（防 `?? 0` 假默认值）与取消中断路径测试 | 拷入你的 Playwright E2E 套件并替换为真实路由与选择器 |

## 验收铁律

信任任何一条拷贝过去的门禁之前，**必须先故意植入一条违规反例**（例如调低
`db_max_connections`、把 `task_soft_limit` 改得比 `task_hard_limit` 大，或让报错接口渲染成假 `[]`），亲眼确认门禁真的会变**红**。
