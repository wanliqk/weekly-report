# 模块说明

> 状态：V1 模块已实现；第二版 BE-10A/BE-10B/BE-10C 后端模块已实现，Electron/Vue 界面待 FE-10
> 更新日期：2026-08-07

本文件说明目标模块边界。模块被列出不表示对应代码已经存在或完成；实际进度以当前工作树、`progress.md` 和 `task.md` 为准。

> CR-20260807-01 的模块边界见第 9 节；第 2 节保留 V1 历史快照。BE-10A 已完成 M03 数据基线、M05 双账号/强制改密及 M21 审计表；BE-10B 已完成 M06 安全删除、M08/M18 日报聚合与日期归档、M19/M21 管理员撤销与审计；BE-10C 已完成 M09/M11/M20 的日期级正式来源适配和统计查询。业务事务状态以 `task.md` 为准。

## 1. 工程模块

```text
weekly-report/
├─ electron/                   # electron-vite 工程根
│  ├─ src/main/                # Electron Main、sidecar 生命周期
│  ├─ src/preload/             # 安全运行时桥接
│  ├─ src/renderer/            # Vue 3 渲染进程
│  ├─ electron.vite.config.ts
│  └─ electron-builder.yml
├─ backend/                    # FastAPI；目标包含迁移和后端测试
├─ build/                      # 打包说明；目标包含 sidecar、图标、安装器与许可证
├─ docs/                       # 原始需求与技术方案
├─ ai-docs/                    # 架构基线、规范、任务与评审依据
└─ package.json                # npm workspace 根入口
```

### 1.1 当前工程状态（2026-08-06）

- `electron/` 已有 main/preload/renderer、安全 Token 桥接、鉴权 Store/Router/API client、初始化/登录/应用布局、用户管理、模板管理、日报工作台/动态表单页面、导出保存对话框白名单、周报列表/编辑/来源页面和设置页面（自动归档、企业微信占位、管理员整库备份保存对话框白名单）。
- `backend/` 已有 FastAPI 应用工厂、数据库/迁移、统一响应与异常、认证依赖，以及初始化、认证、用户管理、模板、设置、日报、导出、周报和手动整库备份的 API/Service 实现（手动备份因不落业务表，无独立 Repository 层，属 `database.md` §6 记录的既定例外）。
- 阶段 4、阶段 5、阶段 6、阶段 7、阶段 8、阶段 9 均已完成并通过独立审查（阶段 6、阶段 7、阶段 8 含专项安全审查）。V1 规划的全部 9 个阶段现已交付。
- `build/sidecar/weekly-report-backend.exe` 已由真实 PyInstaller `onedir` 构建产出并验证；`electron/dist/win-unpacked/`、`electron/dist/weekly-report-0.1.0-setup.exe` 已真实构建并完成本机安装/升级/卸载验证。

## 2. 目标业务与平台模块

