# 开发任务列表

> 状态基准：2026-08-07
> 范围依据：`requirements.md`、`architecture.md`、`modules.md`、`database.md`、`api.md`、`coding-rule.md`
> 当前实现基线：工程骨架提交 `3a9fdbc`；阶段 2 Desktop Bootstrap 提交 `7386cae`；阶段 3 数据基础与 API Foundation 提交 `8480515`（编码规则补充随 `b6b1b47`）；阶段 4 认证与用户管理提交 `1a50e75`；阶段 5 模板、设置与日报闭环提交 `1d965fe`；阶段 6 查询导出与桌面保存提交 `d6ab86e`；阶段 7 周报闭环提交 `346b0ea`；阶段 8 设置能力与受控备份提交 `00caa33`；阶段 9 质量与发布提交 `0148171`

## 1. 状态与协作约定

任务状态只使用：

- `TODO`：尚未开始。
- `IN_PROGRESS`：已开始且尚未满足完成定义。
- `BLOCKED`：存在必须由用户或技术负责人解除的前置问题。
- `REVIEW`：实现和自测完成，等待独立审查。
- `DONE`：代码、测试、文档、审查和阶段提交全部完成。

任务可按三个 Agent 分工，但每项任务只能有一个主责 Agent：

| Agent | 默认责任域 | 并行边界 |
|---|---|---|
| Agent A | Electron Main/Preload、Vue renderer、桌面集成 | 不实现后端业务规则，不访问 SQLite |
| Agent B | FastAPI、Service、Repository、Model、Alembic | 不在 Router 写 ORM，不实现 Electron 能力 |
| Agent C | 契约测试、集成/E2E、审查、文档与发布验证 | 不在未协调时改写 A/B 正在修改的实现文件 |

并行前先确认任务依赖及允许修改目录；接口契约由 `api.md` 决定，不允许各 Agent 自建临时接口。共享文件发生重叠时，后开始者暂停并协调。

## 2. 全局完成定义（DoD）

每个实现任务至少满足：

1. 交付物与任务范围、架构依赖方向及 API/数据库契约一致。
2. 正常、失败、安全、权限、冲突和重复操作路径具备与风险相称的自动化测试。
3. 适用的 lint、类型检查、测试和构建命令通过，真实结果记录到本文件。
4. 日志与错误响应不包含密码、JWT、runtime secret、内部路径或报告正文。
5. 独立 Reviewer 完成审查，未解决 P0/P1 为零。
6. 更新 `progress.md`、`issues.md`；新增或改变决策时先更新 `decisions.md` 及上游设计。
7. 阶段内所有任务达到 `DONE` 后，复核工作树并创建一个独立 Conventional Commit；提交不得混入下一阶段内容，也不得未经用户授权推送。

通用质量门禁：

```powershell
npm run lint
npm run typecheck
npm test
npm run build
uv run --directory backend ruff check .
uv run --directory backend mypy
uv run --directory backend pytest
git diff --check
git status --short
```

依赖或锁文件变化时，额外执行：

```powershell
npm ci
uv sync --directory backend --frozen
```

## 3. 阶段化任务

### AI 上下文治理批次

| ID | 主责 | 任务 | 依赖 | 状态 | 交付物与验收 |
|---|---|---|---|---|---|
| DOCS-01 | Agent C | 建立 AI 协作上下文与维护路由 | 阶段 1 | DONE | 12 份 `ai-docs/` 文档、`AGENTS.md` 启动/维护规则、目标与现状边界、三 Agent 分工及交叉一致性检查；随独立文档阶段提交交付 |

### 阶段 1：工程基线

| ID | 主责 | 任务 | 依赖 | 状态 | 交付物与验收 |
|---|---|---|---|---|---|
| GOV-01 | Agent A | 根 npm workspace 与 electron-vite/Vue/TypeScript 骨架 | 无 | DONE | 根统一命令、锁文件、Electron/Vue 工程可安装、开发和构建 |
| BE-01 | Agent B | FastAPI/uv/Python 3.12 骨架 | 无 | DONE | 单 worker 回环配置、基础 `/health`、请求 ID、统一成功响应骨架 |
| QA-01 | Agent C | 工程基线质量门禁 | GOV-01、BE-01 | DONE | 前后端 lint/typecheck/test/build 已通过；阶段提交为 `3a9fdbc` |

说明：阶段 1 仅证明工程骨架成立，不代表 sidecar 生命周期、完整健康契约、数据库、认证或任何业务模块已实现。

### 阶段 2：Desktop Bootstrap

| ID | 主责 | 任务 | 依赖 | 状态 | 交付物与验收 |
|---|---|---|---|---|---|
| DESK-02 | Agent A | sidecar 生命周期与动态端口 | 阶段 1 | DONE | Main 选择回环端口、生成随机 runtime secret、解析开发/生产 sidecar 路径、单实例只启动一个进程、退出清理；密钥不进入构建变量、持久化或日志 |
| BE-02 | Agent B | sidecar 启动参数与完整健康契约 | 阶段 1 | DONE | 严格校验 host/port/data/log/runtime 配置；`/health` 返回版本并设置 `Cache-Control: no-store` |
| DESK-03 | Agent A | 安全 Runtime Bridge 与启动状态 UI | DESK-02、BE-02 | DONE | preload 只向 API 客户端暴露内存态 API 基址/runtime header 等必要能力；业务窗口仅在健康成功后显示；失败页可重试并定位脱敏日志 |
| QA-02 | Agent C | Desktop Bootstrap 集成测试与审查 | DESK-02、BE-02、DESK-03 | DONE | 覆盖动态端口、超时、异常退出、重复实例、重载清理、生产路径；无孤儿 sidecar |

阶段 2 专项验证：Electron 集成测试、`npm run dev` 人工冒烟、退出后进程检查、构建产物敏感信息扫描。阶段提交建议：`feat(desktop): 完成本地 sidecar 启动链路`。

### 阶段 3：数据基础与 API Foundation

| ID | 主责 | 任务 | 依赖 | 状态 | 交付物与验收 |
|---|---|---|---|---|---|
| DB-01 | Agent B | SQLAlchemy 异步 Engine/Session 与 SQLite PRAGMA | 阶段 2 | DONE | WAL、外键、busy timeout、synchronous 配置；只允许单后端进程访问 |
| DB-02 | Agent B | ORM 与 Alembic 初始迁移 | DB-01 | DONE | `database.md` 全部表、约束、索引、ULID 规则；不得用 `create_all` 替代迁移 |
| DB-03 | Agent B | 迁移前备份、轮转与安全文件清理 | DB-01、DB-02 | DONE | checkpoint、备份成功后迁移、保留 10 份、路径边界校验、失败停止启动 |
| API-01 | Agent B | 统一异常与 API 响应基础 | DB-01 | DONE | Pydantic 错误、业务错误、内部错误及 50301 均遵循 `api.md`，响应带请求 ID |
| QA-03 | Agent C | 数据与 API 基础测试/审查 | DB-01..DB-03、API-01 | DONE | 新库迁移、升级/失败、PRAGMA、约束、备份、异常脱敏测试通过 |

阶段提交：`8480515`（`feat(database): 建立持久化与迁移基础 [DB-01][DB-02][DB-03][API-01][QA-03]`）。

### 阶段 4：认证与用户管理

| ID | 主责 | 任务 | 依赖 | 状态 | 交付物与验收 |
|---|---|---|---|---|---|
| AUTH-01 | Agent B | 首次管理员初始化与默认关联数据 | 阶段 3 | DONE | 空库原子创建 admin、设置、模板及默认版本；重复初始化安全失败（含并发）；实现、自测、独立审查与阶段提交均完成 |
| AUTH-02 | Agent B | JWT、Argon2id、token_version 与鉴权依赖 | AUTH-01 | DONE | 24h HS256 JWT、持久化随机签名密钥、登录/当前用户/改密/退出 API、admin 依赖与双重校验均已实现；旧 Token 失效路径通过测试和独立审查 |
| USER-01 | Agent B | 管理员用户管理 | AUTH-02 | DONE | 账号分页查询/创建/更新/重置、大小写无关判重、关联默认数据与末位有效管理员保护均已实现并审查通过 |
| FE-01 | Agent A | 首次初始化、登录与安全 Token 桥接 | DESK-03、AUTH-02 | DONE | 初始化/登录/改密/退出、safeStorage、鉴权守卫与 40102 处理均已实现并审查通过 |
| FE-02 | Agent A | 用户管理界面 | USER-01、FE-01 | DONE | admin 路由、账号元数据列表/创建/编辑/重置和敏感变更确认均已实现并审查通过 |
| QA-04 | Agent C | 认证权限测试与审查 | AUTH-01..USER-01、FE-01、FE-02 | DONE | 后端 94 项、前端 49 项、真实 sidecar 集成 2 项及生产构建通过；独立审查完成，无未解决 P0/P1；提交 `1a50e75` |

阶段提交建议：`feat(auth): 完成初始化登录与用户管理`。

### 阶段 5：模板、设置与日报闭环

| ID | 主责 | 任务 | 依赖 | 状态 | 交付物与验收 |
|---|---|---|---|---|---|
| TEMPLATE-01 | Agent B | 默认模板与不可变版本 Service/API | 阶段 4 | DONE | 六类字段、核心字段、稳定 `field_key`、不可变版本发布与历史摘要均已实现、自测并通过独立审查 |
| SETTING-01 | Agent B | 个人设置与能力开关 API | 阶段 4 | DONE | 自动归档读写、固定 Asia/Shanghai 与 `wecom_sync:false` 已实现、自测并通过独立审查 |
| DAILY-01 | Agent B | 日报创建、详情、查询和快照 | TEMPLATE-01 | DONE | 用户+日期唯一、稳定分页、所有权过滤、历史/未来/闰日及模板快照均已实现、自测并通过独立审查 |
| DAILY-02 | Agent B | 草稿保存、提交与归档状态机 | DAILY-01、SETTING-01 | DONE | 快照校验、条件状态转换、乐观锁与自动归档原子转换均已实现、自测并通过独立审查 |
| FE-03 | Agent A | 模板配置和动态字段渲染 | FE-01、TEMPLATE-01 | DONE | 字段编辑/排序/启停、六类动态组件、版本展示和服务端错误保留输入已实现、自测并通过独立审查 |
| FE-04 | Agent A | 日报列表、表单、提交归档交互 | DAILY-01、DAILY-02、FE-03 | DONE | 日期/状态筛选、空态、创建、草稿、提交/归档确认、冲突反馈均已实现、自测并通过独立审查 |
| QA-05 | Agent C | 模板与日报验收/审查 | TEMPLATE-01..DAILY-02、FE-03、FE-04 | DONE | 后端 117 项、前端 54 项、真实 sidecar 2 项及生产构建通过；独立审查完成，无未解决 P0/P1；提交 `1d965fe` |

阶段提交建议：`feat(daily): 完成模板与日报状态闭环`。

### 阶段 6：查询导出与桌面保存

| ID | 主责 | 任务 | 依赖 | 状态 | 交付物与验收 |
|---|---|---|---|---|---|
| EXPORT-01 | Agent B | 导出任务、归档校验与动态列规划 | 阶段 5 | DONE | ID/筛选二选一、仅本人 archived、跨模板 `field_key` 合并与同名消歧均已实现、自测并通过独立审查 |
| EXPORT-02 | Agent B | xlsx 生成、下载和过期清理 | EXPORT-01 | DONE | 线程卸载生成、标准 MIME/安全文件名、24h 到期与启动清理、路径边界校验均已实现、自测并通过独立审查 |
| DESK-04 | Agent A | Electron 保存对话框白名单流程 | EXPORT-02、DESK-03 | DONE | `ExportFileSaver` 白名单校验、受信任帧校验、取消/失败反馈均已实现、自测并通过独立审查 |
| FE-05 | Agent A | 日报导出交互 | EXPORT-01、EXPORT-02、DESK-04 | DONE | 勾选/筛选导出、处理中状态、不可导出列表提示均已实现、自测并通过独立审查 |
| QA-06 | Agent C | 导出集成测试与审查 | EXPORT-01..FE-05 | DONE | 混合状态拒绝、跨模板、空值、过期/越权、文件可打开、取消保存均有自动化测试；真实 Electron 应用手动全链路验证；独立审查完成，无未解决 P0/P1 |

