# Secure Vibe Coding 安全代码审查清单

**状态**: accepted baseline
**更新日期**: 2026-11-20
**English**: [secure-vibe-coding-review.md](secure-vibe-coding-review.md)
**权威标准**: [standards/secure-vibe-coding.zh.md](../standards/secure-vibe-coding.zh.md)

> **现实痛点**：Coding Agent 的默认目标是尽快让主路径跑通。若无硬约束，它会顺手写出 `os.getenv("SECRET", "dev")`、漏掉服务端租户过滤、直接 `requests.get(url)` 允许重定向、用 `except Exception` 吞掉鉴权失败，或编造一个不存在的依赖包名。凡触及安全面的 diff，合并前逐项核对本清单——并强制附带至少一条**反向安全单测**证明攻击会被真实拦截。

---

## 1. 认证、授权与防 Fail-Open

- [ ] **默认拒绝（Fail-Closed）**：缺失鉴权、Token 过期/非法、未知角色或查询异常一律返回 `401`/`403`，绝不回落放行。
- [ ] **服务端强制租户与对象归属校验（防 IDOR）**：所有数据库查询按已认证的 `tenant_id`/owner 过滤，绝不信任客户端传入的租户/用户 ID 或仅前端隐藏入口。
- [ ] **安全边界禁止裸 `except Exception`**：策略、鉴权和校验路径不静默吞错，不用兜底值把拒绝变成允许。
- [ ] **严格 JWT / Token 校验**：校验签名、显式算法白名单（禁 `alg=none`）、`exp`/`iss`/`aud`；密钥与 MAC 比对用常量时间函数（`hmac.compare_digest`）。
- [ ] **安全 CORS 与 Cookie**：严禁 `CORS *` 与 `credentials: true` 同时开启；会话 Cookie 开启 `HttpOnly`/`Secure`/`SameSite`；基于 Cookie 的写接口有 CSRF 防护。

## 2. 注入、SSRF、路径穿越与 ReDoS

- [ ] **全参数化查询**：零字符串拼接构造 SQL / Cypher / LDAP / NoSQL。
- [ ] **禁止 `shell=True` 与动态执行**：子进程使用参数数组；零 `eval` / `exec` / 未转义模板注入。
- [ ] **路径收敛检查**：文件读写与解压先 `resolve()` 校验仍在根目录内，显式拒绝 `..`、前导 `/`、控制字符与逃逸软链接。
- [ ] **出站 HTTP 防 SSRF**：受用户或 LLM 影响的 URL 仅放行 `https`、拦截回环/私网/链路本地/云元数据 IP（`169.254.169.254`）、禁用隐式重定向、设超时与响应体上限。
- [ ] **安全解析与渲染**：不可信数据禁 `pickle` 与不安全 `yaml.load`；禁原始 HTML/SVG 注入（`dangerouslySetInnerHTML`）；不可信文本上的正则必须线性时间并截断长度。

## 3. 密钥与密码学运营卫生

- [ ] **零硬编码兜底密钥**：无 `os.getenv("KEY", "default-secret")`、无提交 `.env`/私钥；缺少必填密钥时启动直接失败。
- [ ] **零明文密钥泄漏**：Token、密码、私钥不出现在日志、异常堆栈、HTTP 报错、数据库明文字段、Docker 镜像层或 LLM Prompt 中。
- [ ] **禁自造密码与弱算法**：只用标准库（`cryptography`/WebCrypto/RustCrypto）；密码不用 MD5/SHA1、禁用 ECB、禁止固定 IV/Nonce、安全随机数用 `secrets`/CSPRNG 而非 `random`。
- [ ] **密钥隔离与 TLS 校验**：不同用途/环境隔离密钥、使用 AEAD 或 Encrypt-then-MAC、绝不关闭 TLS 证书校验（禁止 `verify=False`）。

## 4. 供应链与 CI 加固

- [ ] **核验每个新增依赖（防 Slopsquatting）**：确认包真实存在、维护者与上游仓库可信，并锁定版本与哈希。
- [ ] **锁定 CI Workflow**：GitHub Actions 锁定到 40 位 commit SHA、`permissions: contents: read`、`persist-credentials: false`、支持时启用 `--require-hashes`。
- [ ] **禁止运行期联网装包**：容器启动与 Agent 工具绝不在运行时执行 `curl | sh` 或未锁定装包。

## 5. Agent / LLM 应用边界（如适用）

- [ ] **不可信数据不直连危险 Sink**：LLM 输出与外部工具结果必须过闭合 Schema 与策略门禁后才能触碰 SQL、Shell、HTTP 或写文件。
- [ ] **加固不可信定界**：边界标记能防 Unicode 隐身字符（`Cf`/默认可忽略字符）与 NFKC 折叠；证据提取基于结构化解析而非全文正则。
- [ ] **参数哈希绑定审批与工具摘要锁**：高风险审批绑定 `(action, target, canonical_args_hash)`；MCP 工具目录锁定摘要防 Rug-Pull 漂移。
- [ ] **密封开发数据**：Coding Agent 只基于合成 Fixture 或密封 Data Card 开发（例如通过 `sealed-data seal` + `deps security-audit`），绝不直接读取真实生产密钥或原始客户数据。

## 6. 高频反模式速查表（`绝不这样写 -> 永远这样写`）

| 绝不这样写 | 永远这样写 | 原因 |
|---|---|---|
| `except:` | `except SpecificError as e:`（至少 `except Exception as e:`） | 裸 `except:` 会吞掉 `SystemExit`/`KeyboardInterrupt`，导致进程杀不死 |
| `except Exception: pass` | 记录日志、重抛或明确拒绝（`401`/`403`） | 静默吞错会把鉴权/校验失败变成放行 |
| `SECRET_KEY = os.getenv("SECRET_KEY", "dev")` | 必填配置，缺失直接启动失败 | 硬编码开发兜底密钥极易悄悄带上生产 |
| `api_key = key or "dummy"` | 直接抛 `401` / fail closed | 宁可快速失败，绝不用假凭据放行 |
| `allow_origins=["*"]` + `allow_credentials=True` | 从配置读取显式 Origin 白名单 | 通配 CORS + 凭据会直接造成跨站劫持 |
| `f"SELECT * FROM t WHERE id = {x}"` | 参数化查询 / 绑定变量 | 防止 SQL 注入 |
| `catch (e) { console.error(e) }` | 界面明确报错并保留用户输入 | 吞掉写操作失败会误导用户以为操作成功 |
| 安全审计日志单独开事务写入 | 将安全审计记录随主变更放在同一事务内提交 | 防止敏感写操作成功却丢掉审计记录 |

## 7. 合并 AI 代码前必问的七个安全问题

1. 当认证、授权或策略查询**失败或超时**时，代码是明确拒绝还是悄悄放行？
2. 租户 A 的合法用户改一个请求里的 ID，能不能读到或改掉租户 B 的数据？
3. 本次新增接口、解析器或工具里，有没有把不可信输入送进 URL、文件路径、Shell 参数、正则或反序列化？
4. diff 里有没有混入硬编码兜底密钥、弱加密算法、固定 IV 或 `verify=False`？
5. 如果新增了依赖包或 GitHub Action，是否已核实真实来源并锁定精确版本/SHA？
6. 是否至少补了**一条反向安全单测**，证明非法/恶意输入会被拒绝？
7. 确定性安全扫描（SAST / 密钥扫描 / `deps security-audit`）是否真实执行并返回退出码 `0`（而非跳过）？