| ID | 模块 | 职责 | 依赖 | 明确禁止 |
|---|---|---|---|---|
| M01 | Desktop Bootstrap | `electron/src/main` 中实现单实例、窗口、sidecar 启停、健康检查、路径、保存对话框 | Electron、electron-vite、Runtime | 承载业务规则、访问 SQLite |
| M02 | Runtime Bridge | preload 白名单、API 基址、运行期头、Token 安全存取 | M01 | 通用 IPC、任意文件/命令能力 |
| M03 | Persistence | Engine/Session、PRAGMA、ORM、迁移、自动备份和手动备份快照 | SQLAlchemy/Alembic | 依赖 API/页面、包含状态机 |
| M04 | API Foundation | 应用装配、统一响应/异常、请求 ID、鉴权依赖 | M03 | 直接写 ORM |
| M05 | Auth | 初始化、登录、JWT、token_version、改密、退出 | M03、M04 | 将 Token 写普通存储 |
| M06 | User Admin | 用户查询、创建、角色/状态修改、重置密码、末位管理员保护 | M05 | 查看他人业务内容 |
| M07 | Template | 默认模板、字段规则、不可变版本发布和历史摘要 | M03、M05 | 原地修改历史版本 |
| M08 | Daily Report | 创建、快照、草稿保存、状态机、查询、详情 | M07、M10 | 读取当前模板解释历史日报 |
| M09 | Weekly Report | 周范围、可用性、生成、编辑、来源、重生成 | M08 | 汇总未归档日报、反写日报 |
| M10 | Settings/Capabilities | 自动归档、固定时区、功能开关 | M05 | 定义企业微信同步 API |
| M11 | Export | 条件校验、动态列规划、Excel 任务和清理 | M08、M01 | 导出未归档/他人数据 |
| M12 | Frontend Shell | `electron/src/renderer` 中实现路由、布局、鉴权守卫、HTTP 客户端、全局反馈 | M02、M04 | 复制后端业务规则 |
| M13 | Daily UI | 日报列表、动态表单、提交归档交互 | M08、M12 | 绕过 API 直接访问本地数据 |
| M14 | Template UI | 模板字段编辑、校验提示、版本展示 | M07、M12 | 生成或修改 field_key |
| M15 | Weekly UI | 周选择、可用性、编辑、来源追溯、覆盖确认 | M09、M12 | 未确认调用 regenerate |
| M16 | Admin/Settings UI | 用户管理、个人设置、企业微信占位 | M06、M10、M12 | 展示他人业务数据入口 |
| M17 | Packaging/Release | electron-vite `out/`、PyInstaller sidecar、electron-builder `extraResources`、安装包、升级与许可证 | M01、全部构建产物 | 将数据写安装目录；将 sidecar 放入 ASAR |

### 2.1 当前实现矩阵（2026-08-06）

| 模块 | 状态 | 当前事实 / 下一缺口 |
|---|---|---|
| M01 Desktop Bootstrap | 部分完成 | 已有单实例、安全窗口、sidecar 启停、动态端口、健康等待、退出清理（`taskkill /t /f`）、保存对话框白名单（`ExportFileSaver`，阶段 6 `DESK-04`）；缺生产运行期目录的实际落地验证（依赖阶段 9 `PKG-01` 产出真实二进制） |
| M02 Runtime Bridge | 部分完成 | preload 已暴露受限 `runtimeBridge.{sidecar,api,token,exportFile}`；Token 由 Main `safeStorage` 加密持久化且不可用时不明文回退；导出下载保存白名单已实现（阶段 6 `DESK-04`），写入路径始终取自系统对话框返回值 |
| M03 Persistence | DONE | 已有异步 Engine/Session、PRAGMA（WAL/FK/busy_timeout/synchronous）、8 张表 ORM Model、Alembic 初始迁移、迁移前备份+轮转+路径边界校验；各业务模块 Repository 均已落地；手动整库备份（`BACKUP-01`，阶段 8）已实现，按设计不落业务表，改用进程内 `BackupRegistry` + 启动清理 |
| M04 API Foundation | 部分完成 | 已有应用工厂、精确 CORS/Host、请求 ID、runtime secret、JWT/当前用户/admin 依赖、达标 `/health`、统一响应与异常；其余具体业务错误码随对应模块实现 |
| M05 Auth | DONE | 初始化、24h JWT、持久化签名密钥、`token_version`、登录、当前用户、改密和退出均已实现、通过门禁和独立审查 |
| M06 User Admin | DONE | 用户分页查询、创建、角色/状态修改、重置密码和末位有效管理员保护已实现、通过门禁和独立审查 |
| M07 Template | DONE | 六类字段规则、稳定键、核心字段、不可变版本发布和历史摘要已实现并通过独立审查 |
| M08 Daily Report | DONE | 所有权过滤、创建/快照、稳定查询、草稿保存、提交/归档、自动归档和乐观锁已实现并通过独立审查 |
| M09 Weekly Report | DONE | 自然周校验、仅归档来源、同周唯一（含并发）、来源快照、人工编辑不反写日报、确认后原子重生成均已实现并通过独立审查（含专项安全审查） |
| M10 Settings/Capabilities | DONE | 自动归档设置、固定 Asia/Shanghai 和 `wecom_sync:false` API 已实现并通过独立审查 |
| M11 Export | DONE | 导出条件互斥/归档所有权校验、跨模板动态列合并消歧、xlsx 线程卸载生成、24h 懒过期与启动清理、路径边界校验均已实现并通过独立审查（含专项安全审查，修复公式注入） |
| M12 Frontend Shell | DONE | 鉴权 Store/Router、API client（含二进制下载与 CORS 错误体解码）、40102 处理、应用布局、登录/初始化流程与安全 Token 桥接已实现、通过门禁和独立审查 |
| M13 Daily UI | DONE | 日报列表/筛选/创建、动态表单、草稿、提交/归档确认、冲突反馈及勾选/筛选导出交互已实现并通过独立审查 |
| M14 Template UI | DONE | 模板字段编辑/排序/启停、类型组件和版本历史已实现并通过独立审查 |
| M15 Weekly UI | DONE | 周范围选择、逐日可用性、生成、编辑保存、来源跳转和重新生成醒目确认已实现并通过独立审查 |
| M16 Admin/Settings UI | DONE | 用户管理、个人设置（自动归档开关、固定时区展示）、企业微信占位（零外部请求本地提示）和管理员整库备份创建/保存入口均已实现并通过独立审查（含专项安全审查） |
| M17 Packaging/Release | DONE | electron-vite `out/`、PyInstaller `onedir` sidecar、electron-builder `extraResources`、NSIS 安装包均已真实产出；本机完成安装/升级/卸载验证（无独立干净虚拟机，已与用户确认该限制）；过程中发现并修复三个真实缺陷（sidecar 生产环境变量注入缺失、主进程模块打包遗漏、npm workspace 作用域包名导致安装产物异常，见 `issues.md` ISS-014/ISS-015/ISS-016）；代码签名和正式多杀软兼容性矩阵测试仍未做（非阻塞，`issues.md` RISK-003） |