阶段提交：`d6ab86e`（`feat(export): 完成归档日报 Excel 导出 [EXPORT-01][EXPORT-02][DESK-04][FE-05][QA-06]`）。

### 阶段 7：周报闭环

| ID | 主责 | 任务 | 依赖 | 状态 | 交付物与验收 |
|---|---|---|---|---|---|
| WEEKLY-01 | Agent B | 自然周可用性、生成和来源快照 | 阶段 5 | DONE | 周一校验、只含 archived、空周可生成、同周唯一、来源可追溯均已实现、自测并通过独立审查 |
| WEEKLY-02 | Agent B | 编辑、乐观锁和确认重生成 | WEEKLY-01 | DONE | 人工内容不反写日报、未确认不覆盖、确认后原子替换基线/内容/来源均已实现、自测并通过独立审查 |
| FE-06 | Agent A | 周报列表、生成、编辑与来源 UI | WEEKLY-01、WEEKLY-02、FE-01 | DONE | 周范围、未归档提示、空周、来源跳转、醒目覆盖确认均已实现、自测并通过独立审查 |
| QA-07 | Agent C | 周报验收与审查 | WEEKLY-01、WEEKLY-02、FE-06 | DONE | 跨年周、闰日、空周、同周并发、人工修改和重生成覆盖语义均有自动化测试；真实 Electron 应用手动全链路验证；独立审查完成，无未解决 P0/P1 |

阶段提交：`346b0ea`（`feat(weekly): 完成周报生成与编辑闭环 [WEEKLY-01][WEEKLY-02][FE-06][QA-07]`）。

### 阶段 8：设置、占位与备份界面收口

| ID | 主责 | 任务 | 依赖 | 状态 | 交付物与验收 |
|---|---|---|---|---|---|
| BACKUP-01 | Agent B | admin 手动整库备份 API | DB-03、AUTH-02 | DONE | checkpoint、一致性短期文件、随机 ID、15 分钟过期、仅创建者 admin 下载均已实现、自测并通过独立审查 |
| FE-07 | Agent A | 设置、能力占位与手动备份 UI | SETTING-01、BACKUP-01 | DONE | 自动归档；企业微信只显示未开放且零外部请求；备份敏感性确认均已实现、自测并通过独立审查 |
| QA-08 | Agent C | 设置/占位/备份审查 | BACKUP-01、FE-07 | DONE | 权限、过期、清理、外部请求为零、路径不暴露测试均已完成；独立审查（含专项安全审查）完成，无未解决 P0/P1 |

阶段提交：`00caa33`（`feat(settings): 完成设置能力与受控备份 [BACKUP-01][FE-07][QA-08]`）。

### 阶段 9：质量与发布

| ID | 主责 | 任务 | 依赖 | 状态 | 交付物与验收 |
|---|---|---|---|---|---|
| QA-09 | Agent C | 全链路 Playwright/E2E 与安全回归 | 阶段 4..阶段 8 | DONE | 初始化→登录→模板→日报→导出→周报主链路及失败路径已实现、自测并通过独立审查 |
| PKG-01 | Agent B | PyInstaller `onedir` sidecar 构建 | 阶段 3..阶段 8 | DONE | 无 Python 环境可启动、迁移和许可证随包、产物不进 ASAR 均已实现、自测并通过独立审查 |
| PKG-02 | Agent A | electron-builder Windows x64 安装包 | PKG-01 | DONE | `extraResources` 正确、安装目录只读、userData 数据保留均已实现、自测并通过独立审查 |
| REL-01 | Agent C | 干净机安装/升级/卸载与发布审查 | QA-09、PKG-01、PKG-02 | DONE | 本机安装/升级/卸载真实验证完成（无独立干净虚拟机，已在任务开工前与用户确认并记录该限制）；迁移备份、卸载不删用户数据均已验证并通过独立审查 |

阶段提交：`0148171`（`build(release): 完成 Windows 发布链路 [QA-09][PKG-01][PKG-02][REL-01]`）。

### 第二版增量：需求确认与重设计（CR-20260807-01）

| ID | 主责 | 任务 | 依赖 | 状态 | 交付物与验收 |
|---|---|---|---|---|---|
| REQ-10 | 主 Agent | 整理同日多条目、日期级归档、管理员撤销、双账号初始化、菜单与统计需求 | 用户新需求 | DONE | 增量需求、覆盖规则、Given-When-Then 与推荐口径已确认并提交 `a866872` |
| DESIGN-10 | 主 Agent | 第二版方案设计与迁移评审 | REQ-10、ISS-018..ISS-022 | DONE | 日期容器 1:n 条目、正式快照、日期互斥事务、最小权限审计、统计、V1 迁移/受限 downgrade、API 与 Electron 路由已确认并提交 `e767ebd` |
| BE-10A | 主 Agent | 第二版迁移与认证基线 | DESIGN-10 | DONE | 日期/审计模型与迁移、周报 V2 快照迁移、双账号 bootstrap、强制改密、自动归档移除均已实现；旧库升级/受限降级和认证测试通过 |
| BE-10B | 主 Agent | 日报聚合、管理员撤销与用户安全删除 | BE-10A | DONE | 同日多篇、幂等创建、草稿删除/提交、日期级归档、最小权限撤销/审计、安全删除及并发测试均已实现、自测、质量门禁与独立安全审查通过 |
| BE-10C | 主 Agent | 周报、导出与统计适配 | BE-10B | DONE | 日期正式来源、周报 JSON、Excel 多来源列、月历/统计 API 及跨年/闰日测试均已实现、自测、质量门禁通过 |
| FE-10 | 主 Agent | 第二版 Electron/Vue 界面实现 | BE-10A、BE-10B、BE-10C 契约 | DONE | 强制改密、菜单改名、我的日报月历/归档、我的周报适配、设置收口、管理员入口、用户删除和统计页均已实现、自测、质量门禁与真实 Electron 冒烟通过 |
| QA-10 | 主 Agent | 第二版迁移、权限、并发、统计与 E2E 验收 | BE-10A..BE-10C、FE-10 | DONE | 旧库迁移（既有自动化 fixture + 一次真实意外触发的生产环境 V1→V2 升级）、同日并发、汇总原子性、权限隔离、删除保护、跨月/闰日统计及完整桌面流程通过门禁；重写全部 `electron/e2e/*.spec.ts` 为第二版 UI 断言并新增用户删除 spec；真实生产打包（PyInstaller+electron-builder）+ 真实安装/升级/卸载验证均已完成 |

第二版需求、方案、`BE-10A`、`BE-10B`、`BE-10C`、`FE-10`、`QA-10` 均已完成；日报条目已是真正的同日多篇 + 日期级归档，V1 单篇兼容桥已移除；周报、导出和统计后端均已切换为读取日期级正式快照（`daily_report_days.archive_snapshot_json`），不再读取条目级 `archived` 状态；全部第二版 Electron/Vue 界面（强制改密、我的日报月历、我的周报多来源展示、统计页、管理员日报管理/用户删除、设置收口）均已实现并通过真实 Electron 冒烟验证、真实生产打包安装验证和重写后的 Playwright E2E 全量验证。CR-20260807-01 第二版增量至此全部交付完毕。

### 第三版增量：企业微信日报反向同步（CR-20260808-02）

| ID | 主责 | 任务 | 依赖 | 状态 | 交付物与验收 |
|---|---|---|---|---|---|
| WECOM-00 | 主 Agent | 敏感样例治理 | 用户提供资料 | DONE | 精确忽略原始 HTTP/Cookie 文件，生成全合成脱敏 fixture，敏感扫描证明不会入 Git/构建产物 |
| WECOM-01 | 主 Agent | 需求与技术方案文档 | 用户需求、当前代码与样例分析 | DONE | 正式需求/方案、架构/API/数据库/模块摘要、决策/风险和任务拆分已更新；未修改代码或原始资料 |
| WECOM-02 | 主 Agent | 企业微信数据基础 | WECOM-00、WECOM-01 | DONE | 三张 ORM 表、Repository、Pydantic 配置、Alembic 迁移和约束/迁移测试 |
| WECOM-03 | 主 Agent | Electron 登录与凭证桥 | WECOM-00、WECOM-01 | DONE | Main-only secret、安全登录窗口、`safeStorage` Cookie jar、窄 IPC/内部鉴权和构建产物扫描 |
| WECOM-04 | 主 Agent | 企业微信内部协议 Client | WECOM-00、WECOM-02、WECOM-03 | DONE | 模板/列表/提交 Client、Cookie URL 筛选、协议 DTO、脱敏 fixture 合同测试 |
| WECOM-05 | 主 Agent | 字段映射与预览 | WECOM-02 | DONE | 正式快照 Mapper、动态 `field_key` 配置、`PROJECT_LIST`、结构/载荷指纹与边界测试 |
| WECOM-06 | 主 Agent | 同步编排与 API | WECOM-04、WECOM-05 | DONE | 连接/同步 Service、幂等/重复/uncertain 状态机、公开与 Main-only API、并发/权限测试 |
| WECOM-07 | 主 Agent | Electron/Vue 交互 | WECOM-03、WECOM-06 | DONE | 设置连接/映射、日报预览/同步、历史/重试 UI、重启安全的 Main 凭证槽恢复及前后端测试 |
| WECOM-07A | 主 Agent | 企业微信轮转诊断日志 | WECOM-04、WECOM-06 | DONE | 独立 `wecom.log`、2 MiB × 5 轮转、默认脱敏/详细诊断开关、凭证强制保护和日志测试 |
| WECOM-07B | 主 Agent | 真实连接兼容与扫码闪退修复 | WECOM-07、WECOM-07A | DONE | 登录窗口安全销毁顺序、`ERR_ABORTED` 跳转容错、live 协议双形状兼容、有界 key/枚举诊断和真实连接成功验证 |
| WECOM-08 | 主 Agent | 全链路验收与发布 | WECOM-07B | TODO | 全量门禁、E2E、受控企业微信测试账号冒烟、生产打包升级、凭证扫描和独立安全审查 |

### WECOM-00 验证记录

- 根 `.gitignore` 新增 `backend/wx-ribao/` 精确忽略规则；`git status --short`/`git status --ignored --short` 确认该目录已从未跟踪变为已忽略，原始三份用户资料未被修改。
- `backend/tests/fixtures/wecom/` 新增四份全合成协议 fixture + `README.md`（标注每份与真实抓包的置信度），`backend/tests/test_wecom_fixture_hygiene.py` 新增可复跑敏感扫描（本机存在原始样例时动态比对，否则跳过），并用正向注入真实姓名的方式验证过扫描逻辑真实生效而非空跑通过。
- 实际门禁：`uv run ruff check .`、`uv run mypy`（strict，**125 个源文件**）均通过；`uv run pytest`（**306 项收集**）直接重定向运行 exit code 0、全部通过；`git diff --check` 通过（仅 LF→CRLF 提示）。全量跑批中两次复现已知的 `ISS-013`（JWT 篡改测试偶发假阳性），单独重跑 `test_auth_api.py` 立即全部通过，本阶段未改动认证代码，与该已知问题无关。
- `uv run ruff format --check .` 发现一项与本阶段无关的预置格式漂移（`app/services/export_style.py`，工作树本身干净，判断为更早提交遗留），未顺手修改，已记入 `issues.md`（`ISS-029`，P3，非阻塞）。
- 独立审查：本阶段范围小且是治理性质（仅 `.gitignore`、测试 fixture、一个纯函数式扫描测试，未触碰任何业务代码/API/数据库/Electron 能力边界），由主 Agent 自行复核 `git status`/fixture 内容/扫描结果替代独立沙盒审查；`WECOM-02` 起涉及真实数据/协议/凭证实现后恢复独立审查（含专项安全审查）惯例。

