# 模块说明

> 状态：目标模块基线（V1；实现状态单独列示）
> 更新日期：2026-08-05

本文件说明目标模块边界。模块被列出不表示对应代码已经存在或完成；实际进度以当前工作树、`progress.md` 和 `task.md` 为准。

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

### 1.1 当前工程状态（2026-08-05）

- `electron/` 已有 main/preload/renderer 骨架、Router、Pinia、Element Plus、Axios 和 Vitest 基线；仅有首页占位，尚无业务页面与 HTTP API 层。
- `backend/` 已有 FastAPI 应用工厂、配置、请求 ID、统一成功响应 schema、`GET /health` 与测试；Service、Repository、Model 目录仍为空壳。
- 尚无 Alembic 配置或迁移、数据库会话、认证和业务 API。
- `build/sidecar/` 仍为占位，尚未生成 PyInstaller 产物。

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

### 2.1 当前实现矩阵（2026-08-05）

| 模块 | 状态 | 当前事实 / 下一缺口 |
|---|---|---|
| M01 Desktop Bootstrap | 部分完成 | 已有单实例、安全窗口、sidecar 启停、动态端口、健康等待、退出清理（`taskkill /t /f`）；缺保存对话框白名单（阶段 6 `DESK-04`）和生产运行期目录的实际落地验证（依赖阶段 9 `PKG-01` 产出真实二进制） |
| M02 Runtime Bridge | 部分完成 | preload 已暴露 `runtimeBridge.{sidecar,api}`（状态查询/订阅/重试、API 基址与 runtime secret）；缺 Token 安全存取（`safeStorage`，阶段 4 `FE-01`）和下载保存白名单（阶段 6 `DESK-04`） |
| M03 Persistence | 未实现 | 只有依赖声明和目录占位；无 Engine/Session、ORM、Alembic、PRAGMA、备份 |
| M04 API Foundation | 部分完成 | 已有应用工厂、精确 CORS/Host、请求 ID、`RuntimeSecretMiddleware`、达标 `/health`（`version`+`Cache-Control: no-store`）和成功响应 schema；缺统一异常体系（422 归一化）和 JWT 鉴权依赖 |
| M05—M11 业务后端 | 未实现 | 尚无认证、用户、模板、日报、周报、设置、能力或导出接口 |
| M12 Frontend Shell | 部分完成 | 已有 Vue/Router/Pinia/UI 基线与首页；缺鉴权、API client、布局、全局错误处理 |
| M13—M16 业务前端 | 未实现 | 尚无对应页面与交互 |
| M17 Packaging/Release | 占位 | 有 electron-builder 配置和 sidecar 目录占位；无 PyInstaller/安装升级验证闭环 |

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