## 3. 后端模块内部契约

每个业务模块采用以下结构；简单模块可合并文件，但职责不可合并：

```text
app/
├─ api/v1/<module>.py          # HTTP 契约
├─ schemas/<module>.py         # 输入、输出和领域值对象
├─ services/<module>.py        # 业务规则与事务
├─ repositories/<module>.py    # 数据访问和所有者过滤
└─ models/<module>.py          # ORM 映射
```

- API 只接受/返回 schema；禁止返回 ORM 实例的隐式序列化结果。
- Service 的公开方法代表一个业务用例，并明确事务边界。
- Repository 接口必须接收 `owner_id` 或使用已绑定当前用户的上下文。
- 跨模块调用优先调用对方 Service 的明确领域方法，禁止直接读写对方 Repository。

## 4. 前端页面与模块映射

| 路由 | 页面能力 | 后端模块 |
|---|---|---|
| `/setup` | 首次管理员初始化 | M05 |
| `/login` | 登录 | M05 |
| `/daily` | 日报列表和筛选 | M08 |
| `/daily/new` | 选择日期并创建 | M08 |
| `/daily/:id` | 动态表单、保存、提交、归档 | M07、M08、M10 |
| `/templates` | 当前模板配置和版本摘要 | M07 |
| `/weekly` | 周报列表、周选择、可用性 | M09 |
| `/weekly/:id` | 周报编辑、来源和重生成 | M09 |
| `/settings` | 自动归档、能力占位和 admin 手动备份入口 | M03、M10 |
| `/admin/users` | 用户管理 | M06 |

## 5. 跨模块关键流程

### 5.1 创建与提交日报

`Daily UI -> Daily API -> Daily Service -> Template Service/Repository -> Daily Repository -> DB`。

- 创建在一个事务中读取当前模板版本、写日报、模板快照和空内容。
- 提交依据日报快照校验；若自动归档开启，在同一事务写提交和归档信息。

### 5.2 生成周报

`Weekly UI -> Weekly API -> Weekly Service -> Daily Repository -> Weekly Repository -> DB`。

- Availability 是只读预检；Generate 必须重新读取并校验来源，不信任预检缓存。
- 写入周报、来源关系、生成基线和当前内容必须在同一事务。

