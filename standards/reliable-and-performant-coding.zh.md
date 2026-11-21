# 可靠性、稳定性与高性能 AI 编码标准

**状态**: accepted baseline
**更新日期**: 2026-11-21
**English**: [reliable-and-performant-coding.md](reliable-and-performant-coding.md)

## 目标

安全规范守住系统“不被打穿”，而可靠性、稳定性与性能规范守住系统在 P99 负载下不崩塌、在数小时 Agent 长程运行中不泄漏资源，以及在底座模型或依赖升级时不静默翻车。

本标准定义的是**写码前必须生效的不变量（Pre-Coding Invariants）**——要求 Coding Agent 在写代码当下直接遵守，而不是等事后审 PR 再大面积返工。

---

## 1. 资源生命周期与长程循环韧性

AI 生成的代码往往在单次 Happy Path 下完美运行，却在 Agent 连续执行上百步后崩溃。

- **谁创建，谁负责关闭**：HTTP 客户端、LLM SDK、数据库 Session、SSH/Socket 连接与文件句柄必须归属显式上下文管理器（`with`/`async with`/RAII/`defer`/应用 lifespan）——严禁每次调用临时创建却不关闭（彻底消除 `Event loop is closed` 与句柄耗尽）。
- **面向长程循环（Long-Path）而非一次性脚本设计**：持久化复用连接（连接池 / SSH ControlMaster），对瞬时网络抖动使用有界指数退避重试，配轻量心跳探针，并对不可信字节流使用容错解码（如 `errors="replace"`）。
- **全链路有界载荷**：大文件上传/下载在网关和服务端流式分块落盘，禁止整块拼入内存；列表接口强制分页（`default=20`，硬上限 `max=200`）；工具大输出按上限截断并显式披露。

## 2. 幂等、`RESULT_UNKNOWN` 与爆炸半径四层治理

跨外部 API 与网络，“请求发出去但没收到回执”（`RESULT_UNKNOWN`）是物理常态，跨厂商不存在分布式 Exactly-Once。

- **写操作遇到 `RESULT_UNKNOWN` 严禁盲目重试**：变更类写操作必须带幂等键；超时未知态先走独立只读回读（read-after-write）核对外部真实状态，再决定补发、对账或转人工。
- **自动化副作用的四层爆炸半径兜底**：
  1. **执行前物理硬限流**：独立于 LLM 的速率与资产爆炸半径红线（核心资产禁止自动变更）。
  2. **可逆优先 + TTL + 预置补偿**：优先采用带 TTL 的可逆动作，发出动作前先生成回滚/补偿凭证。
  3. **带外紧急制动（Emergency Stop）**：急停开关独立于 LLM 循环与 UI，通过单调递增 `safety_epoch` 瞬时作废所有在途旧 Grant。
  4. **显式耐久状态机**：长任务必须持久化租约、心跳与 fencing token，防止超时重试脑裂覆盖新持有者。

## 3. 并发、事件循环卫生与容量总账

- **严禁阻塞异步事件循环**：禁止在异步处理器（Python `async def`、Node/Tokio 事件循环）内调用同步 DB 驱动、同步缓存/HTTP 或重 CPU 解析；要么匹配同步线程模型，要么显式卸载到线程池。
- **严禁跨越远程 `await` 持有数据库连接或行锁**：在等待外部 HTTP/LLM/沙箱调用前先提交并释放短事务；锁与并发冲突必须在真实生产数据库引擎（如 PostgreSQL）上测试，不能只靠内存 SQLite。
- **把乘数账本写成确定性契约测试**（参考 [`examples/backend-contract-gates.py`](../examples/backend-contract-gates.py)）：
  - **连接池总账**：`sum(进程数 * (pool_size + max_overflow)) * 发布倍率 <= 0.7 * db_max_connections`。
  - **超时链单调性**：`queue_visibility > stale_cleanup > task_hard > task_soft > sub_agent > tool_or_sse > llm_client`。
  - **查询预算与索引**：强制联合索引 `(tenant_id, ...)` 与显式外键索引；用严格关联加载 + SQL 计数测试掐死 N+1；耗时与计数器默认 64 位整数（`BIGINT`）。
- **空载必须保持安静**：`<60s` 高频定时任务先做只读 `EXISTS` 探针并关闭结果存储写回；SSE/流式接口必须绕过缓冲型 GZip 压缩中间件。

## 4. Schema 单一权威与可观测降级

- **Schema 单一权威**：每个持久化存储只允许通过版本化迁移工具（Alembic、Goose、Flyway、Prisma Migrate）演进——严禁启动期 `create_all()` 静默建表改结构。
- **降级必须可观测（禁止假绿灯）**：前后端严格拆分 `loading`、`error`、`真正为空` 三态；禁止用 `?? 0`、`|| []` 或静默 `catch` 把读取失败伪装成合理业务值；DB 异常写失败态前必须先 `rollback()`。
- **零灾难性回溯正则**：解析与脱敏正则必须保持线性时间，并在匹配前截断超长输入。

## 5. 厚做 vs 薄做架构与模型升级回归纪律

底座模型每 3–6 个月跃迁一次，架构必须抗迭代并产生复利。

- **必须厚做（模型越强复利越高）**：事实平面与规范数据模型、确定性治理/授权/审计内核、受控执行沙箱、可复现评测基准。
- **必须薄做、随时敢删**：只为弥补弱模型临时缺陷而堆出的重型 Prompt 脚手架或纯 LLM 互评反幻觉胶水层。
- **把每次模型升级当成高风险发布**：绝不靠改一个环境变量直接切模型——上线前必须跑固定回归集，同步核查完成率、工具报错率、安全拒答率、更强并行 Tool Call 引爆的隐藏并发死锁、固定上下文压缩阈值错配以及 Schema 严格度暴露的歧义。

## 6. 工程隔离式多 Agent 与 Tool Harness 设计

- **靠隔离而非群聊拿增益**：多 Agent 的真实增益来自从零加载的干净 `TaskEnvelope` 上下文隔离、最小权限交集（海量原始日志工具只授给 Sub-Agent，不污染 Supervisor）、Append-Only 单写者黑板（非 owner 写入显式登记为 `conflict`），以及保留分歧并用外部证据证伪的确定性聚合。
- **按操作系统 ABI 思维设计 Tool Harness**：高频受控查询收口为固定语义原语，长尾开放分析交由受控沙箱（高频复用脚本再结晶为版本化工具）；大返回值溢出落盘并按字节切片回读；**将机器异常翻译为对 AI 可操作的下一步恢复提示**，避免 Agent 原地撞墙重试。

## 相关文档

- 后端性能审查清单：[checklists/backend-performance-review.zh.md](../checklists/backend-performance-review.zh.md)
- 前端 454 Bug 审查清单：[checklists/frontend-vibe-coding-review.zh.md](../checklists/frontend-vibe-coding-review.zh.md)
- 可运行后端契约门禁示例：[examples/backend-contract-gates.py](../examples/backend-contract-gates.py)
- 默认安全编码标准：[secure-vibe-coding.zh.md](secure-vibe-coding.zh.md)
