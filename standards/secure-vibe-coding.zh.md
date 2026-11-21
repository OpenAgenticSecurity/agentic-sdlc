# Secure Vibe Coding 安全编码标准

**状态**: accepted baseline
**更新日期**: 2026-11-20
**English**: [secure-vibe-coding.md](secure-vibe-coding.md)

## 目标

Vibe Coding 极大加快了代码生成速度，也同样加快了可预测安全漏洞的上线速度。AI 写出的漏洞大多不是罕见 0-day，而是高度集中于六类模式：Fail-Open 兜底、缺失鉴权/租户隔离、危险 Sink 注入、硬编码开发密钥、错误的密码学默认值、幻觉依赖包，以及未设防的 LLM/工具边界。

本标准定义 AI 辅助开发代码的**不可妥协安全编码不变量**、**反向安全单测要求**，以及如何通过静态门禁和本地 Rust 工程承载 **`deps`** 实现确定性落地。

---

## 1. 认证、授权与防 Fail-Open

- **所有边界默认拒绝（Fail-Closed）**：缺失凭据、过期 Token、未知角色、查询失败或未评级动作必须明确拒绝（`401`/`403` 或抛错），绝不允许顺着兜底分支放行。
- **安全路径禁止静默吞异常**：认证、授权、策略校验与租户过滤逻辑中，严禁裸 `except Exception: pass` 或把 `?? true`、`|| []` 当成“无限制”放行。
- **服务端强制租户与对象归属校验（防 IDOR / 越权）**：所有读写改删必须在数据查询层显式绑定已认证的 principal/tenant 范围，绝不轻信客户端传入的 `tenant_id` / `user_id`，也绝不把前端隐藏按钮当权限控制。
- **严格校验 Token**：校验签名、显式算法白名单（拒绝 `alg=none` 与非对称/对称混淆）、`exp`、`nbf`、`iss`、`aud`；Token/MAC 比对一律使用常量时间函数（如 `hmac.compare_digest`）。
- **安全的 Web 默认值**：严禁同时开启 `Access-Control-Allow-Origin: *` 与 `Access-Control-Allow-Credentials: true`；基于 Cookie 的写操作强制 CSRF 防护；会话 Cookie 设置 `HttpOnly`、`Secure`、`SameSite`。

## 2. 注入、SSRF、路径穿越与 ReDoS

- **只用参数化查询**：严禁通过字符串拼接或格式化构造 SQL、Cypher、LDAP 或 NoSQL 查询。
- **禁止 Shell 拼接**：子进程调用使用参数数组（`subprocess.run([...], shell=False)`）；严禁把不可信输入传入 `shell=True`、`eval`、`exec` 或未转义模板。
- **规范化路径收敛（防路径穿越 / Zip-Slip）**：文件读写与压缩包解压前必须 `Path.resolve()` 校验仍在预期根目录内，显式拒绝 `..`、绝对路径、控制字符以及指向目录外的软链接（symlink）。
- **SSRF 与 DNS Rebinding 防护**：严禁把用户或 LLM 提供的 URL 直接传给 `requests.get` / `httpx` / `fetch`。必须限制协议白名单（`https`）、连接前解析并拦截回环/私网/链路本地/云元数据地址（如 `169.254.169.254`、`fd00::/8`）、禁用隐式重定向，并设严格连接/读/总超时与响应体大小上限。
- **安全反序列化与渲染**：严禁对不可信输入使用 `pickle`、`marshal` 或不安全的 `yaml.load`（一律用 `yaml.safe_load` 或带闭合 Schema 的 JSON）；禁止未消毒原始 HTML/SVG 渲染（如裸 `dangerouslySetInnerHTML`）。
- **线性正则与输入封顶**：脱敏与解析正则严禁嵌套量词与重叠分支（防灾难性回溯 ReDoS），匹配前先截断超长输入。

## 3. 密钥托管与实用密码学运营底线

- **零硬编码兜底密钥**：严禁 `os.getenv("SECRET_KEY", "dev-secret")` 类写法，严禁提交真实凭据、私钥或 `.env`；缺少必填密钥必须直接启动失败。
- **凭据不进任何明文 Sink**：密钥、Token、私钥严禁出现在日志、异常回显、数据库明文字段、Docker 镜像层或 LLM Prompt 中。
- **绝不自造密码算法与实现**：不自创加密/AK-SK 截取算法，不手写加解密原语，统一使用经过审计的标准库（`cryptography`、WebCrypto、libsodium、RustCrypto）。
- **密码学运营铁律**：
  - **密钥与数据同等价值**：私钥存放在专属 KMS / HSM / Vault，绝不存放在本地明文目录或用配置文件保存私钥口令。
  - **禁止固定 IV / Nonce**：每次加密使用密码学安全随机数（`secrets` / CSPRNG，严禁 `random`）生成唯一 Nonce，优先使用带关联数据（AAD）的 AEAD（AES-GCM / ChaCha20-Poly1305）。
  - **严格密钥分离与生命周期**：不同业务场景（签名 vs 加密、测试 vs 生产）严禁共用同一密钥或证书，禁止复用随机数，强制轮换与有效期。
  - **密文上算 MAC（Encrypt-then-MAC / AEAD）**：绝不在明文上单独计算 MAC。
  - **TLS 与证书校验**：严禁关闭证书校验（`verify=False`）；校验证书链、主体身份与有效期，生产环境避免多年期自签或过度宽泛的通配符证书。

## 4. AI 时代供应链与依赖卫生