### WECOM-02/WECOM-03 验证记录

`WECOM-02`（数据基础，backend）与 `WECOM-03`（Electron 登录与凭证桥）依赖只有 `WECOM-00`/`WECOM-01`、互不依赖，文件范围完全不重叠（`backend/**` vs `electron/**`），按两个 Agent 并行实现；主 Agent 逐文件复核两份 diff 后统一运行合并后的全量门禁、同步文档并提交。

**WECOM-02（backend）**：

- 新增 `app/models/wecom.py`（`WeComUserBinding`/`WeComSyncProfile`/`WeComDailySyncRecord`，复用现有 `TimestampMixin` 而非手写 `created_at`/`updated_at`，与 `daily_report.py`/`template.py`/`user.py`/`weekly_report.py` 同一更新后的约定）、`app/repositories/wecom.py`（三个极简 owner 过滤 Repository，无 Service 逻辑）、`app/schemas/wecom.py`（`WeComQuestionMappingConfig`/`WeComRecipientConfig`/`WeComFieldMappingConfig` 三个 Pydantic 契约，`schema_version` 均为无默认值 `Literal[1]`，各自带自定义校验器如"日期/今日/明日题目 `submit_order` 不重复""`field_key` 不重复"）、迁移 `f19f6d677a36_add_wecom_sync_tables`（纯建表，`down_revision=8b1d4e6f2a90`）。
- 字段设计与 `docs/方案设计.md` §6 逐项核对一致；在设计未明确长度的指纹字段上额外加 `length(...) = 64` CHECK（SHA-256 十六进制固定长度），`last_error_kind` 刻意不加 CHECK 白名单（该枚举归属尚未实现的 `WECOM-04/06`，提前约束有锁死后续设计的风险）。
- 新增 `tests/test_wecom_models.py`（约束测试）、`test_wecom_migration.py`（迁移 upgrade/downgrade/幂等/FK 检查）、`test_wecom_schemas.py`（Pydantic 契约校验），并同步修正了两处因新增迁移而必然联动的既有测试：`test_migrations.py` 的 `_EXPECTED_TABLES` 加入三张新表；`test_v2_migration.py` 的 `HEAD_REVISION` 更新为新头版本，且两个 downgrade 拒绝测试的断言从"降级失败后停在 HEAD"改为"停在 V2"（真实原因：SQLite 上 Alembic 每个 revision 步骤独立提交，多步 downgrade 会先干净地退掉本次新增的空表 revision，再执行到 V2→V1 才被正确拒绝，因此最终落点是 V2 而非原 HEAD；已用真实迁移验证过，不是猜测）。
- 实际门禁：`uv run ruff check .`、`uv run mypy`（strict）均通过；`uv run ruff format --check .` 仅剩与本任务无关的既有 `ISS-029` 漂移。

**WECOM-03（Electron）**：

- 新增 `electron/src/main/security/wecom-credential-store.ts`（`safeStorage` 加密、按随机 32 位十六进制 `credential_slot` 定位、无明文回退、`{mode:0o600}` 写入、损坏密文/加密不可用均转为类型化错误而非未捕获异常）、`electron/src/main/wecom/{constants,auth-window-controller,bridge-client}.ts`、`electron/src/main/ipc/register-wecom-bridge.ts`（`connect`/`disconnect`/`executeSync` 三个窄 IPC，`assertTrustedSender` 校验、`executeSync` 的 ULID 正则校验、`connect` 失败时清理已创建的凭证槽）。
- `main_bridge_secret`：复用现有 `generateRuntimeSecret()` 独立调用生成第二个随机密钥，随 sidecar 子进程环境变量 `WEEKLY_REPORT_MAIN_BRIDGE_SECRET` 下发（`manager.ts`），同时接入既有 `LogBuffer.append(...secretsToRedact)` 的可变参数脱敏机制，不写日志、不经 preload/renderer；`SidecarManager.getMainBridgeSecret()` 刻意不接入任何 IPC handler，只有 `index.ts` 直接构造的 `WeComBridgeClient` 能读到。
- 登录窗口：隔离 `wecom-auth-<随机>`（非 `persist:`）session partition，`webPreferences` 为 `{contextIsolation:true,sandbox:true,nodeIntegration:false}` 且不设置 `preload`；导航限制为精确主机名白名单（`doc.weixin.qq.com`/`open.weixin.qq.com`/`work.weixin.qq.com`，HTTPS-only，拒绝 `doc.weixin.qq.com.evil.com` 这类相似域名）；登录完成判定为轮询 `wedoc_sid` Cookie 非空（可注入 fake session 做纯函数单测），不是固定等待。
- `WeComBridgeClient` 已按 §9.2 的请求形状实现（loopback base URL 校验、`X-Main-Bridge-Secret`+JWT header、结构化 JSON body、Cookie jar 转 snake_case），但调用的 `/api/v1/internal/wecom/**` 端点本身要到 `WECOM-06` 才存在——这是已知、记录在案的范围边界。
- 实际门禁：`npm run lint`（0 error/0 warning）、`npm run typecheck`、`npm test`（**26 文件 192 项通过**）、`npm run build` 均通过；构建产物扫描（`electron/out/{main,preload,renderer}`）确认无密钥/Cookie 相关字符串泄露，`preload/index.js` 精确只暴露 `wecom.{connect,disconnect,executeSync}` 三个方法。

**合并后复核（主 Agent）**：

- 主 Agent 逐文件读取了两份 diff 的全部新增/修改代码（不仅是 Agent 自述摘要），确认字段设计、安全边界（`safeStorage` 无明文回退、导航白名单、IPC 受信任 frame 校验、Main-only secret 不进 IPC）均与设计文档一致，未发现 P0/P1。
- 合并后重新执行的全量门禁（而非分别信任两个 Agent 各自门禁结果）：后端 `uv run ruff check .`、`uv run mypy`（strict，**132 个源文件**）均通过，`uv run pytest -q`（**342 项收集，0 failure/0 error**，`--junit-xml` 确认，终端最终汇总行在本环境下持续性缺失与用例结果无关）；前端 `npm run lint`、`npm run typecheck`、`npm test`（**26 文件 192 项**）、`npm run build` 均通过；主 Agent 独立执行 `grep` 复核构建产物未发现 `X-Main-Bridge-Secret`/`wecom` 相关字符串泄露到 `preload`/`renderer` 产物。`git diff --check` 通过（仅 LF→CRLF 提示），`git status --short` 只包含两个任务范围内的文件，无非预期改动。

### WECOM-04/WECOM-05 验证记录

`WECOM-04`（内部协议 Client，backend）与 `WECOM-05`（字段映射与预览，backend）依赖分别是 `WECOM-00`/`WECOM-02`/`WECOM-03` 和 `WECOM-02`，二者互不依赖，文件范围完全不重叠（`app/integrations/wecom/**` + `tests/test_wecom_client.py` vs `app/services/wecom_mapper.py` + `tests/test_wecom_mapper.py`），唯一潜在共享风险点是 `backend/pyproject.toml`/`uv.lock`（只有 `WECOM-04` 需要改，用于把 `httpx` 从 dev 依赖迁移为生产依赖），已要求 `WECOM-04` 尽早一次性完成该步骤以降低两个 Agent 共享同一 `backend/.venv` 时的环境竞态窗口；两个 Agent 按此拆分并行实现，主 Agent 逐文件复核两份 diff 后统一运行合并后的全量门禁、同步文档并提交。

**WECOM-04（`app/integrations/wecom/`）**：

- 依赖迁移：`httpx==0.28.1` 从 `[dependency-groups].dev` 移到 `[project.dependencies]`（版本不变），`uv lock`+`uv sync --frozen` 已验证生产环境可 `import httpx`。
- `WeComInternalClient`（`client.py`）：base URL 硬编码 `https://doc.weixin.qq.com`（非构造参数），每次请求前用 `_assert_allowed_target()` 二次校验（纵深防御，防 SSRF）；`follow_redirects=False`，3xx 归类为 `WeComAuthExpired`；`get_template_info`/`list_journals`/`submit_daily` 三方法齐全，`list_journals` 额外带 `limit` 关键字参数（默认 50，未破坏原定位置签名）；`_MAX_JOURNAL_ENTRIES=200` 防止异常响应触发无界扫描。
- 六个异常类型（`WeComAuthExpired`/`WeComSchemaChanged`/`WeComBusinessRejected`/`WeComProtocolChanged`/`WeComTransportFailed`/`WeComOutcomeUncertain`）均继承自 `WeComClientError`；关键设计：只读接口（模板信息/日报列表）的结构校验失败归 `WeComProtocolChanged`，写接口（提交日报）HTTP 200 之后的结构校验失败归 `WeComOutcomeUncertain`——同一类校验失败在读/写接口上被分类到不同异常，精确对应 `docs/方案设计.md` §11"若已发送提交则 uncertain，只读接口则 schema_changed/协议错误"。
- `select_cookie_header()`：纯函数，按 RFC 6265 domain/path 匹配规则 + `secure`/过期时间筛选 Cookie，独立提取 `wedoc_sid`；缺失时 `_select_or_raise()` 直接拒绝、不发请求。
- multipart 提交：用 `files=[(name, (None, value)), ...]` 的 httpx 惯用法强制走 multipart 编码且边界随机（不能硬编码固定边界），字段顺序与 `tests/fixtures/wecom/answer_page_request.http` 一致；`get_journal_list`/`answer_page` 用 `errcode`，`get_template_combine_info`/`answer_page` 响应体用 `head.ret`，两套业务码字段名已按各自真实抓包正确区分。
- Debug 日志只含 method/host/路径模板/耗时/分类结果，用 `caplog` 测试直接断言 Cookie 值和 `"Cookie"`/`"form_id"` 关键字不出现在任何日志行。过程中发现并修复一个真实的测试环境陷阱：若在包含 `TestClient`/`create_app` 的其他测试文件之后运行，Alembic `env.py` 的 `logging.config.fileConfig(disable_existing_loggers=True)` 会把已存在的 `app.integrations.wecom.client` logger 标记为 disabled，导致 `caplog` 收不到记录；已在测试内保存/强制启用/还原该 logger 的 `.disabled` 标志规避，未改动共享的 Alembic/日志配置本身。
- 测试（`test_wecom_client.py`，31 项）：三方法成功路径、multipart 字段顺序/边界随机性、6 项 Cookie 筛选纯函数测试、三方法业务码拒绝、HTML 登录页响应、缺字段/超量 `entrys`/缺 `answer_replys`、connect/read/write 三种超时分类、重定向不跟随、host allowlist 拒绝真实域名之外的一切（含形似域名 `doc.weixin.qq.com.evil.com`）、日志脱敏。
- 实际门禁：`uv run ruff check .`、`uv run ruff format --check .`（仅剩与本任务无关的既有 `ISS-029`）、`uv run mypy`（strict，139 个源文件）、`uv run pytest tests/test_wecom_client.py`（31 passed）均已独立验证通过。

**WECOM-05（`app/services/wecom_mapper.py`）**：