### 5.3 Excel 导出

`Daily UI -> Export API -> Export Service -> Daily Repository -> openpyxl -> Export Job -> Electron Save`。

- 后端负责选择与生成；Electron 仅负责将已下载文件保存到用户选择位置。
- 文件路径不出现在普通 API 响应中。

## 6. 模块完成定义（DoD）

模块只有同时满足以下条件才可标为完成：

- API/内部契约与 `api.md` 一致，无未登记的接口。
- 业务规则与所有权隔离有自动化测试。
- 错误码、日志脱敏、并发/重复点击行为有覆盖。
- 前后端联调完成，空态、加载、成功、失败和冲突状态可见。
- 没有跨层访问、循环依赖或绕过 Service 的写操作。
- 代码审查已通过，审查结论和遗留项写入 `task.md`。
- 当前阶段的适用质量门禁全部通过，`progress.md` 已记录实际结果，并创建独立 Conventional Commit；未获授权不得推送。

## 7. 责任边界

- 单个开发任务只能指定一个主责 Agent；跨模块任务拆成契约任务和各端实现任务。
- Agent 可修改任务范围内文件及必要测试，不得顺带重构未授权模块。
- 发现契约不足时先更新问题记录，由技术负责人修改设计文档后再继续。
- 并行 Agent 共享同一工作树；拆分时必须给出互斥文件范围，合并前由主责 Agent 统一验证，任何 Agent 都不得覆盖他人的未提交改动。

## 8. electron-vite 产物与责任映射

| 源码/配置 | 构建产物 | 主责任务 |
|---|---|---|
| `electron/src/main/**` | `electron/out/main/**` | DESK-02、DESK-03 |
| `electron/src/preload/**` | `electron/out/preload/**` | DESK-03 |
| `electron/src/renderer/**` | `electron/out/renderer/**` | FE-* |
| `electron/electron.vite.config.ts` | 三端构建规则 | GOV-01/相关任务，变更需桌面架构评审 |
| `electron/electron-builder.yml` | Windows 安装包规则 | PKG-01 |
| PyInstaller `onedir` | `process.resourcesPath/sidecar/**` | PKG-01、DESK-02 |

## 9. 第二版目标模块与页面映射

### 9.1 模块变更

| 模块 | 第二版职责 | 依赖 | 禁止事项 |
|---|---|---|---|
| M05 Auth | 双账号 bootstrap、固定 admin、强制改密依赖 | M03、M04 | 复制密码哈希、业务 API 绕过强制改密 |
| M06 User Admin | 原 CRUD + 安全删除、末位管理员/当前账号保护 | M05、M21 | 级联删除有业务用户 |
| M08 Daily Entry | 同日多篇、创建幂等、草稿保存/删除、提交 | M07、M18 | 单篇归档、提交自动归档 |
| M18 Daily Day | 月历摘要、日期容器、正式快照、日期级归档事务 | M08 | 忽略草稿归档、部分提交 |
| M19 Admin Daily | 待撤销元数据、撤销提交、审计查询 | M05、M18、M21 | 查询或返回他人正文 |
| M20 Statistics | 当前用户月份日历、完成率、篇数、连续天数 | M18、M09 | 全员排名、工作日口径 |
| M21 Audit | 管理员动作白名单审计 | M03、M05 | 正文、模板快照、凭证入审计 |
| M09 Weekly Report | 仅按日期级正式日报生成与追溯 | M18 | 直接汇总来源条目 |
| M10 Settings/Capabilities | 固定时区、企业微信占位、备份入口 | M05 | 自动归档开关、假 AI 配置 |
| M11 Export | 一日期一正式记录、多来源值稳定渲染 | M18、M01 | 来源条目重复导出 |
| M13 Daily UI | 我的日报月历、条目卡片、日期归档与正式快照 | M08、M18、M12 | 只靠颜色表达状态 |
| M15 Weekly UI | 我的周报、日期正式来源跳转 | M09、M12 | 本次发起 AI 请求 |
| M16 Admin/Settings UI | 日报管理、用户删除、设置与备份 | M06、M19、M10、M12 | 普通用户显示 admin 入口 |
| M22 Statistics UI | 月历、指标卡、口径说明与日期跳转 | M20、M12 | 客户端自行聚合全量正文 |

