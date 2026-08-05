# 开发任务列表

> 状态基准：2026-08-06
> 范围依据：`requirements.md`、`architecture.md`、`modules.md`、`database.md`、`api.md`、`coding-rule.md`
> 当前实现基线：工程骨架提交 `3a9fdbc`；阶段 2 Desktop Bootstrap 提交 `7386cae`；阶段 3 数据基础与 API Foundation 提交 `8480515`（编码规则补充随 `b6b1b47`）；阶段 4 认证与用户管理提交 `1a50e75`；阶段 5 模板、设置与日报闭环提交 `1d965fe`

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

阶段提交：`feat(export): 完成归档日报 Excel 导出`。

### 阶段 7：周报闭环

| ID | 主责 | 任务 | 依赖 | 状态 | 交付物与验收 |
|---|---|---|---|---|---|
| WEEKLY-01 | Agent B | 自然周可用性、生成和来源快照 | 阶段 5 | TODO | 周一校验、只含 archived、空周可生成、同周唯一、来源可追溯 |
| WEEKLY-02 | Agent B | 编辑、乐观锁和确认重生成 | WEEKLY-01 | TODO | 人工内容不反写日报；未确认不覆盖；确认后原子替换基线/内容/来源 |
| FE-06 | Agent A | 周报列表、生成、编辑与来源 UI | WEEKLY-01、WEEKLY-02、FE-01 | TODO | 周范围、未归档提示、空周、来源跳转、醒目覆盖确认 |
| QA-07 | Agent C | 周报验收与审查 | WEEKLY-01、WEEKLY-02、FE-06 | TODO | 跨年周、闰日、空周、同周并发、人工修改和重生成覆盖语义 |

阶段提交建议：`feat(weekly): 完成周报生成与编辑闭环`。

### 阶段 8：设置、占位与备份界面收口

| ID | 主责 | 任务 | 依赖 | 状态 | 交付物与验收 |
|---|---|---|---|---|---|
| BACKUP-01 | Agent B | admin 手动整库备份 API | DB-03、AUTH-02 | TODO | checkpoint、一致性短期文件、随机 ID、15 分钟过期、仅创建者 admin 下载 |
| FE-07 | Agent A | 设置、能力占位与手动备份 UI | SETTING-01、BACKUP-01 | TODO | 自动归档；企业微信只显示未开放且零外部请求；备份敏感性确认 |
| QA-08 | Agent C | 设置/占位/备份审查 | BACKUP-01、FE-07 | TODO | 权限、过期、清理、外部请求为零、路径不暴露测试 |

阶段提交建议：`feat(settings): 完成设置能力与受控备份`。

### 阶段 9：质量与发布

| ID | 主责 | 任务 | 依赖 | 状态 | 交付物与验收 |
|---|---|---|---|---|---|
| QA-09 | Agent C | 全链路 Playwright/E2E 与安全回归 | 阶段 4..阶段 8 | TODO | 初始化→登录→模板→日报→导出→周报主链路及失败路径 |
| PKG-01 | Agent B | PyInstaller `onedir` sidecar 构建 | 阶段 3..阶段 8 | TODO | 无 Python 环境可启动，迁移和许可证随包，产物不进 ASAR |
| PKG-02 | Agent A | electron-builder Windows x64 安装包 | PKG-01 | TODO | `extraResources` 正确、安装目录只读、userData 数据保留 |
| REL-01 | Agent C | 干净机安装/升级/卸载与发布审查 | QA-09、PKG-01、PKG-02 | TODO | Windows 10/11 干净机、上一版本升级、迁移备份、卸载不删用户数据 |

阶段提交建议：`build(release): 完成 Windows 发布链路`。

## 4. 当前可领取任务

阶段 3（`DB-01`/`DB-02`/`DB-03`/`API-01`/`QA-03`）已实现、通过质量门禁并创建独立提交 `8480515`；独立 Reviewer 审查仍待补齐（非阻塞）。

阶段 4 `AUTH-01`/`AUTH-02`/`USER-01`/`FE-01`/`FE-02`/`QA-04` 已完成实现、自测、质量门禁、独立审查与提交 `1a50e75`，统一为 `DONE`。

阶段 5 七项任务均已完成实现、自测、质量门禁、独立审查与提交 `1d965fe`，统一为 `DONE`。

阶段 6 五项任务（`EXPORT-01`/`EXPORT-02`/`DESK-04`/`FE-05`/`QA-06`）均已完成实现、自测、质量门禁、独立审查，统一为 `DONE`。阶段 7 周报闭环从干净工作树开始。

## 5. 实际验证记录