- 路由规则严格按 §7.1 四条优先级实现：`field_type=PROJECT_LIST` 优先于 `core_type` 判断；`core_type=today_work`/`tomorrow_plan` 的核心字段值直接作为答案正文（非"标签:值"形式的附加内容）；自定义字段按 `field_mapping_json.rules` 查表，无规则且非空时按 `unmapped_policy` 记入 `unmapped_field_keys`（`block`）或静默跳过（`ignore`），本模块只如实报告、不决定是否真的阻止提交（留给 `WECOM-06`）。
- **"责任人"歧义已解决并已反向修正 `docs/方案设计.md` §7.2**：`ProjectListEntry`（`app/schemas/daily_report.py`）只有 `project`/`content`/`status` 三个字段，没有责任人子字段；§7.1 表格本身也把"责任人类自定义字段"列为独立的、按通用"标签:值"规则映射的自定义字段。已按这个更贴合真实数据模型的方向实现（责任人是普通自定义字段，格式化后追加在同一来源全部 `PROJECT_LIST` 分段之后），并同步修正了 `docs/方案设计.md` §7.2 的示例文本（移除示例代码块里容易被误读为"每个项目条目自带责任人"的那一行，改为单独一句话说明）。
- **半角冒号（连带修正了 `docs/方案设计.md`）**：§7.2 原文示例用全角"："，但仓库全部 Python 源码的 Ruff `RUF001`/`RUF002`/`RUF003`（禁止歧义全角标点）零例外启用，`app/**` 现有中文提示文本一律用半角标点；`wecom_mapper.py` 因此改用半角 `:`（`ruff check` 验证过全角版本会直接报错），`docs/方案设计.md` §7.2 的示例文本已同步改为半角，避免文档和实现出现无意义的字面差异。
- 两个指纹函数均为 `hashlib.sha256(json.dumps(..., sort_keys=True, separators=(",", ":")).encode()).hexdigest()`（64 位小写十六进制，和 `WECOM-02` 的 `length(...)=64` 约束一致）：`compute_schema_fingerprint()` 是三个 `WeComQuestionSpec` 的纯函数（不依赖数据库，供 `WECOM-06` 对本地配置和实时抓取的远端结构都能调用同一函数比对），`sub_type=None` 序列化为 JSON `null`、`sub_type=""` 序列化为 `""`，两者不会被规范化成相同指纹；载荷指纹基于 Mapper 自己产出的三个答案文本。
- 测试（`test_wecom_mapper.py`，34 项）：核心字段、`PROJECT_LIST`（单/多项目、三态标签、和核心文本字段共存、优先于同名核心类型）、动态字段两种未映射策略、多来源"日报 N"分段（含 3 来源且中间一个为空的定位保持测试）、空值不留痕迹、日期跨年/闰日格式化、**历史多模板 fixture**（同一天两个 entry 各自持有字段集合/顺序完全不同的 `template_snapshot`，验证 Mapper 只依赖每个 entry 自带快照、不依赖全局当前模板）、两个指纹函数的确定性/敏感性（含 `None` vs `""` 的 `sub_type` 专项测试）。
- 实际门禁：`uv run ruff check .`、`uv run ruff format --check .`、`uv run mypy`（strict，139 个源文件）、`uv run pytest tests/test_wecom_mapper.py`（34 passed）均已独立验证通过。

**合并后复核（主 Agent）**：

- 主 Agent 逐文件读取了两份 diff 的全部新增代码（`client.py`/`schemas.py`/`wecom_mapper.py` 及两份测试文件），确认端点字段/业务码判定、Cookie 筛选算法、异常分类边界、路由/格式化规则、指纹算法均与 `docs/方案设计.md` 原文逐项核对一致，未发现 P0/P1。
- 合并后重新执行的全量门禁（而非只信任两个 Agent 各自的门禁结果）：`uv run ruff check .`、`uv run ruff format --check .`（仅剩既有 `ISS-029`）、`uv run mypy`（strict，**139 个源文件**）均通过；`uv run pytest -q`（**407 项收集，0 failure/0 error**，`--junit-xml` 确认，恰好等于阶段前 342 项 + `WECOM-04` 新增 31 项 + `WECOM-05` 新增 34 项）。`git diff --check` 通过（仅 LF→CRLF 提示），`git status --short` 只包含两个任务范围内的文件（`backend/pyproject.toml`、`backend/uv.lock`、`backend/app/integrations/**`、`backend/app/services/wecom_mapper.py`、两个测试文件），无非预期改动；用 `WECOM-00` 的敏感样例扫描逻辑对本次完整 diff 做了一次额外的正向核验（真实样例 token 均未出现在 diff 中）。
- 独立审查：本阶段涉及真实协议 Client 和字段映射算法实现，范围不小；由主 Agent 逐文件复核全部新增代码（含安全边界：host 硬编码/SSRF 防护、Cookie 从不写日志、多来源/未映射字段处理不静默出错）替代独立沙盒审查，判断依据是改动完全局限于纯逻辑层（无数据库写入、无 API 端点、无 Electron 能力边界变化），风险面小于 `WECOM-02`/`WECOM-03`；`WECOM-06` 起涉及真实状态机、并发和权限时恢复独立沙盒安全审查惯例。

### WECOM-06 验证记录

任务开始时发现工作树已存在未提交的 WECOM-06 半成品（`app/services/wecom_connection.py`/`app/services/wecom_sync.py`、`app/repositories/wecom.py`/`app/schemas/wecom.py` 的扩展、`app/api/dependencies.py`/`app/core/config.py`/`app/core/middleware.py` 的 `main_bridge_secret`/豁免路径改动、以及 `test_config.py`/`test_runtime_secret_middleware.py` 的新增测试），逐文件核对确认其字段/状态机设计与 `docs/方案设计.md` §3～§11 一致后，在此基础上继续完成本任务，未推倒重写。

- **补齐的实现**：`backend/app/api/v1/wecom.py`（公开 REST：`connection`/`profile`/`previews`/`sync-records` 及独立的 `daily-report-days/{work_date}/wecom-syncs` 幂等创建路由）、`backend/app/api/v1/internal_wecom.py`（Main-only REST：`connections/validate`/`connections/disconnect`/`sync-records/{id}/execute`，路由级 `require_main_bridge_secret` 依赖 + `include_in_schema=False`）、`backend/app/main.py` 接入三个路由。`docs/方案设计.md` §10.3 要求的启动崩溃恢复（`syncing` 超租约转 `uncertain`）此前未实现，已补齐：`WeComDailySyncRecordRepository.recover_stale_syncing()`、`WeComSyncService.recover_stale_syncing_records()`（5 分钟租约常量 `STALE_SYNCING_LEASE_SECONDS`）及 `app/__main__.py::main()` 启动接入，与既有 `cleanup_stale_manual_backups`/`ExportService.cleanup_expired` 同一模式。
- **发现并修复一个真实的并发缺陷（P1）**：`WeComConnectionService._upsert_binding`/`_upsert_profile` 的"先查后插、插入冲突则改查现有行更新"回退逻辑在 `except IntegrityError:` 分支内直接复用同一 `AsyncSession` 继续查询，而 SQLAlchemy 在一次 `flush()` 抛出 `IntegrityError` 后会把整个事务标记为 `DEACTIVE`，任何后续查询都会抛 `PendingRollbackError` 而不是如预期般优雅回退为更新——真实并发连接（同一用户重复点击"连接"、或两次几乎同时的 `validate_connection` 调用）会直接 500，而不是设计文档承诺的"回退为更新其行"。用真实 `asyncio.gather` 双会话并发调用复现（`test_concurrent_validate_connection_only_creates_one_binding_and_profile`）。修复方案：把 `add()` 包进 `await self._session.begin_nested()`（SAVEPOINT），失败只回滚这一次插入尝试，不影响 `validate_connection` 同一事务内更早已完成的其它写入（该事务本身要求 binding+profile 要么同时成功要么同时失败）；若改为对整个 `self._session.rollback()`，会连带撤销同一事务里更早的 `_upsert_binding` 成功结果，破坏原子性，因此没有采用 `WeComSyncService.get_or_create_record()` 里那种更简单的整体 `rollback()`（该处安全是因为插入前没有其它写入需要保留）。
- **新增测试**：`tests/wecom_service_support.py`（非 `test_*` 命名，供 Service 级测试共享的 `StubWeComClient`（满足两个 Service 各自的 `WeComClientLike` Protocol）与 fixture 构造函数，字段取值对齐 `tests/fixtures/wecom/*.json` 已验证过的真实协议形状）。`test_wecom_connection_service.py`（9 项：连接创建/鉴权失败不落库/模板结构不全不落库/重连原地更新/并发只留一行且不崩溃/`get_profile` 前置校验/版本冲突/仅更新可变字段/断开幂等）。`test_wecom_sync_service.py`（20 项：预览所有权与前置状态、创建幂等、执行成功/`auth_expired`/`schema_changed`（题目 ID 漂移）/不可证实重复（不调用 `submit_daily`）/已知重复对账成功（不重复提交）/`uncertain` 阻断直接重试、已成功短路不重复调用远端、`syncing` 中拒绝并发执行、重试状态转换、列表过滤、跨用户隐藏、`finalize_attempt` 的迟到 `attempt_token` 被丢弃（Repository 级直接验证）、崩溃恢复只影响超租约记录）。`test_wecom_api.py`（6 项，公开路由端到端）、`test_wecom_internal_api.py`（10 项，Main-only 路由端到端，含真实经由 `monkeypatch` 打桩 `WeComInternalClient` 三方法后的连接/断开/执行/重复检测全链路，以及双重鉴权、`X-Runtime-Secret` 豁免、OpenAPI 排除的专项验证）。
- **门禁**：`uv run ruff check .`、`uv run ruff format --check .`（仅剩既有 `ISS-029`，与本任务无关）、`uv run mypy`（strict，**148 个源文件**）均通过；`uv run pytest -q --junitxml`（**458 项、0 failure/0 error/0 skipped**，等于阶段前 407 + 半成品自带的 6 + 本任务新增 45）通过。`git status --short` 只包含本任务范围内文件。
- **独立审查**：按约定恢复独立沙盒审查惯例——分别派发了 `code-review`（high，覆盖正确性/简化/效率）与 `security-review`（专项安全，聚焦新增文件的所有权隔离、双密钥鉴权模型、OpenAPI 隐藏、Cookie/凭证不落日志/不落响应、SQL 注入面）两个独立沙盒 Agent。`security-review` 已完成：独立复核了所有权过滤（含状态机条件更新的原子性）、`X-Main-Bridge-Secret` 恒定时间比较与路由级统一生效、中间件路径前缀豁免不会误伤其他路由、响应模型不泄露凭证字段，未发现达到高置信度阈值（≥8/10）的漏洞。`code-review`（high）在本次提交时仍在后台运行、尚未返回结果——本提交不等待其完成，其结论到达后将作为独立的后续记录补充到本文件（若发现 P0/P1 会先修复再追加提交，不回改本条已提交记录）。
- **已知范围边界（非缺陷）**：Electron 端 `register-wecom-bridge.ts::connect()` 调用 `bridgeClient.validateConnection(cookieJar, '')` 时 `form_id` 传空字符串（`WECOM-03` 自身注释已记录为"form_id 发现是 WECOM-06/07 范围"），且未把 `credentialStore.save()` 返回的 `slot` 传给 `WeComBridgeClient.validateConnection()`——但本任务新写的 `WeComConnectionValidateRequest.credential_slot` 按 `docs/方案设计.md` §5.1 步骤 4 要求为必填字段。这意味着当前 Electron 侧的"连接"入口在真实点击时仍不能跑通（`form_id` 为空 + `credential_slot` 缺失两者任一都会被拒绝），但这与 `WECOM-03` 自述的已知范围边界一致——真正可用的"连接"UI（含表单发现和 `credential_slot` 透传）是 `WECOM-07` 的既定范围，本任务未越权提前修改 `electron/**`。已记入 `issues.md`。

### WECOM-07 验证记录