### 9.1a 第二版模块实现状态（2026-08-07，随 `BE-10C` 更新）

| 模块 | 状态 | 事实 |
|---|---|---|
| M05 Auth | DONE（后端） | 双账号 bootstrap、固定 admin、强制改密依赖已随 `BE-10A` 实现；Electron 强制改密页面待 `FE-10` |
| M06 User Admin | DONE（后端） | 原 CRUD（`USER-01`）+ 安全删除（`BE-10B`：无业务记录物理删除、有记录 `40910`、当前账号/末位管理员保护、确认用户名精确匹配、`can_delete`/`cannot_delete_reason` 提示字段）均已实现；Electron 用户删除入口待 `FE-10` |
| M08 Daily Entry | DONE（后端） | `client_request_id` 幂等创建（跨用户/跨日期复用返回 `40908`，响应含 `created` 标记）、草稿保存/物理删除（含清理空日期容器）、提交不自动归档均已实现并通过并发测试 |
| M18 Daily Day | DONE（后端） | 月历摘要（`GET /daily-report-days?month=`，稀疏返回、含 `day_id`）、日期详情（含正式快照）、日期级归档事务（日期行并发互斥、聚合全部已提交条目）均已实现；Electron 月历 UI 待 `FE-10` |
| M19 Admin Daily | DONE（后端） | 待撤销元数据列表（原始列选择不触碰正文）、撤销提交（`{version,reason}`）、审计查询（按 action/日期过滤）均已实现并通过独立安全审查；Electron 管理界面待 `FE-10` |
| M20 Statistics | DONE（后端） | `GET /statistics/monthly?month=` 已实现（`BE-10C`）：当前/历史/未来月分母、完成率、`daily_report_count`/`weekly_report_count`、今天/昨天连续记录规则均有纯函数与服务级测试覆盖；Electron 统计页待 `FE-10` |
| M21 Audit | DONE（后端） | `daily_submission_revoked`/`user_deleted` 两类白名单审计写入均已实现，`metadata_json` 只含结构化白名单字段 |
| M09 Weekly Report | DONE（后端） | 已随 `BE-10C` 改读 `daily_report_days.archive_snapshot_json` 的日期级正式快照，`WeeklyDay` 支持一日期多来源 `entries[]`，`availability` 按日期容器状态推导；Electron 周报页仍是 V1 展示形状，适配待 `FE-10` |
| M11 Export | DONE（后端） | 已随 `BE-10C` 改为按 `daily_report_day_ids`/日期范围选择 `daily_report_days.status='archived'`，一日期一行，多来源字段按 `[1]`/`[2]` 编号合并、单来源保持原始类型；Electron 导出交互仍按条目 ID 选择，适配待 `FE-10` |
| M13/M15/M16/M22 UI | 未实现 | 全部第二版 Electron/Vue 页面待 `FE-10` |

### 9.2 第二版路由

| 路由 | 页面 | 权限 |
|---|---|---|
| `/setup` | 创建首次普通用户，服务端自动创建 admin | 未初始化 |
| `/change-password` | 临时密码强制修改 | 登录且 `must_change_password` |
| `/daily` | 我的日报月历和选中日期详情 | 登录 |
| `/daily/new?work_date=...` | 创建指定日期条目 | 登录、日期开放 |
| `/daily/:id` | 来源条目编辑/只读详情 | 所有者 |
| `/weekly`、`/weekly/:id` | 我的周报 | 登录 |
| `/statistics` | 个人统计 | 登录 |
| `/settings` | 设置 | 登录 |
| `/admin/daily-reports` | 待归档条目撤销和审计 | admin |
| `/admin/users` | 用户增删改查 | admin |

第二版代码完成状态以 `task.md`/`progress.md` 为准；BE-10A 之外的模块职责仍是待实现契约，禁止提前标作 DONE。