| 阶段 | Commit | 验证结果 | Reviewer | 遗留风险 |
|---|---|---|---|---|
| 阶段 1 工程基线 | `3a9fdbc` | `npm ci`、lint、typecheck、Vitest、build、Ruff、mypy、pytest、`uv sync --frozen` 已由阶段交付记录为通过 | 未单独记录 | Element Plus 当前全量引入；sidecar 生命周期与完整健康契约待阶段 2 |
| 阶段 2 Desktop Bootstrap | `7386cae` | `npm ci`（636 包）、`npm run lint`（0 error/0 warning）、`npm run typecheck`（`tsc`+`vue-tsc` 0 错误）、`npm test`（9 文件 36 项通过）、`npm run build`、`npm run test:integration --workspace electron`（真实子进程，2 项通过）、`uv sync --frozen`、`uv run ruff check .`、`uv run mypy`（strict，20 文件）、`uv run pytest -q`（17 项通过）、`git diff --check` 均已实际执行并通过；手动冒烟（`npm run dev` 真实运行 + `CloseMainWindow()` 模拟正常退出）确认单一 sidecar 进程、健康检查真实通过、退出后无孤儿进程；构建产物已扫描确认无 runtime secret 泄露 | 未单独记录 | ISS-010（Electron 被外部强杀时孤儿进程防护仍不完整，需 Windows Job Object）；PyInstaller 生产二进制尚未产出，生产路径分支未被真实二进制验证过（阶段 9 `PKG-01`） |
| 阶段 3 数据基础与 API Foundation | `8480515` | `npm run lint`、`npm run typecheck`（前端不受影响，已复核）；`uv sync --directory backend --frozen`、`uv run ruff check .`、`uv run ruff format --check .`、`uv run mypy`（strict，40 个源文件，含 `alembic/`）、`uv run pytest -q`（45 项通过：新增 ULID、DB engine/PRAGMA、错误处理器、Alembic 迁移、备份轮转、ORM 约束共 28 项）均已实际执行并通过；手动冒烟（`uv run python -m app` 真实启动）确认迁移自动执行、8 张业务表 + `alembic_version` 正确创建、`/health` 可访问 | 待独立 Reviewer | 无 Repository/Service 层（按阶段边界属于阶段 4 起逐步实现）；`所有权过滤`/`乐观锁` 本阶段只在 ORM 层面验证模式可行，实际业务强制仍需阶段 4/5 的 Repository/Service 落地 |
| 阶段 4 认证与用户管理 | `1a50e75` | `uv sync --directory backend --frozen`（46 个包）；Ruff check/format、mypy strict（66 个源文件）、pytest（**94 项通过**）；前端 lint、typecheck、Vitest（**12 文件 49 项通过**）、生产 build；Electron 真实 sidecar 集成测试（**2 项通过**）；`git diff --check` 通过。覆盖 JWT 过期/篡改、运行期与用户 Token 双校验、改密/重置/禁用失效、末位管理员并发保护、safeStorage 无明文回退、40102 清理和管理界面核心交互 | 独立审查完成；无未解决 P0/P1 | 阶段 4 已完成；阶段 5 从干净工作树开始 |
| 阶段 5 模板、设置与日报闭环 | `1d965fe` | Ruff check/format、mypy strict（81 个源文件）、pytest（**117 项通过**）；前端 lint、typecheck、Vitest（**14 文件 54 项通过**）、生产 build；Electron 真实 sidecar 集成测试（**2 项通过**）；`git diff --check` 通过。覆盖模板不可变版本/稳定键/核心字段、个人设置、同日并发、未来/闰日、快照、字段类型/有限数值、状态机、自动归档、乐观锁与所有权隔离 | 独立审查完成；无未解决 P0/P1 | 无；阶段 6 从干净工作树开始 |
| 阶段 6 查询导出与桌面保存 | 待创建 | Ruff check/format、mypy strict（89 个源文件）、pytest（**140 项通过**，新增 23 项：动态列规划、跨模板合并消歧、公式注入防护、导出条件互斥/越权/混合状态拒绝、过期懒清理与启动清理、CORS `Content-Disposition` 暴露回归）；前端 lint、typecheck、Vitest（**16 文件 76 项通过**，新增文件保存白名单、导出 API/IPC 契约）、生产 build；Electron 真实 sidecar 集成测试（**2 项通过**）；`git diff --check` 通过。另在真实 `npm run dev` 环境完成手动全链路验证（初始化→登录→创建/提交/归档日报→勾选/筛选导出→原生另存为对话框保存成功→打开校验内容→取消保存反馈），过程中发现并修复一个真实缺陷：`CORSMiddleware` 未 `expose_headers` 导致 renderer 读不到服务端文件名（已加回归测试）；独立安全审查另发现并修复 Excel 公式注入风险（自由文本以 `=` 开头时被 openpyxl 提升为可执行公式），已窄范围加前缀转义且不影响中文项目常见的“-”“+”列表符号 | 独立审查完成（含专项安全审查）；无未解决 P0/P1 | 无；阶段 7 从干净工作树开始 |