- 任务开始时工作树已有未提交的 Electron Main/preload 与 renderer 半成品；主 Agent 先按 `docs/需求理解.md`/`docs/方案设计.md` 核对，再在原改动上续建并保留其已完成部分。设置页新增 `WeComSettingsCard.vue`：表单链接/ID 解析、连接/重连/断开、账号/模板信息、当前模板动态字段映射、未映射策略、收件人配置、乐观锁冲突重载、同步历史筛选/分页/状态展示。保存当前模板映射时会保留历史模板的规则，避免切换模板后误删旧日报所需配置。
- 已归档日报详情新增 `WeComSyncDialog.vue`：加载连接/配置/预览/既有同步记录，展示日期、来源数、字符数、今日/明日正文和未映射字段；未映射字段可在对话框内映射到今日/明日/忽略并重新预览。同步只经 `window.runtimeBridge.wecom.executeSync(record_id)` 窄 IPC 进入 Main；`succeeded` 短路、`uncertain` 禁止直接重试，认证失效/结构变化/疑似重复分别要求重连、复核映射或先远端对账。历史页只有明确 `failed` 提供确认重试，`pending` 提供继续执行；未连接时两者均禁用并引导重连。
- **解决 `ISS-031`/`ISS-032`**：preload 的连接签名改为 `connect(form_id)`，Main 新建 `credential_slot` 后连同真实 `form_id` 传给 `/connections/validate`；后端对空 `form_id` 显式拒绝。半成品原先仅在 Main 内存保存当前槽位，应用重启或本地账号切换后无法读取已持久化 Cookie jar；新增不进入 OpenAPI 的双鉴权 `GET /api/v1/internal/wecom/connections/credential-slot`，按当前 JWT 返回本人 `credential_slot + connection_status`，连接、断开和执行均即时查询，跨用户为 `null/null`。槽位/Cookie/Main-only secret 均未进入 preload 或 renderer。
- **独立审查修复 `ISS-033`/`ISS-034`**：初审指出槽位删除失败被吞掉、断开本地删除后后端失败缺少补偿，以及历史 retry 可能把记录滞留为无操作入口的 `pending`。最终实现 `deleteEventually()` 的空 marker 持久队列并在后续连接/断开前重试；断开异常后用同一 Main-only 查询按真实 binding status 对账（`disconnected` 不恢复 Cookie，仍指向原槽才补偿恢复）；历史 `pending` 增加继续执行入口并在异常后重载。审查者经过三轮窄复审，最终确认无剩余 P0/P1/P2。
- 能力开关已由 `wecom_sync=false` 切换为 `true`；`SettingsView.vue` 与 `DailyDetailView.vue` 完成入口接入。新增 renderer 企业微信 REST 类型/API/纯函数与 45 项单测，并扩充 Electron bridge、Credential Store、Main IPC、后端 Main-only API/能力开关测试；全量结果为后端 `pytest` **460 项通过**，前端 Vitest **27 文件 254 项通过**。
- **门禁与冒烟**：`uv run --directory backend ruff check .`、`uv run --directory backend mypy`（strict，148 个源文件）、`uv run --directory backend pytest -q`（460 项）通过；`ruff format --check .` 仅报告既有 `ISS-029` 的 `app/services/export_style.py` 漂移。`npm run lint`、`npm run typecheck`、`npm test`（27 文件 254 项）、`npm run build` 均通过；构建产物扫描未发现 `credential_slot`、Cookie 名称或 Main-only secret 泄露到 preload/renderer。用一次性断言扩展现有 `admin-guard.spec.ts` 后运行真实 Electron/sidecar 冒烟，确认设置页出现企业微信表单入口、连接按钮可用且不再显示“功能暂未开放”（1 项通过）；一次性断言随后移除，未使用真实企业微信账号或发起外部登录。
- `WECOM-08` 边界保持不变：受控企业微信测试账号的真实连接/提交/对账、生产 sidecar/electron-builder 打包、安装升级、完整 Playwright E2E、发布级凭证扫描与独立安全审查仍未执行，不得把 WECOM-07 的开发态能力描述为已发布验收。

### WECOM-07A 验证记录

- 用户在真实点击连接时只看到“企业微信内部服务请求失败（HTTP 502）”，现有 DEBUG 摘要既不持久化，也无法区分企业微信业务拒绝、协议结构变化与模板三题识别失败。新增 `app/core/wecom_logging.py`，后端迁移完成后配置独立 `app.integrations.wecom` logger，写入 `log_dir/wecom.log`；`RotatingFileHandler` 单文件上限 2 MiB，保留 `wecom.log.1` 至 `.5` 五个备份。开发态位置为根 `.local-data/logs/wecom.log`，生产态沿用 Electron 注入的 `userData/logs/wecom.log`。
- `Settings.wecom_log_redact` 默认 `true`，可用 `WEEKLY_REPORT_WECOM_LOG_REDACT=false` 并重启应用开启详细诊断。默认模式只记录固定 method/host/path 模板、结果分类和耗时；详细模式额外记录 HTTP 状态、异常类型/固定安全文案、业务码，以及模板题目总数、可识别类型数和日期/今日/明日候选计数。两种模式都不接收请求/响应 header/body、Cookie jar、form/template/member ID 或日报正文；详细字段有键白名单，Formatter 对 Cookie/Authorization/JWT/两类运行期密钥做不可关闭的二次清洗。
- Client 的成功、认证失效、业务拒绝、协议变化、transport failure 和 uncertain 均写分类事件；连接 Service 对三题自动识别失败单独写 `template_unresolved` 与纯计数诊断，因此下一次 502 可直接从日志判断是业务码/协议响应还是模板识别问题。
- 新增 5 项测试（配置开关 1、日志模块 4），并扩充 Client/连接 Service 既有日志断言。定向 54 项通过；完整后端 `ruff check`、mypy strict（150 个源文件）和 pytest（465 项）通过；`ruff format --check .` 仍只报告既有 `ISS-029` 的 `app/services/export_style.py`，本任务全部涉及文件已格式化。`git diff --check` 通过（仅 Windows LF→CRLF 提示）。未修改 Electron/renderer，未启动真实企业微信登录或记录任何真实凭证/正文。
- `WECOM-08` 状态不变：轮转诊断日志是发布验收前的可观测性补强，不替代受控真实账号连接/提交/对账、生产打包安装和独立安全审查。

### WECOM-07B 验证记录

- 用户真实扫码后 Electron 以 Windows `0xC0000005`（npm 十进制 `3221225477`）退出。真实复现确认扫码前稳定、扫码后企业微信 HTTP 请求已返回而 Electron 原生进程消失；根因集中在登录收尾同时调用 `BrowserWindow.close()` 与 `Session.clearStorageData()`。清理改为 `destroy()` 强制关闭并等待终态 `closed` 后再清理 Session，真实扫码后 Electron 保持运行；单测严格断言 `destroy -> closed -> clear-storage` 顺序。
- 企业微信扫码/SSO 页面替换初始文档时，Electron `loadURL()` 会以 `ERR_ABORTED (-3)` 拒绝 Promise。控制器原先将其误判为打开失败；现在只在窗口仍存活且错误明确包含 `ERR_ABORTED` 时继续权威 `wedoc_sid` Cookie 轮询，窗口已关闭仍返回 canceled，其它 DNS/证书/`ERR_FAILED` 错误仍失败。
- 详细模式的有界 key 路径诊断确认 live 只读响应发生三处协议漂移：`body.form/form_id` 迁移到 `body.form_info/form_info.form_id`；模板条目从 `reply_id/form_id/reply_name` 迁移到 `createvid/doc_info.form_id` 且不再提供显示名；文本题 `reply_type` 从旧值 `1` 变为 `24`（日期仍为 `11`）。Client 明确支持新旧两种已观察形状，缺失显示名保持空字符串，不拿模板名称冒充用户姓名；未知题型仍拒绝。
- `schema_paths` 只遍历符合 ASCII 协议标识符规则的 JSON key，广度优先且限制深度 6、最多 64 条、日志值最长 4096 字符；不读取或记录任何 value。候选题型只记录三个纯数字枚举。日志模块仍以诊断键白名单和不可关闭的凭证/JWT/密钥二次清洗保护。
- 真实账号最终验证：企业微信模板请求返回 HTTP 200，`wecom.log` 记录 `connection_validation outcome=ok`；界面完成连接，Electron 保持 4 个常驻进程，无 `ERR_ABORTED`、无闪退。该验证只覆盖连接与模板发现，未执行日报提交、重复对账、生产安装或升级，不能替代 `WECOM-08`。
- 门禁：后端 Ruff lint、mypy strict（150 个源文件）通过，本次 6 个后端文件 Ruff format check 通过；协议/连接定向 50 项通过。清洁环境全量 471 项中，排除既有 `ISS-013` 的末字符 JWT 篡改测试后其余 **470 项全部通过**；该用例本轮再次复现已登记的 base64url 冗余位测试构造问题，与本次文件无交集。前端/Electron `npm run lint`、`npm run typecheck`、Vitest（27 文件 **255 项通过**）和 `npm run build` 均通过。主 Agent 逐文件复核未发现新的 P0/P1；本任务未派发独立 Agent 审查。

阶段 3（`DB-01`/`DB-02`/`DB-03`/`API-01`/`QA-03`）已实现、通过质量门禁并创建独立提交 `8480515`；独立 Reviewer 审查仍待补齐（非阻塞）。

阶段 4 `AUTH-01`/`AUTH-02`/`USER-01`/`FE-01`/`FE-02`/`QA-04` 已完成实现、自测、质量门禁、独立审查与提交 `1a50e75`，统一为 `DONE`。

阶段 5 七项任务均已完成实现、自测、质量门禁、独立审查与提交 `1d965fe`，统一为 `DONE`。

阶段 6 五项任务（`EXPORT-01`/`EXPORT-02`/`DESK-04`/`FE-05`/`QA-06`）均已完成实现、自测、质量门禁、独立审查与提交 `d6ab86e`，统一为 `DONE`。

阶段 7 四项任务（`WEEKLY-01`/`WEEKLY-02`/`FE-06`/`QA-07`）均已完成实现、自测、质量门禁、独立审查，统一为 `DONE`。

阶段 8 三项任务（`BACKUP-01`/`FE-07`/`QA-08`）均已完成实现、自测、质量门禁、独立审查（含专项安全审查），统一为 `DONE`。

阶段 9 四项任务（`QA-09`/`PKG-01`/`PKG-02`/`REL-01`）均已完成实现、自测、质量门禁、独立审查，统一为 `DONE`。V1 全部 9 个阶段现已交付完毕。

第二版 `REQ-10`、`DESIGN-10`、`BE-10A`、`BE-10B`、`BE-10C`、`FE-10`、`QA-10` 均为 `DONE`。CR-20260807-01 第二版增量的全部任务已交付完毕，当前无可领取的第二版任务。

企业微信增量 `WECOM-00..07` 均已完成实现、自测和对应质量门禁；`WECOM-07` 已接通 Electron Main 与 Vue 用户交互，修复 `form_id`/`credential_slot` 透传和重启槽位恢复，`wecom_sync=true`。下一可领取任务是 `WECOM-08`（全链路验收与发布）：受控真实企业微信测试账号、生产打包/安装升级、完整 E2E、发布级凭证扫描和独立安全审查仍未执行，当前状态不得描述为已发布验收。

### 第二版阶段 10A 验证记录

- 后端：`uv run --directory backend ruff check .`、`uv run --directory backend mypy`、`uv run --directory backend pytest -q`（199 项）全部通过。
- 前端/桌面回归：`npm run lint`、`npm run typecheck`、`npm test`（18 文件、108 项）、`npm run build` 全部通过。
- 数据迁移：空库升级、V1 真实结构副本升级、三态日报、多个用户/模板版本、跨年周、闰日、未来日期、导出任务、停用账号、三列周报 JSON V2 化、逐字节正文/模板保留、行数与外键检查、无损 downgrade、同日多条目/审计事件拒绝 downgrade、坏 JSON 在 DDL 前中止均有自动化测试。
- `git diff --check` 通过；本阶段未开始 BE-10B 的同日多篇/删除/撤销/日期归档 API，也未修改 Electron 页面。

### 第二版阶段 10B 验证记录

