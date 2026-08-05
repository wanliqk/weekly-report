# 技术决策记录

> 更新日期：2026-08-06
> 说明：本文件汇总已经接受的决策，不在此发明新架构。变更核心决策必须先走 `architecture.md` 的架构变更门禁。

## 1. 已接受架构决策

| ID | 决策 | 状态 | 主要来源 | 实施约束 |
|---|---|---|---|---|
| ADR-001 | Electron 与 FastAPI 使用回环 REST 通信 | Accepted | `architecture.md`、`docs/方案设计.md` | 后端只监听 `127.0.0.1`；Vue 仅通过 API 访问业务数据 |
| ADR-002 | FastAPI 是唯一业务入口，Node/Electron 不承载业务规则 | Accepted | `architecture.md`、`AGENTS.md` | 写操作遵循 API→Service→Repository→Model/DB；Electron 不访问 SQLite |
| ADR-003 | SQLite 由单 sidecar、单 worker 独占访问 | Accepted | `architecture.md`、`database.md` | 禁止多 Uvicorn worker 和第二个数据库访问进程 |
| ADR-004 | 使用不可变模板版本与日报完整 JSON 快照 | Accepted | `requirements.md`、`architecture.md` | 模板变更不得改变历史日报；版本行禁止原地更新/删除 |
| ADR-005 | 动态模板、日报和周报内容使用校验后的结构化 JSON | Accepted | `architecture.md`、`database.md` | JSON 写入前由版本化 schema 校验，不接受任意结构 |
| ADR-006 | API 使用 HTTP 状态与 `{code,msg,data}` 双层语义 | Accepted | `api.md`、`architecture.md` | 文件成功流为唯一例外；错误仍返回统一 JSON |
| ADR-007 | 本地认证采用 24h JWT 与 `token_version` | Accepted | `requirements.md`、`architecture.md` | 修改/重置密码或禁用账号后旧 Token 立即失效 |
| ADR-008 | V1 周报重生成须显式确认，确认后覆盖且不保留版本 | Accepted for V1 | `requirements.md`、`architecture.md` | 不得静默覆盖；版本历史留到 P2 |
| ADR-009 | Excel 使用任务记录加二进制下载 | Accepted | `architecture.md`、`api.md` | 后端生成并治理临时文件，普通 API 不返回内部路径 |
| ADR-010 | V1 所有数据库主键统一为 26 字符 ULID 文本 | Accepted | `architecture.md`、`database.md` | 不得混用 UUIDv7 或其他主键格式 |
| ADR-011 | 手动整库备份仅 admin 可用，通过短期下载文件交付 | Accepted | `requirements.md`、`architecture.md`、`api.md` | 备份含所有用户数据；随机 ID、15 分钟过期、界面明确提示敏感性 |
| ADR-012 | electron-vite 5 是唯一 Electron 开发/构建工具 | Accepted | `architecture.md`、`docs/方案设计.md` 工具链变更 | 源码固定在 `electron/src/main|preload|renderer`，产物固定在 `electron/out` |
| ADR-013 | Node.js 22.12+、npm 10+、根 npm workspace 是 JS 工具链基线 | Accepted | `architecture.md`、`AGENTS.md`、根 `package.json` | 使用根 `package-lock.json`；不在未评审时改用 pnpm |

## 2. 已接受产品与安全默认值