- **防幻觉包投毒（Slopsquatting）**：AI 常编造看似合理的包名（已被攻击者抢注）。新增任何第三方依赖前，必须核实包真实存在、发布者与源码仓可信，并锁定精确版本与哈希（`--require-hashes` / lockfile）。
- **GitHub Actions 锁定完整 40 位 SHA**：`.github/workflows/` 禁止引用可变 tag（如 `@v4`/`@main`）；默认最小权限 `permissions: contents: read` 并关闭 `persist-credentials: false`。
- **禁止运行期联网装包**：依赖必须在构建期装完；容器启动脚本与 Agent 运行环境禁止 `curl | sh` 或临时联网拉包。

## 5. Agent 与 LLM 不可信边界代码安全

当 AI 参与开发的系统本身也在调用 LLM、工具或 MCP Server 时：

- **确定性机制与受限中间表示（IR）优先于 LLM 判定**：凡是能用 Schema、解析器、类型检查、Linter 或策略引擎判定的规则，绝不交给 LLM 拍脑袋放行；任何触发副作用的 LLM 输出必须先进入闭合、经校验的中间表示（IR）再执行。
- **显式五层配置优先级**：按 `平台管理配置 > 租户/组织策略 > 密钥库 > 部署环境变量 > 代码默认值` 逐层解析，严禁仅凭代码默认值推断生产安全态或功能权限。
- **外部数据与 LLM 输出默认不可信**：外部网页、日志、邮件或工具输出绝不未经确定性 Schema 校验与策略检查就直接喂入 SQL、Shell、HTTP 或写文件 Sink。
- **加固不可信数据定界**：不能只靠简单字符串标记；需防范 Unicode 隐身字符（`Cf` / `Default_Ignorable_Code_Point`）、NFKC 全角折叠绕过以及 JSON 键名走私。
- **高风险审批绑定规范化参数哈希**：人工审批或执行授权必须绑定 `(action, target, canonical_args_hash)`，防止参数篡改后复用旧审批。
- **锁定工具定义与沙箱隔离**：校验 MCP 工具目录摘要（防 Tool Poisoning / Rug-Pull 漂移），命令与代码执行必须放在资源受限、无宿主机凭据的沙箱中。
- **防范“只读工具组合”数据外泄**：即使封死全部写工具，只要同一会话同时具备内部敏感数据读取与外部联网能力（`web_fetch` / 联网搜索），被注入的 Agent 仍可通过 URL Query 或搜索词外泄数据——高密级会话必须隔离出网或施以域名白名单。
- **禁止按工具名子串判定只读**：绝不能因工具名含 `read`/`get`/`check` 就放行只读——默认将所有工具视为 `mutating`，仅依据签名能力清单的显式白名单降级为只读。

## 6. 强制安全验证（先红后绿 / Red-before-Green）

纯文字安全规范撑不过长会话上下文压缩。任何触及认证、授权、租户隔离、文件路径、出站 HTTP、密码学、反序列化或 Agent 工具边界的 PR **必须**满足：

1. **至少一条反向安全单测**：用真实代码证明非法 Token、跨租户 ID、`../` 路径、软链逃逸、内网 SSRF URL、篡改参数或缺失密钥被**显式拒绝**（`401`/`403`/`ValueError`），而不是只测正常路径。
2. **确定性静态与密钥扫描**：合入前运行语言安全检查（如 Ruff `S` 规则 / Bandit / Semgrep / ESLint 安全规则）与密钥扫描——缺少工具必须非零退出（`NOT_RUN`），严禁绿色跳过。
3. **禁止把生产真实敏感数据喂给 Coding Agent**：使用脱敏 Fixture、Data Card 或密封数据沙箱，绝不让 Agent 直接读取生产库或真实密钥文件。

## 7. 工程承载：如何用 `deps` 在本地强制落地本标准

本标准定义**“必须守住什么”**；Rust 工具 **`deps`** 作为 `agentic-sdlc` 的本地**工程承载（Engineering Carrier）**，在毫秒级开发循环里把关键安全边界变成确定性门禁：

| `agentic-sdlc` 中的安全要求 | `deps` 提供的确定性工程承载 |
|---|---|
| 禁止真实敏感数据集 / PII 进入 Coding Agent 上下文 | 兄弟项目 `sealed-data` 的 **`sealed-data seal`** + MCP `sealed_data_card` / `sealed_data_run`（写入 Claude deny 规则与 OS 沙箱 `denyRead`，让 Agent 只看审批后的 Data Card 与脱敏结果编程） |
| 拦截密钥字面量、Vault 引用错误与 Prompt Injection | **`deps security-audit`** / **`deps security-filter`**（不读取也不回显密钥明文，校验 Vault 引用与确定性注入拦截） |
| 阻止未授权跨边界依赖与架构漂移 | **`deps aac check`** / **`deps aac reconcile --strict`**（Tree-sitter 毫秒级本地架构合规编译） |
| 核对 API 路由/调用、消息队列与 SQL/ORM 语义血缘 | **`deps lineage`** / **`deps lineage-audit`**（基于源码证据的 `deps.semantic-lineage.v1` IR 审计） |
| 生成不可自证、可复验的交付回执 | **`deps agent-verify --receipt`**（显式 `PASS`/`FAIL`/`NOT_RUN`/`CONFLICT`、`does_not_prove[]` 与 SHA-256 `receipt_digest`） |

## 相关文档

- 一页安全 PR 审查清单：[checklists/secure-vibe-coding-review.zh.md](../checklists/secure-vibe-coding-review.zh.md)
- 非权威 Agent 技能投影：[skills/secure-vibe-coding/SKILL.md](../skills/secure-vibe-coding/SKILL.md)
- 测试策略与门禁完整性：[testing-strategy.zh.md](testing-strategy.zh.md)