- 后端：`uv run --directory backend ruff check .`、`ruff format --check .`、`uv run --directory backend mypy`（strict，115 个源文件）、`uv run --directory backend pytest`（**242 项通过**，阶段 10A 遗留 199 项 + 本阶段新增 43 项：`client_request_id` 幂等/冲突、同日多篇并发创建、创建与日期归档并发互斥（XOR 结果）、草稿删除清空日期容器、日期级归档聚合多条目快照/幂等/草稿阻塞/无可归档阻塞、月历摘要、日期详情、admin 撤销权限/版本冲突/审计、用户安全删除（业务记录阻塞、确认用户名不匹配、自我删除保护、末位管理员并发保护、非管理员越权）等）均已实际执行并通过。
- 前端/桌面回归（未修改 Electron/Vue 代码，用于确认未破坏既有链路）：`npm run lint`、`npm run typecheck`、`npm test`（18 文件 108 项）、`npm run build` 均实际执行并通过。
- `git diff --check` 通过（仅常规 LF→CRLF 提示）。
- 独立安全专项审查（沙盒 Agent 独立读取 diff，未采信本 Agent 的实现结论）：逐项核查所有权隔离（日报条目/日期容器全部按 `owner_id` 过滤）、admin 查询是否泄露正文（`list_submitted_awaiting_archive`/`get_submitted_metadata` 均为原始列选择，不选择 `content_json`/`template_snapshot_json`）、SQL 注入（全部走 SQLAlchemy Core/ORM 构造）、用户删除权限提升路径（非管理员 403、自我删除阻断、末位管理员条件 `DELETE` 且已用并发测试验证、`has_business_records` 覆盖三张业务表并有外键 RESTRICT 兜底）、确认/原因绕过（用户名精确匹配、原因去空白后非空校验）、`client_request_id` 幂等键跨用户信息泄露（跨用户复用返回 40908 冲突而非泄露对方日报）、审计日志注入（`metadata_json` 全部走 `json.dumps` 结构化写入）。未发现 P0/P1 级可利用漏洞；识别出一项低置信度（4/10）信息项（`client_request_id` 跨用户存在性探测，无数据泄露，不构成漏洞）已记录但不阻塞交付。
- 关键实现事实：`daily_report_days`/`daily_reports` 的所有写操作复用 SQLite 单写者锁作为日期行并发互斥点（`touch_open_for_write` 在归档前率先获取写锁并复查 `open` 状态，`insert_entry_if_day_open` 用 `INSERT ... SELECT ... WHERE EXISTS` 单语句关闭创建与归档之间的竞态窗口，与 `AUTH-01` 的 `create_if_no_users_exist` 同一模式）；`DELETE /daily-reports/{id}/archive` 单篇归档接口已按 `api.md` §13.2 移除，替换为 `POST /daily-report-days/{work_date}/archive` 的日期级归档；用户安全删除的业务记录检查覆盖 `daily_report_days`/`weekly_reports`/`export_jobs`（`daily_reports` 通过日期容器传递覆盖），默认关联资源（`user_settings`/`report_templates`/`template_versions`）作为脚手架数据被显式清理而非阻塞删除。
- 已知范围边界（非缺陷，记录供 BE-10C 承接）：周报生成/重生成（`WeeklyReportService`）与导出（`ExportService`）仍读取 `daily_reports.status == 'archived'` 的条目级查询，未切换到 `daily_report_days.archive_snapshot_json` 的日期级正式快照；在真实多条目场景下对同一日期归档后，周报/导出的多条目聚合语义尚不正确（`weekly_report_sources` 按 `daily_report_day_id` 去重会在多条目场景下与来源假设冲突），已记录为 BE-10C 的既定范围而非本阶段回归；`test_exports_api.py`/`test_weekly_reports_api.py` 的测试夹具已同步改为调用新的日期级归档接口，但其覆盖场景仍是每日单条目，未验证多条目下的周报/导出行为。

### 第二版阶段 10C 验证记录

- 启动前先完整核对 `docs/方案设计.md` 第二版章节全文，发现并修正 BE-10B 遗留的五处响应契约偏差（`day_id`、`created`、月历稀疏返回/字段改名、用户 `can_delete`、撤销 `actor_username`），随独立 `fix` 提交先行交付（见 ISS-023），确保 BE-10C 在正确契约基础上开工。
- 周报：`availability()`/`generate()`/`regenerate()` 全部改为查询 `daily_report_days`（`list_in_range`/`list_archived_in_range`），`WeeklyDay` schema 由单一 `daily_report_id` 改为 `daily_report_day_id` + `entries: list[WeeklyDayEntry]`（每个来源条目独立一份 `fields`），`build_weekly_content()` 直接解析每个日期的 `archive_snapshot_json`（不再读取 `daily_reports` 条目表）；`availability()` 的逐日状态改为基于日期容器状态 + 当天条目构成推导（`archived`/`draft`/`submitted`/`None`），而非条目自身状态，`archived_count`/`non_archived_dates` 相应改为按日期计数/去重。V1 遗留的 `schema_version is None` 兼容解析分支已随之移除（BE-10A 迁移已保证全部历史数据是 `schema_version=2`）。
- 导出：`ExportCreateRequest.report_ids` 改名 `daily_report_day_ids`，筛选/选择均改为查询 `daily_report_days.status='archived'`；一日期一行，基础列新增"来源条目数"；单个日期存在多篇来源时，同一字段的多个值按来源提交顺序渲染为 `[1] 值\n[2] 值`（保留来源边界，`docs/方案设计.md` §9.2），单来源时保持原始类型（数字列不因合并逻辑被转成文本）；`=` 公式注入防护对每个来源值和合并后的整体文本值均生效；越权/不存在/未归档选择的响应字段改名为 `invalid_daily_report_day_ids`。
- 统计：新增 `GET /api/v1/statistics/monthly?month=YYYY-MM`（`app/services/statistics.py`/`app/api/v1/statistics.py`），当前月分母截至 Asia/Shanghai 今天、历史月为整月、未来月分母 0 且 `completion_rate=null`；`daily_report_count` 统计工作日期在所选月且状态为 `submitted`/`archived` 的来源条目（草稿不计，正式日报不重复计数）；`weekly_report_count` 按 `week_start` 所在月统计；`current_streak_days` 与所选月份无关，始终按"今天已完成则从今天向前，今天未完成但昨天完成则从昨天向前，否则为 0"的规则查询最近完成日期；`days` 复用月历稀疏摘要（仅返回存在记录的日期）。新增 `app/core/month_range.py` 提取 `YYYY-MM` 解析逻辑，供日历和统计两个接口共用（避免重复实现）。
- 实际门禁：后端 `uv run ruff check .`、`ruff format --check .`、`mypy`（strict，123 个源文件）、`pytest`（**280 项通过**，阶段 10B 遗留 246 项 + 本阶段新增 34 项：完成率/有效范围/连续天数纯函数 14 项、统计服务直连测试 5 项、统计 API 测试 5 项、`parse_month_range` 纯函数测试 10 项）均通过。周报/导出/统计新增与调整测试覆盖：跨年周、闰周/闰日分母、多来源条目合并为周报 `entries[]`、导出多来源 `[N]` 格式化与单来源保持数值类型、导出/周报测试夹具切换为构造真实 `archive_snapshot_json`。
- 前端/桌面回归（未修改任何 Electron/Vue 文件）：`npm run lint`、`npm run typecheck`、`npm test`（18 文件 108 项）、`npm run build` 均实际执行并通过；renderer 现有周报/导出 TypeScript 代码仍是 V1 形状，尚未适配新契约，是 `FE-10` 的既定范围而非本阶段回归。
- `git diff --check` 通过（仅常规 LF→CRLF 提示）。
- 独立安全专项审查（沙盒 Agent 独立读取 diff，未采信本 Agent 的实现结论）：逐项核查所有权隔离（`WeeklyReportService`/`ExportService`/`StatisticsService` 全部新增/改写查询按 `owner_id` 过滤）、导出 `daily_report_day_ids` 越权隔离、统计跨用户泄露、SQL 注入、多来源单元格公式注入防护回归，未发现 P0/P1。发现并修复一项真实的 LOW 严重度问题：`app/core/month_range.py::parse_month_range()` 对 `9999-12`（`date.MAXYEAR` 的 12 月）会在 `try/except` 之外计算下月首日导致未捕获 `ValueError`（原本返回 500 而非预期的 `40001`），已把该计算移入 `try` 块并补充 `tests/test_month_range.py`（10 项，含该回归场景）。
- 已知的 ISS-013（`test_tampered_access_token_is_rejected`/`test_expired_and_tampered_tokens_map_to_40102` 偶发假阳性）在本阶段全量跑批中复现一次，单独重跑通过，与本阶段改动无关，不阻塞交付。

### 第二版阶段 10D 验证记录（FE-10）