| ID | 决策 | 状态 | 来源 | 实施约束 |
|---|---|---|---|---|
| PROD-001 | V1 首发仅支持 Windows 10/11 x64 | Accepted for V1 | `requirements.md`、`docs/方案设计.md` | macOS/Linux 属于后续范围 |
| PROD-002 | admin 管理账号但默认不能查看其他用户业务正文 | Accepted | `requirements.md`、`api.md` | 管理接口只返回账号元数据；业务 Repository 仍按 owner 过滤 |
| PROD-003 | 日报状态固定为 `draft→submitted→archived`，归档后只读且不撤回 | Accepted for V1 | `requirements.md`、`database.md` | 自动归档必须在提交事务内完成 |
| PROD-004 | 自然周固定为 Asia/Shanghai 周一至周日，周报仅汇总 archived 日报 | Accepted | `requirements.md`、`api.md` | 未归档日报只作提示，空周允许创建周报 |
| PROD-005 | V1 模板支持 text、textarea、number、date、select、multiselect，无附件 | Accepted for V1 | `requirements.md`、`database.md` | 核心字段不可删除且至少启用一个 |
| PROD-006 | 企业微信仅提供本地“未开放”占位，不定义同步 API | Accepted for V1 | `requirements.md`、`api.md` | 不引入 SDK，不产生企业微信网络请求 |
| PROD-007 | 导出动态列按 `field_key` 首次出现顺序排列，表头取该字段最近一次出现的标签文本 | Accepted for V1 | `EXPORT-01` 实现（`requirements.md` 4.4 只给出“按稳定 `field_key` 合并、同名标签追加短标识”的原则，未定义具体排序/取值算法） | 历史新增字段追加在已见字段之后；`field_key` 不变时标签变化不拆列；两个不同 `field_key` 恰好得到相同表头文本才追加 `field_key` 后缀消歧 |
| PROD-008 | 导出文件内的 `Asia/Shanghai` 时间展示使用固定 UTC+8 偏移而非 `zoneinfo` | Accepted for V1 | `EXPORT-02` 实现 | 中国大陆自 1991 年后不施行夏令时，固定偏移在数值上等价且避免生产环境依赖可选的 `tzdata` 包（Windows 默认不含 IANA 时区数据库）；若产品未来需要真实多时区支持需新 ADR |
| SEC-001 | JWT 持久化使用 Electron safeStorage | Accepted | `architecture.md`、`AGENTS.md` | renderer 不写 `localStorage`/`sessionStorage`；不可用时必须显式失败或提示 |
| SEC-002 | 所有业务 API 同时校验 JWT 与 `X-Runtime-Secret` | Accepted | `architecture.md`、`api.md` | `/health` 是唯一例外；Main 随机生成，renderer API 客户端仅在内存持有，不得进入 Vite 变量、持久化存储或日志 |
| SEC-003 | V1 不做 SQLite 整库加密 | Accepted for V1 | `requirements.md`、`architecture.md` | 密码使用 Argon2id、Token safeStorage；若要求磁盘泄露防护需新 ADR |
| SEC-004 | 密码最小长度 8 位、最大 128 位（服务端统一校验） | Accepted for V1 | `AUTH-01` 实现（`docs/需求理解.md`/`docs/方案设计.md` 未给出具体数值） | 仅为输入校验基线，非完整密码复杂度策略；`bootstrap-admin`/`AUTH-02` 登录改密/`USER-01` 重置密码均须复用同一下限，不得各自定义 |
| SEC-005 | JWT HS256 签名密钥由后端首次启动随机生成并持久化于数据目录 | Accepted for V1 | `AUTH-02` 实现 | 使用 256-bit 随机密钥和独占创建；重启后复用，格式损坏时拒绝启动；不得硬编码、记录日志或经 renderer 暴露 |
| SEC-006 | 导出 xlsx 对以 `=` 开头的字符串单元格加前缀单引号转义，防止 Excel 公式注入 | Accepted for V1 | `EXPORT-02` 实现，专项安全审查发现 | 仅处理 `=` 前缀（openpyxl 只会把该前缀提升为公式）；不处理 `+`/`-`/`@`，避免破坏中文报告中常见的列表符号 |
| SEC-007 | CORS 响应头显式 `expose_headers=["Content-Disposition"]` | Accepted for V1 | `EXPORT-02` 实现，真实 Electron 联调发现 | 仅新增这一个响应头的跨域可见性；`allow_origins` 固定白名单、`allow_credentials=False` 不变，不构成新的跨域数据泄露面 |

## 3. 工程协作决策

| ID | 决策 | 状态 | 来源 | 实施约束 |
|---|---|---|---|---|
| GOV-001 | `v1` 是全新主线，只以当前工作树和基线文档为依据 | Accepted | `AGENTS.md` | 未经用户授权不得查看或引用其他分支及 Git 历史实现 |
| GOV-002 | 每个技术阶段通过质量门禁后创建独立 Conventional Commit | Accepted | 用户指令、`AGENTS.md` | 当前阶段不得混入下一阶段；本地提交不代表允许推送 |
| GOV-003 | 任务可按 Agent A/B/C 划分，每项只有一个主责 Agent | Accepted planning convention | 用户指令、`modules.md` | 依赖未满足不得抢跑，共享文件改动先协调 |

## 4. 决策变更流程

以下变化必须先记录动机、备选方案、兼容性和迁移影响，并由技术负责人批准：

- 技术栈、数据库、桌面或后端框架替换。
- API 权限/错误码/状态语义、数据所有权或日报状态机变化。
- 表拆并、主键策略、模板快照、周报来源/覆盖语义变化。
- 数据目录、sidecar 生命周期、安全边界或打包结构变化。

批准后依次更新 `requirements.md`/`architecture.md`/`database.md`/`api.md`、`task.md`，最后修改代码。