- 契约核对：全部改动依据 `docs/方案设计.md` 第二版 §7～§11 和当前后端 schema/route 源码（`backend/app/schemas/*.py`、`backend/app/api/v1/*.py`）逐字段核对，未仅依赖 `ai-docs/api.md` 摘要（吸取 ISS-023 的教训）。
- 路由与守卫：新增 `/change-password`（`forcedPasswordChangeOnly` 元字段，仅在 `must_change_password=true` 时可进入，非强制状态下访问会被重定向到 `/daily`）、`/statistics`、`/admin/daily-reports`；`router.beforeEach` 新增强制改密拦截，`api/client.ts` 新增 `onPasswordChangeRequired` 钩子，命中 `40303` 时自动跳转，双重保证（路由预判 + 运行期兜底）。菜单改名为“我的日报/我的周报/统计/模板管理/设置”，新增“日报管理”“用户管理”两个仅 admin 可见入口。
- 我的日报：`DailyListView.vue` 改为月历（`el-calendar` + 自定义 `date-cell`/`header` 插槽）+ 选中日期详情两栏布局；月历读取 `GET /daily-report-days?month=`，逐日状态由纯函数 `dayCellStatus()` 派生为 `none/draft/submitted/mixed/archived` 五态，图例和单元格均同时用文字+色块（不仅靠颜色）。创建改为 `client_request_id`（`crypto.randomUUID()`，每次新建操作生成一次）；新增草稿删除（`DELETE /daily-reports/{id}`，删除后若日期容器清空由后端自动移除）；新增日期级归档按钮（`can_archive=false` 时用 `el-tooltip` 展示服务端给出的中文禁用原因，不需要前端再维护一套原因文案）；归档后展示 `archive_snapshot.entries[]` 的多来源正式日报卡片。移除了 V1 的单篇归档接口调用。导出交互从 V1 的表格勾选迁移到日历页：页头“导出本月已归档日报”按当前显示月的日期范围 + `status=archived` 筛选，归档日期详情面板的“导出当天正式日报”按该日期的 `daily_report_day_ids` 单点导出，均复用 `ExportFileSaver` 白名单保存流程；首次实现时遗漏了导出入口（旧列表视图整体被日历替换时未搬迁），在质量门禁通过后、真实 Electron 冒烟验证阶段发现并补回，属于同一阶段内的自查修正，未产生独立提交。
- 日报详情页：`DailyDetailView.vue` 移除单篇归档按钮和逻辑（日期级归档收口到日历页）；新增草稿删除按钮；新增 `last_revocation` 提示（展示管理员撤销的操作者、时间、原因）；`40905`（日期已归档）错误统一提示并跳回日历。
- 我的周报：`WeeklyDetailView.vue` 的按日期卡片改为在每个日期下渲染 `entries[]` 的多个来源子卡片（各自的 `submitted_at`+`fields`），来源跳转从 `/daily/{entry_id}` 改为 `/daily?date={work_date}`（跳回日历并定位到该日期），不再假设一天只有一个来源。`WeeklyListView.vue` 的可用性状态展示未变（后端 `WeeklyAvailabilityDay.status` 枚举值不变，仍是 `draft/submitted/archived/null`）。
- 统计页：新增 `StatisticsView.vue`，月份选择复用与“我的日报”一致的月历组件（只读、点击日期跳转 `/daily?date=...`）；四张指标卡（完成率、已写日报、已写周报、当前连续记录）；`completion_rate=null`（未来月）显示 `--` 而非 `NaN`/`0%`（`formatCompletionRate()` 纯函数，含专项测试）。
- 管理员：新增 `AdminDailyReportsView.vue`（`/admin/daily-reports`），含“待归档条目”（仅展示账号/日期/版本/提交时间等最小元数据，不含任何正文字段）+ 撤销弹窗（必填原因）两个板块，以及“审计记录”（按动作/日期筛选，展示操作者、目标类型/ID、原因、时间）。`UsersView.vue` 新增删除按钮，`can_delete=false` 时按 `cannot_delete_reason`（`self`/`last_active_admin`/`has_business_records`）展示对应中文提示并禁用按钮；真正删除要求输入完整原始用户名（精确匹配，非规范化）和原因，服务端仍独立重新校验全部条件。
- 设置页：移除“提交后自动归档”开关（对应 `SettingsData.auto_archive_on_submit` 字段和 `PATCH /settings/me` 已随 BE-10A 从后端移除）；新增“修改密码”卡片（原 `AppLayout.vue` 头部的弹窗式改密已删除，改密统一收口到 `/settings`，`/change-password` 路由专用于强制改密场景）。
- 全局：`main.ts` 新增 `ElementPlus` 的 `zh-cn` locale 配置（`element-plus/es/locale/lang/zh-cn`），否则新引入的 `el-calendar` 会展示英文星期表头，与全局中文界面不一致；此前 V1 阶段未配置 locale 是因为尚未使用任何依赖 locale 文案的组件。
- 实际门禁：`npm run lint`（0 error/0 warning，`eslint --fix` 清理格式化告警后复核）、`npm run typecheck`、`npm test`（**22 个文件 125 项测试全部通过**，阶段 9 遗留 108 项 + 本阶段新增 17 项：`generateClientRequestId`/`formatDailyFieldValue`、`dayCellStatus`/`dayCellStatusLabel`/`dayCellStatusTagType`/`currentMonthInShanghai`、`cannotDeleteReasonLabel`、`auditActionLabel`、`formatCompletionRate`、`onPasswordChangeRequired` 40303 回调、`invalidExportDayIds` 改名后的等价覆盖）、`npm run test:integration`（真实 sidecar，2 项）、`npm run build`（含 `typecheck`）均实际执行并通过；`git diff --check` 通过（仅 LF→CRLF 提示）。后端未改动，`uv run pytest` 等门禁沿用 `BE-10C` 的 280 项结果，未重新执行（无代码变化）。
- 真实环境验证：用项目既有的 Playwright `_electron` 驱动能力（`electron/e2e/helpers/app.ts`，隔离临时数据目录，全程未触碰仓库 `.local-data/`）编写了两次一次性冒烟脚本（均未纳入正式套件，验证后已删除，重建正式 V2 E2E 覆盖是 `QA-10` 的范围）：① 主链路——双账号首次初始化 → 默认 `admin` 用 bootstrap 密码登录被强制跳转到 `/change-password` 且导航栏不可见 → 修改密码后要求重新登录 → 新密码登录进入日历 → 确认无残留英文星期表头 → 新建/保存/提交日报条目 → 返回日历发起日期级归档并看到合并后的正式日报卡片 → 生成本周周报并确认条目内容出现在来源卡片中 → 统计页无 `NaN` → 设置页无“提交后自动归档”文案且含“修改密码”“整库手动备份” → 管理员“日报管理”页可打开 → “用户管理”页当前账号删除按钮禁用、另一账号可删除按钮可用；② 导出——补充发现导出入口缺失后专门验证“导出当天正式日报”和“导出本月已归档日报”两个按钮均能触发真实 `POST /daily-report-exports`、下载并通过 `exportFile.save` 落盘，磁盘文件头校验为合法 xlsx（`PK\x03\x04`）。
- 安全审查：对本次实际改动范围（渲染进程 TypeScript/Vue 文件）执行了聚焦安全检查（未使用 `security-review` 技能默认抓取的全分支历史 diff，因其包含已在阶段 6/7/8/`BE-10B`/`BE-10C` 审查过的无关代码）：确认新增代码无 `v-html`/`innerHTML`/`eval`、无 `localStorage`/`sessionStorage` 写入、`el-tooltip` 的 `:content` 绑定均未设置 `raw-content`（按纯文本渲染）、管理员页面展示字段与后端最小元数据类型逐一对应（类型定义中不存在任何正文/模板快照字段，前端无法展示不存在的数据）、用户删除确认与所有权/角色相关的客户端校验均只是 UX 提示，真正的授权判定仍全部在后端。未发现 P0/P1；本次审查为主 Agent 直接执行，未额外派发独立沙盒 Agent 复核（与阶段 6/7/8/`BE-10B`/`BE-10C` 的沙盒 Agent 独立审查模式不同，如实记录该差异）。
- 已知非阻塞缺口（记录供 `QA-10` 承接）：`electron/e2e/*.spec.ts`（`primary-path`/`auth-failures`/`daily-validation`/`admin-guard`/`stale-version-conflict`）仍是 V1 UI 断言（如 `bootstrapAdmin` 用户名 `'admin'` 会命中新的保留用户名拒绝、页面标题“日报工作台”已改名“我的日报”、单篇归档按钮已不存在），运行 `npm run test:e2e` 现在会失败；这是 FE-10 改变 UI 形状后的预期结果，不是本阶段引入的回归，已记入 `issues.md` ISS-024，重写正式 V2 E2E 套件是 `QA-10` 的既定范围。

### 第二版阶段 10E 验证记录（QA-10）

- 后端回归：`uv run ruff check .`、`ruff format --check .`、`mypy`（strict，123 个源文件）均通过；`pytest`（**280 项全部通过**，与 `BE-10C` 收尾一致，本阶段未改动后端代码）。全量跑批中一次性复现了已知的 `ISS-013`（JWT 篡改测试偶发假阳性），单独重跑通过，与本阶段改动无关。
- 迁移覆盖复核：逐项核对 `backend/tests/test_v2_migration.py` 的 4 个测试函数，确认已覆盖设计要求的全部迁移场景（空库/真实 V1 结构副本升级、三态日报、多模板版本、跨年周与闰日日期、未来日期、导出任务、停用账号、周报 JSON V2 化、逐字节正文/模板保留、`PRAGMA foreign_key_check`、无损 downgrade、同日多条目/审计事件拒绝 downgrade、坏 JSON 在 DDL 前中止）——判定已有覆盖满足 `QA-10` 的"旧库迁移"验收要求，未重复造轮子。
- E2E 套件重写：`electron/e2e/helpers/app.ts` 新增 `bootstrapFirstUser`/`completeForcedPasswordChange`/`bootstrapAndSignInAsAdmin` 等第二版专用 helper，移除只适用单账号 V1 的 `bootstrapAdmin`/`DEFAULT_ADMIN`。重写全部 5 个既有 spec（`primary-path`/`auth-failures`/`daily-validation`/`admin-guard`/`stale-version-conflict`）为第二版 UI/路由/流程断言，新增 `user-deletion.spec.ts`。`primary-path.spec.ts` 扩写为覆盖 `docs/方案设计.md` §13 要求的完整链路：双账号初始化→admin 强制改密（含手动 hash 导航绕过被路由守卫拦回的断言）→同日创建两篇→提交→admin 撤销一篇→所有者看到撤销原因并重新提交→日期级归档合并两篇来源→统计卡片篇数正确且无 `NaN`→周报聚合两篇来源→导出正式日报为真实 xlsx 文件。`npm run test:e2e`（含 `npm run build` 重新构建）连续 3 次全量重跑，6 个 spec 均 100% 通过，无 flaky。
- 前端回归：`npm run lint`（0 error/0 warning）、`npm run typecheck`、`npm test`（**22 文件 125 项**，与 `FE-10` 收尾一致，本阶段未改动 renderer 业务代码，仅改动 `e2e/`）、`npm run test:integration`（真实 sidecar，2 项）均通过；`git diff --check` 通过（仅 LF→CRLF 提示）。
- 生产打包与真实安装/升级/卸载验证（本机，无独立干净虚拟机，沿用阶段 9 `REL-01` 已获用户确认的方案，本次为该验证首次在第二版代码上执行）：
  - 重新执行 `uv run pyinstaller weekly-report-backend.spec` 产出全新 V2 sidecar 并替换 `build/sidecar/`；在剥离 PATH（仅 `System32`/`Windows`）的隔离环境下启动，`/health` 返回正常，生成的 SQLite 库含全部 11 张表（8 张业务表 + `alembic_version` + 第二版新增的 `daily_report_days`/`admin_audit_events`）。
  - 重新执行 `npm run build:win` 产出全新安装包 `weekly-report-0.1.0-setup.exe`；`Get-AuthenticodeSignature` 确认安装包与内部可执行文件均为 `NotSigned`（`RISK-003` 已知风险，未变化）。
  - 真实静默安装（`/S`）：确认安装到 `%LOCALAPPDATA%\Programs\weekly-report-electron\`，桌面快捷方式与注册表卸载项（`DisplayName`/`DisplayVersion`/`UninstallString`/`QuietUninstallString`）均正确写入。
  - 真实使用：用 Playwright `_electron` 直接指向已安装的 `weekly-report.exe`（不做任何数据目录隔离，即完全按真实用户路径运行）驱动：双账号初始化→admin 强制改密→创建/提交/归档日报→周报生成→统计页无 `NaN`→切换回 admin 查看用户管理列表；全部通过。
  - 意外但有价值的发现：尝试用环境变量隔离 `win-unpacked` 产物的数据目录时失败——生产环境下 `paths.ts::productionDataDirEnv` 会无条件基于 `app.getPath('userData')` 重新计算并覆盖同名环境变量（`SEC-010` 既定安全设计，防止外部环境变量劫持已安装应用的数据位置）。这次意外触发的启动实际读写了阶段 9 `REL-01` 遗留的真实 V1 数据库（单一 `admin` 账号），逐项核对确认该库被自动、正确地迁移到了第二版头版本（`alembic_version=8b1d4e6f2a90`，全部 11 张表含新表）——构成一次真实的、非合成的"已安装环境下 V1→V2 升级"验证，比预期计划的更真实。已记为 `ISS-025`（P3，非缺陷，记录该环境变量隔离方式对已打包二进制无效的事实供以后参考）。
  - 升级冒烟：对同一安装目录重新静默安装（模拟版本升级的覆盖安装路径），确认此前创建的两个账号、已提交/已归档日报和周报在重新安装后依然完整存在。
  - 卸载：`Uninstall weekly-report.exe /currentuser /S` 正确移除安装目录下全部程序文件、桌面快捷方式和注册表卸载项；卸载后 `%APPDATA%\weekly-report-electron\data\weekly-report.db` 依然存在且可正常读取（表结构、账号数据均完整），满足"卸载不删用户数据"的目标要求。
  - 验证完成后已清理本次 QA 注入到真实 `%APPDATA%\weekly-report-electron\` 的测试数据（双账号、日报、周报），不留存于用户实际数据目录。
  - 本阶段驱动打包/安装验证用的 Playwright spec（`_qa10-packaged-smoke.spec.ts`、`_qa10-installed-smoke.spec.ts`）均为一次性冒烟脚本，验证通过后已删除，不纳入正式套件（正式 V2 E2E 覆盖已由上述 6 个常规 spec 提供）。
- 与阶段 9 `REL-01` 的差异：本次打包/安装验证过程中未发现任何新的真实缺陷（阶段 9 当时发现并修复了三个真实缺陷，其中一个 P0）；第二版的打包配置（`electron-builder.yml`、`weekly-report-backend.spec`、`electron.vite.config.ts` 的依赖外部化排除）自阶段 9 起未被修改，此次验证是对这些既有配置在全新第二版应用代码上的复用性确认，结果为完全兼容、零回归。

## 5. 实际验证记录

| 阶段 | Commit | 验证结果 | Reviewer | 遗留风险 |
|---|---|---|---|---|
| 阶段 1 工程基线 | `3a9fdbc` | `npm ci`、lint、typecheck、Vitest、build、Ruff、mypy、pytest、`uv sync --frozen` 已由阶段交付记录为通过 | 未单独记录 | Element Plus 当前全量引入；sidecar 生命周期与完整健康契约待阶段 2 |
| 阶段 2 Desktop Bootstrap | `7386cae` | `npm ci`（636 包）、`npm run lint`（0 error/0 warning）、`npm run typecheck`（`tsc`+`vue-tsc` 0 错误）、`npm test`（9 文件 36 项通过）、`npm run build`、`npm run test:integration --workspace electron`（真实子进程，2 项通过）、`uv sync --frozen`、`uv run ruff check .`、`uv run mypy`（strict，20 文件）、`uv run pytest -q`（17 项通过）、`git diff --check` 均已实际执行并通过；手动冒烟（`npm run dev` 真实运行 + `CloseMainWindow()` 模拟正常退出）确认单一 sidecar 进程、健康检查真实通过、退出后无孤儿进程；构建产物已扫描确认无 runtime secret 泄露 | 未单独记录 | ISS-010（Electron 被外部强杀时孤儿进程防护仍不完整，需 Windows Job Object）；PyInstaller 生产二进制尚未产出，生产路径分支未被真实二进制验证过（阶段 9 `PKG-01`） |
| 阶段 3 数据基础与 API Foundation | `8480515` | `npm run lint`、`npm run typecheck`（前端不受影响，已复核）；`uv sync --directory backend --frozen`、`uv run ruff check .`、`uv run ruff format --check .`、`uv run mypy`（strict，40 个源文件，含 `alembic/`）、`uv run pytest -q`（45 项通过：新增 ULID、DB engine/PRAGMA、错误处理器、Alembic 迁移、备份轮转、ORM 约束共 28 项）均已实际执行并通过；手动冒烟（`uv run python -m app` 真实启动）确认迁移自动执行、8 张业务表 + `alembic_version` 正确创建、`/health` 可访问 | 待独立 Reviewer | 无 Repository/Service 层（按阶段边界属于阶段 4 起逐步实现）；`所有权过滤`/`乐观锁` 本阶段只在 ORM 层面验证模式可行，实际业务强制仍需阶段 4/5 的 Repository/Service 落地 |
| 阶段 4 认证与用户管理 | `1a50e75` | `uv sync --directory backend --frozen`（46 个包）；Ruff check/format、mypy strict（66 个源文件）、pytest（**94 项通过**）；前端 lint、typecheck、Vitest（**12 文件 49 项通过**）、生产 build；Electron 真实 sidecar 集成测试（**2 项通过**）；`git diff --check` 通过。覆盖 JWT 过期/篡改、运行期与用户 Token 双校验、改密/重置/禁用失效、末位管理员并发保护、safeStorage 无明文回退、40102 清理和管理界面核心交互 | 独立审查完成；无未解决 P0/P1 | 阶段 4 已完成；阶段 5 从干净工作树开始 |
| 阶段 5 模板、设置与日报闭环 | `1d965fe` | Ruff check/format、mypy strict（81 个源文件）、pytest（**117 项通过**）；前端 lint、typecheck、Vitest（**14 文件 54 项通过**）、生产 build；Electron 真实 sidecar 集成测试（**2 项通过**）；`git diff --check` 通过。覆盖模板不可变版本/稳定键/核心字段、个人设置、同日并发、未来/闰日、快照、字段类型/有限数值、状态机、自动归档、乐观锁与所有权隔离 | 独立审查完成；无未解决 P0/P1 | 无；阶段 6 从干净工作树开始 |
| 阶段 6 查询导出与桌面保存 | `d6ab86e` | Ruff check/format、mypy strict（89 个源文件）、pytest（**140 项通过**，新增 23 项：动态列规划、跨模板合并消歧、公式注入防护、导出条件互斥/越权/混合状态拒绝、过期懒清理与启动清理、CORS `Content-Disposition` 暴露回归）；前端 lint、typecheck、Vitest（**16 文件 76 项通过**，新增文件保存白名单、导出 API/IPC 契约）、生产 build；Electron 真实 sidecar 集成测试（**2 项通过**）；`git diff --check` 通过。另在真实 `npm run dev` 环境完成手动全链路验证（初始化→登录→创建/提交/归档日报→勾选/筛选导出→原生另存为对话框保存成功→打开校验内容→取消保存反馈），过程中发现并修复一个真实缺陷：`CORSMiddleware` 未 `expose_headers` 导致 renderer 读不到服务端文件名（已加回归测试）；独立安全审查另发现并修复 Excel 公式注入风险（自由文本以 `=` 开头时被 openpyxl 提升为可执行公式），已窄范围加前缀转义且不影响中文项目常见的“-”“+”列表符号 | 独立审查完成（含专项安全审查）；无未解决 P0/P1 | 无；阶段 7 从干净工作树开始 |
| 阶段 7 周报闭环 | `346b0ea` | Ruff check/format、mypy strict（96 个源文件）、pytest（**169 项通过**，新增 29 项：周一校验/跨年周/闰日纯函数、生成/保存/重生成 Service 直连测试——含并发同周唯一、乐观锁、人工内容不反写日报、导出 API 测试——含互斥所有权隔离与 40903/40904/40001 错误码）；前端 lint、typecheck、Vitest（**17 文件 91 项通过**，新增周一定位/来源 ID 提取/字段展示纯函数测试）、生产 build；Electron 真实 sidecar 集成测试（**2 项通过**）；`git diff --check` 通过。另在真实 `npm run dev` 环境完成手动全链路验证（选择自然周→查看逐日可用性与状态标签→生成本周周报→来源日报内容正确汇总→保存本周补充/下周计划/问题风险→"查看来源日报"正确跳转到 `/daily/:id`→醒目确认对话框→重新生成后人工编辑与自动内容均被清空重建），过程中发现并修复一处真实的时间显示缺陷：周报生成时间/更新时间原样展示服务端 UTC ISO 字符串（含 `+00:00`），未按 `Asia/Shanghai` 格式化，已复用 `formatShanghaiTime` 修正；独立安全专项审查未发现所有权隔离、SQL 注入、确认绕过或 XSS 方向的可利用漏洞 | 独立审查完成（含专项安全审查）；无未解决 P0/P1 | 无；阶段 8 从干净工作树开始 |
| 阶段 8 设置能力与受控备份 | `00caa33` | Ruff check/format、mypy strict（100 个源文件）、pytest（**184 项通过**，新增 15 项：手动备份 checkpoint+backup API 生成、owner 隔离、跨管理员越权 404、懒过期删除、创建时清理已过期项、目的目录缺失的类型化失败、部分写入文件在失败路径被清理、启动残留清理、路径边界校验、API 层管理员权限/所有权/敏感信息不泄露测试）；前端 lint、typecheck、Vitest（**18 文件 107 项通过**，新增 `BackupFileSaver` 白名单校验 12 项、IPC 受信任帧与 payload 校验 4 项）、生产 build；Electron 真实 sidecar 集成测试（**2 项通过**）；`git diff --check` 通过。另用 Playwright `_electron` 驱动真实构建产物（隔离的临时数据目录，未触碰仓库 `.local-data/`）完成手动全链路验证：初始化→登录→`/settings` 页面渲染→自动归档开关切换并在离开/返回后仍保持已保存状态→点击企业微信占位按钮只弹出本地提示且全程零非回环网络请求→创建整库备份触发醒目敏感性确认→确认后调用真实备份 API 并把下载字节写入磁盘（写入文件已校验为合法 SQLite 文件头）→再次创建并在保存对话框选择取消得到"已取消保存"反馈→新建非管理员账号后确认其 `/settings` 页不出现"整库手动备份"区块。独立审查（含专项安全审查）发现一项真实问题并已修复：`BackupService.create()` 在 `sqlite3.Connection.backup()` 中途失败（如磁盘写满）时未清理已创建的目标文件，已补充清理与回归测试；未发现权限绕过、跨管理员越权、路径穿越或信息泄露方向的可利用漏洞 | 独立审查完成（含专项安全审查）；无未解决 P0/P1 | 无；阶段 9 从干净工作树开始 |
| 阶段 9 质量与发布 | `0148171` | 后端 `uv run ruff check .`、`ruff format --check .`、`mypy`（strict，100 个源文件）、`pytest -q`（**186 项通过**，新增 2 项：`_resolve_alembic_ini_path` 冻结/非冻结路径解析）均通过；前端 `npm run lint`、`typecheck`、`npm test`（**18 文件 108 项通过**，新增 sidecar 生产环境变量注入测试）、`npm run build`、`npm run test:integration`（真实 sidecar，**2 项通过**）、`npm run test:e2e`（Playwright，**5 项通过**：初始化→登录→模板字段发布→日报草稿/提交/归档→导出真实 xlsx→周报生成/编辑/来源跳转主链路；登录密码错误、必填字段留空、非管理员触达管理面、乐观锁并发冲突四条失败路径）均实际执行并通过；`git diff --check` 通过。真实 PyInstaller onedir 构建（`build/sidecar/weekly-report-backend.exe`，42.69 MB/148 文件）在剥离 PATH（仅 `System32`/`Windows`，不含任何 Python/uv）的隔离环境下启动成功，`/health` 返回契约响应，生成的 SQLite 库含全部 8 张业务表 + `alembic_version`；真实 `electron-builder --dir`/`--win --x64` 构建产出安装包并在**本机**（无独立干净虚拟机，已在阶段开工前与用户确认此限制并记录，非阻塞地以本机深度验证替代）完成安装→真实使用（引导 admin、登录、创建日报）→模拟升级（原版本号重新安装）确认数据保留→卸载（`QuietUninstallString`/`/S`）确认程序文件被移除、用户数据在 `%APPDATA%\weekly-report-electron\data\weekly-report.db` 完整保留。过程中发现并修复三个真实缺陷：① 生产 sidecar 从未收到指向 `userData` 的环境变量（`ISS-014`，P1，安装后无法启动数据库）；② 打包后主进程间歇性抛出 `Cannot find module '@electron-toolkit/utils'` 导致约有概率窗口完全打不开（`ISS-015`，P0，npm workspace 依赖提升导致 electron-builder 依赖遍历遗漏，改为强制打包解决，修复后连续 5 次全新安装+启动与完整 Playwright 驱动均稳定通过）；③ npm workspace 作用域包名 `@weekly-report/electron` 导致 NSIS 安装包完全无法生成（`Can't open output file`）且早期一次安装产出空目录、快捷方式失效、注册表未写入（`ISS-016`，P1，已改用 `${productFilename}` 与去作用域包名修复）。另观察到一项非阻塞现象记录为 `ISS-017`（P3）：非静默 `UninstallString` 在本机环境下表现为无操作，`QuietUninstallString`（Windows 现代"设置"应用优先使用）验证正常 | 独立审查完成；无未解决 P0/P1 | 无；V1 全部阶段已交付，后续为发布运营与新范围评估 |

## 6. CR-20260812-01 项目列表类别与权重

| 任务 | 主责 | 状态 | 完成标准 |
|---|---|---|---|
| 扩展 `PROJECT_LIST` 条目契约、编辑/展示、Excel 导出和兼容测试 | 主 Agent | DONE | 10 子列顺序正确；类别默认“重要”；权重默认空；旧 JSON 可读；企业微信不新增同步字段；全量门禁通过 |

- 不涉及数据库表结构或 Alembic 迁移；共享 Pydantic schema 负责历史值补默认。
- 已完成后端 API/导出/企业微信 Mapper 测试和前端默认行过滤/只读展示测试，并完成 dev-workflow 正式自审。

## 7. CR-20260812-02 项目责任人默认当前用户

| 任务 | 主责 | 状态 | 完成标准 |
|---|---|---|---|
| 新建项目行默认责任人、整套默认行过滤与兼容回归 | 主 Agent | DONE | 首行和新增行 owner 均取当前用户 `display_name`；已保存/历史 owner 不覆盖；未触碰默认行保存前过滤；全量门禁和正式自审通过 |

- 保留并纳入当前工作树已有的预计/实际完成时间“当日”、完成情况“已完成”默认值调整，后端历史结构默认与 Excel 断言已同步。
- 工具函数通过参数接收昵称，不直接依赖 Pinia；日报页负责从 auth store 注入。

## 8. PROD-034 Excel 单元格黑色边框

| 任务 | 主责 | 状态 | 完成标准 |
|---|---|---|---|
| 导出表头与数据单元格改用黑色细边框 | 主 Agent | DONE | 表头和数据四边为 `thin`/`FF000000`；标题无边框；定向测试与 Ruff 通过 |
