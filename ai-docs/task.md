# 开发任务列表

> 状态：V1 初始拆分  
> 更新日期：2026-08-05  
> 当前仓库状态：DESK-01 验收通过（2026-08-05）并已提交，转 `DONE`；BE-01 窄范围复审已通过且历史问题全部关闭，待提交后关闭；后续桌面任务以现有 `electron/` workspace 为基线

## 1. 状态与执行规则

状态：`TODO`（可领取）、`READY`（依赖满足）、`IN_PROGRESS`、`BLOCKED`、`IN_REVIEW`、`DONE`。

任务领取后在任务行填写主责 Agent、分支/工作区和开始日期。任何任务进入 `IN_PROGRESS` 前，必须读取全部 `ai-docs`，确认依赖均为 `DONE`，并在任务备注记录架构核对结果。

每个任务完成时补充：

```text
Owner:
Branch/Commit:
Changed files:
Verification:
Reviewer:
Review result:
Risks/Follow-ups:
```

## 2. 里程碑与依赖

```text
M0 文档基线
  -> M1 工程与桌面运行骨架
      -> M2 数据/接口基础
          -> M3 认证与用户闭环
              -> M4 模板与日报闭环
                  -> M5 导出与周报闭环
                      -> M6 集成、安全与发布
```

- M0～M3 是第一个可运行里程碑。
- M4 是日报业务闭环。
- M5 是 V1 完整功能闭环。
- M6 通过后才允许发布候选包。

## 3. 任务总表

| ID | 任务 | 主责域 | 依赖 | 状态 | Owner |
|---|---|---|---|---|---|
| DOC-01 | 建立 ai-docs 架构基线与任务拆分 | Architecture | - | DONE | 首席架构师 |
| GOV-01 | 建立根级检查命令与 CI 质量门禁 | Cross | FE-01, BE-01 | TODO | - |
| DESK-01 | electron-vite 桌面骨架基线（替代原 electron-egg V5）并建立工程目录 | Desktop | DOC-01 | DONE | 桌面平台工程师 |
| BE-01 | 初始化 FastAPI/uv 工程 | Backend | DOC-01 | IN_REVIEW | Python 后端基础设施工程师 Agent |
| FE-01 | 初始化 Vue3/TS 前端工程与基础布局 | Frontend | DESK-01 | TODO | - |
| DESK-02 | sidecar 动态端口、启停和健康检查 | Desktop | DESK-01, BE-01 | TODO | - |
| DESK-03 | 安全 preload、运行时桥接与 safeStorage | Desktop | DESK-01 | TODO | - |
| BE-02 | 配置、日志、请求 ID、统一响应与异常 | Backend | BE-01 | TODO | - |
| DB-01 | SQLAlchemy 基础、SQLite PRAGMA 与初始迁移 | Data | BE-01 | TODO | - |
| DB-02 | 迁移前备份、轮转和失败停止 | Data/Desktop | DB-01, DESK-02 | TODO | - |
| API-01 | 运行期密钥、CORS 和认证依赖框架 | Backend | BE-02, DESK-03 | TODO | - |
| TPL-01 | 模板模型、默认模板和不可变版本服务 | Backend | DB-01, BE-02 | TODO | - |
| AUTH-01 | 首次初始化、密码哈希和默认用户资产 | Backend | TPL-01, DB-01, BE-02 | TODO | - |
| AUTH-02 | 登录、JWT、token_version、me、改密和退出 | Backend | AUTH-01, API-01 | TODO | - |
| USER-01 | 管理员用户管理与末位管理员保护 | Backend | AUTH-02 | TODO | - |
| BACKUP-01 | admin 手动整库备份和短期下载 API | Backend | DB-02, AUTH-02 | TODO | - |
| FE-AUTH-01 | setup/login、Token 生命周期和鉴权路由 | Frontend | FE-01, DESK-03, AUTH-02 | TODO | - |
| FE-USER-01 | 用户管理页面 | Frontend | FE-AUTH-01, USER-01 | TODO | - |
| TPL-02 | 模板 API、字段规则和版本摘要 | Backend | TPL-01, AUTH-02 | TODO | - |
| FE-TPL-01 | 动态字段组件与模板配置页面 | Frontend | FE-AUTH-01, TPL-02 | TODO | - |
| SET-01 | 用户设置和 capabilities API | Backend | AUTH-02, DB-01 | TODO | - |
| FE-SET-01 | 设置页面与企业微信占位 | Frontend | FE-AUTH-01, SET-01 | TODO | - |
| FE-BACKUP-01 | admin 手动备份与 Electron 保存流程 | Frontend/Desktop | FE-AUTH-01, BACKUP-01, DESK-03 | TODO | - |
| DAILY-01 | 日报模型、创建唯一性与模板快照 | Backend | TPL-01, AUTH-02 | TODO | - |
| DAILY-02 | 草稿保存、类型校验与乐观锁 | Backend | DAILY-01 | TODO | - |
| DAILY-03 | 提交/归档状态机和自动归档事务 | Backend | DAILY-02, SET-01 | TODO | - |
| DAILY-04 | 日报列表、筛选和详情 API | Backend | DAILY-01 | TODO | - |
| FE-DAILY-01 | 日报列表、筛选和新建流程 | Frontend | FE-TPL-01, DAILY-04 | TODO | - |
| FE-DAILY-02 | 日报详情、草稿保存、提交和归档 | Frontend | FE-DAILY-01, DAILY-02, DAILY-03 | TODO | - |
| EXPORT-01 | 导出任务、动态列规划和 Excel 生成 | Backend | DAILY-04, DB-01 | TODO | - |
| EXPORT-02 | 导出状态/下载 API 与临时文件清理 | Backend | EXPORT-01 | TODO | - |
| FE-EXPORT-01 | 导出交互和 Electron 保存流程 | Frontend/Desktop | FE-DAILY-01, EXPORT-02, DESK-03 | TODO | - |
| WEEK-01 | 周范围与可用性查询 | Backend | DAILY-04 | TODO | - |
| WEEK-02 | 周报生成、空周和来源追溯 | Backend | WEEK-01 | TODO | - |
| WEEK-03 | 周报编辑、乐观锁和确认重生成 | Backend | WEEK-02 | TODO | - |
| FE-WEEK-01 | 周报列表、选择和可用性提示 | Frontend | FE-AUTH-01, WEEK-01 | TODO | - |
| FE-WEEK-02 | 周报详情、编辑、来源和覆盖确认 | Frontend | FE-WEEK-01, WEEK-02, WEEK-03 | TODO | - |
| INT-01 | 前后端契约回归与核心 E2E | QA | FE-DAILY-02, FE-EXPORT-01, FE-WEEK-02, FE-USER-01, FE-SET-01, FE-BACKUP-01 | TODO | - |
| SEC-01 | Electron/API/所有权安全专项审查 | Security | INT-01 | TODO | - |
| PERF-01 | 查询索引、SQLite busy 和大导出验证 | QA/Data | INT-01 | TODO | - |
| PKG-01 | electron-vite 产物、PyInstaller sidecar 与安装包资源 | Release | DESK-02, DB-02, GOV-01 | TODO | - |
| PKG-02 | 干净机安装、升级、卸载和数据保留验证 | Release/QA | PKG-01, INT-01, SEC-01, PERF-01 | TODO | - |
| REL-01 | V1 发布评审与文档收口 | Architecture | PKG-02 | TODO | - |

## 4. 任务明细

### M0：治理基线

#### DOC-01 建立架构基线与任务拆分 — DONE

- 交付物：`requirements.md`、`architecture.md`、`modules.md`、`database.md`、`api.md`、`coding-rule.md`、`task.md`。
- 验收：七份文档互相引用一致；未改变 `docs/方案设计.md` 的核心架构。

#### GOV-01 根级检查命令与 CI

- 范围：以根 npm workspace 为唯一 Node 入口，将根 `package.json#engines.node` 收敛为 Node.js 22.12+ LTS，提供 install/dev/lint/typecheck/test/build 命令；CI 分 electron-vite、后端、E2E/打包阶段。
- 验收：Node.js 22.12+ LTS、npm 10+；`npm ci` 和 `uv sync --frozen` 可复现且不改锁文件；`npm run build` 产出 `electron/out/{main,preload,renderer}`；任一 lint、类型或测试失败会阻止合并。
- 评审重点：固定 electron-vite/Electron/electron-builder/npm/uv 版本；CI 不上传 `.env`、运行期密钥、数据库、日志或工作正文。

### M1：工程与桌面运行骨架

#### DESK-01 固定桌面工程基线

- 独立任务说明：`ai-docs/tasks/DESK-01.md`。
- 当前处理：已按 electron-vite 实现；2026-08-05 窄范围复审确认 Node 基线、导航实现、CSP 分离和许可证数量修复有效，但导航白名单没有仓库内可重复执行的测试，仍为 `Request Changes` 并保持 `IN_REVIEW`；不安排框架替换重做或 GUI 复测。
- 交付物：记录 electron-vite/Electron 固定版本和许可证；建立 `electron/src/{main,preload,renderer}`、`backend/`、`build/` 与根 npm workspace；补齐 `.gitignore`。
- 验收：应用可显示空壳窗口；`.local-data`、日志、数据库、备份和构建缓存均不被 Git 跟踪。
- 评审重点：只引入桌面骨架；electron-vite 只负责构建，Electron Main/Preload 不作为业务后端。
- 审查：窄范围复审当前 P0=0、P1=1、P2=1（镜像策略按用户指示未复核）、P3=0。Node.js 22.12+ 基线已落实；`will-navigate` 实现的 12 个安全用例均通过，但缺少持久化测试文件和 `test` 脚本，现有 lint/typecheck/build 无法阻止安全策略回归。完整报告见 `docs/electron/代码审查.md`。P1 关闭前不得转 `DONE`，FE-01、DESK-03 仍不得按依赖开工。

#### BE-01 初始化 FastAPI/uv 工程

- 独立任务说明：`ai-docs/tasks/BE-01.md`。
- 交付物：`pyproject.toml`、`uv.lock`、应用入口、测试骨架、Ruff/mypy/pytest 配置。
- 验收：开发命令启动单 worker，最小测试和质量检查通过；依赖锁定。
- 审查：2026-08-04 首轮结论 `Approved`；2026-08-05 窄范围复审确认 P2-01、P2-02、P3-01 均已关闭，当前未关闭问题 P0/P1/P2/P3 均为 0。冻结安装、Ruff、mypy、pytest 和真实启动探活均复验通过，详见 `docs/backend/代码审查.md`。9 个后端文件及对应任务/审查文档仍未提交，按 DoD 保持 `IN_REVIEW`，提交经复审的精确文件集后方可改为 `DONE`。

#### FE-01 初始化前端工程

- 范围：接管现有 `electron/src/renderer` 占位页，不重新脚手架、不创建根 `frontend/`；在 `electron/package.json` 中补充 Vue Router、Pinia、Element Plus、Axios、Vitest 等依赖。
- 交付物：`electron/src/renderer/src/{api,components,layouts,router,stores,types,views}`、基础布局、路由、测试配置；必要的 alias 统一维护在 `electron/electron.vite.config.ts`。
- 验收：从仓库根执行 npm workspace 命令；严格类型检查、单测和 `npm run build` 通过；renderer 构建进入 `electron/out/renderer`；保持现有 CSP、禁止 Node API，生产配置不包含业务假数据或敏感环境变量。

#### DESK-02 sidecar 生命周期

- 实现位置：在 `electron/src/main` 新建职责单一的 `service/backend-process.ts`（或等价目录）并由现有 `index.ts` 装配；不得把全部生命周期继续堆入入口文件。
- 开发启动：以 `backend/` 为 `cwd` 启动 `uv run`，传入动态端口、数据/日志目录和随机 runtime secret；生产启动：仅从 `process.resourcesPath/sidecar` 解析 PyInstaller `onedir` 入口。
- 交付物：回环动态端口、每次启动随机密钥、开发/生产命令选择、`GET /health` 轮询、启动错误页、正常/异常退出清理和脱敏诊断。
- 验收：重复启动保持单实例；electron-vite 主进程热重载、窗口重建和应用退出均不会产生第二个 sidecar 或残留进程；健康检查成功前不开放业务页；后端只监听 `127.0.0.1`。
- 测试：端口竞争、健康超时、uv/sidecar 不存在、迁移失败、sidecar 意外退出、退出超时、electron-vite HMR 重启、`process.resourcesPath` 含空格。
- 禁止：将 PyInstaller 可执行文件打入 ASAR、使用开发机绝对路径、依赖源码目录 `cwd`、通过 renderer 启动进程或使用 electron-vite 的 Node 子进程打包语法包装外部 Python sidecar。

#### DESK-03 安全运行时桥接

- 实现位置：`electron/src/preload/index.ts`、`index.d.ts` 及 `electron/src/main` 下按能力拆分的 IPC handler；不得创建第二套 preload。
- 交付物：contextBridge 类型化白名单，API 基址/运行期请求头读取、`safeStorage` Token 存取、受控保存对话框和外链白名单。
- 契约：每个 IPC channel 集中命名并验证 sender/参数；禁止暴露通用 `ipcRenderer`、`electronAPI`、文件路径、shell 或命令执行。runtime secret 只能由 Main 在运行期产生，经窄桥接供 API client 使用，不得进入 `VITE_`/`RENDERER_VITE_` 或静态 bundle。
- electron-vite 约束：preload 保持 sandbox；如新增第三方依赖，必须证明其已在 preload 中完整打包或移动到 Main，不得设置 `sandbox=false`。
- 验收：renderer 无 Node/任意 IPC/任意文件访问；Token 不写 localStorage；`safeStorage` 不可用有明确失败/降级提示且不落明文；`npm run build` 后 preload 在 `electron/out/preload` 可加载。

### M2：数据与 API 基础

#### BE-02 API 基础设施

- 交付物：配置加载、请求 ID、统一成功/错误包装、Pydantic 错误转换、脱敏日志。
- 验收：所有错误符合 `api.md`；500 不暴露堆栈/路径；响应带请求 ID。

#### DB-01 数据库基础与初始迁移

- 交付物：Engine/Session、PRAGMA、全部 V1 ORM 表、显式约束/索引、初始 Alembic migration。
- 验收：新库升级成功，外键开启，单 worker；模型与 `database.md` 一致。
- 测试：唯一约束、外键、CHECK、WAL 和 busy_timeout。

#### DB-02 备份与迁移保护

- 交付物：checkpoint、一致性备份、最近 10 份轮转、迁移失败停止和手动备份服务接口。
- 验收：备份失败不迁移；轮转不越出备份目录；旧库升级后数据完整。

#### BACKUP-01/FE-BACKUP-01 admin 手动整库备份

- 交付物：checkpoint 后一致性快照、15 分钟短期下载、admin 权限校验、敏感数据提示和 Electron 保存。
- 验收：普通用户 403；API 不返回内部路径；过期文件不可下载并会清理；取消保存不误报成功；备份能被 SQLite 完整性检查打开。
- 评审重点：备份包含全体用户数据，任何日志和 renderer 状态都不得暴露内部文件路径或内容。

#### API-01 本地 API 安全框架

- 交付物：运行期密钥校验、精确 CORS、JWT 依赖骨架、请求大小/安全头基础配置。
- 验收：缺失/错误 runtime secret 被拒绝；不允许通配 CORS；日志不包含密钥。

### M3：认证与用户闭环

#### AUTH-01 初始化与密码基础

- 交付物：Argon2id、bootstrap status/admin、用户创建资产服务（设置+默认模板）。
- 验收：仅空用户表可初始化；并发初始化只产生一个 admin；密码不以明文出现。

#### AUTH-02 登录与 Token 生命周期

- 交付物：login/me/password/logout、24h JWT、每次鉴权校验 active 和 token_version。
- 验收：密码修改后旧 Token 立即失效；禁用用户旧 Token 失效；错误登录不泄露用户名存在性。

#### USER-01 用户管理

- 交付物：用户分页、创建、元数据详情、角色/状态修改、重置密码。
- 验收：只有 admin 可用；无法禁用/降级最后一个有效 admin；不返回他人业务内容。

#### FE-AUTH-01 初始化与登录 UI

- 交付物：setup/login、authStore、Axios 拦截器、权限路由和登出清理。
- 验收：首次启动流正确；40102 清 Token 跳登录；Token 不进 localStorage；失败不泄露内部错误。

#### FE-USER-01 用户管理 UI

- 交付物：用户列表、创建/编辑/启停/重置密码交互。
- 验收：普通用户无入口且路由拒绝；危险操作确认；末位管理员错误可理解。

### M4：模板、设置与日报闭环

#### TPL-01/TPL-02 模板后端

- 交付物：默认核心字段、字段 schema、不可变版本、current/versions API。
- 验收：核心字段不可删除且至少启用一个；field_key 稳定；选项非空不重复；旧版本不被修改。
- 测试：六种字段类型、重命名/排序、并发发布、非法选项和历史不可变性。

#### FE-TPL-01 动态字段与模板 UI

- 交付物：六类字段渲染器、模板字段增配/排序/启停和版本展示。
- 验收：客户端约束与服务端错误均正确展示；已有 field_key 不被重新生成。

#### SET-01/FE-SET-01 设置与能力

- 交付物：自动归档设置、固定时区、capabilities、设置页和企业微信占位。
- 验收：wecom_sync 始终 false；点击不调用外部网络或不存在的同步 API。

#### DAILY-01 日报创建与快照

- 交付物：日报模型服务、按当前模板创建草稿、同日唯一冲突处理。
- 验收：创建原子固化版本/快照；重复创建返回 40901 和已有 ID；支持历史/未来日期。

#### DAILY-02 草稿保存

- 交付物：快照驱动的内容校验、PATCH 条件更新和新 version 返回。
- 验收：只有 draft 可保存；未知字段/类型错误被拒绝；旧 version 返回 40904 且不覆盖。

#### DAILY-03 状态机

- 交付物：submit/archive 与自动归档事务。
- 验收：必填缺失保持 draft；submitted 不可编辑；自动归档的两个时间和最终状态原子写入；重复操作不改时间。

#### DAILY-04 查询与详情

- 交付物：日期/状态筛选、分页稳定排序、详情与所有权过滤。
- 验收：组合筛选正确；越权/不存在行为一致；返回快照而非当前模板。

#### FE-DAILY-01/02 日报 UI

- 交付物：列表/筛选/创建、动态详情、保存、提交、归档和冲突恢复。
- 验收：loading 防重复；保存失败保留输入；40901 可跳已有日报；40904 提示重载；归档后只读。

### M5：导出与周报闭环

#### EXPORT-01/02 Excel 导出

- 交付物：导出任务模型服务、选择校验、动态列算法、xlsx、状态/文件 API、24h 清理。
- 验收：只导出本人 archived；不同模板版本字段不丢；同名列消歧；内部路径不出 API。
- 测试：空结果、非法 ID、他人 ID、混入未归档、重复标签、大数据和清理边界。

#### FE-EXPORT-01 导出 UI/保存

- 交付物：按选择/筛选导出、状态轮询、下载和 Electron 保存对话框。
- 验收：处理中可见；失败可重试；取消保存不误报成功；文件可由常见 Excel 软件打开。

#### WEEK-01 周范围与可用性

- 交付物：Asia/Shanghai 周计算、availability API。
- 验收：只接受周一；正确返回 archived 与未归档日期；覆盖跨年、闰日、夏令时无关性。

#### WEEK-02 周报生成

- 交付物：空周、结构化内容、来源快照/关系和同周唯一性。
- 验收：仅 archived 为来源；空周可生成；重复生成返回 40903 和已有 ID；日报不被修改。

#### WEEK-03 编辑与重生成

- 交付物：PUT 乐观锁、regenerate 显式确认、来源替换。
- 验收：未确认不覆盖；确认后两份内容和来源在同一事务更新；旧 version 不覆盖。

#### FE-WEEK-01/02 周报 UI

- 交付物：列表/周选择/缺失提示、详情编辑、来源跳转和覆盖警告。
- 验收：空周文案明确；人工编辑失败不丢；重新生成必须醒目确认；来源可追溯。

### M6：集成、安全与发布

#### INT-01 核心 E2E 与契约回归

- 流程：初始化 -> 登录 -> 模板 -> 日报保存/提交/归档 -> Excel -> 周报生成/编辑 -> 改密旧 Token 失效。
- 验收：Windows 开发环境稳定重复运行；API 字段/错误码契约无漂移；关键失败路径有用例。

#### SEC-01 安全专项审查

- 范围：`electron.vite.config.ts`、electron-builder 文件清单、main/preload/IPC、Vite 环境变量暴露、sidecar 绑定与资源路径、CORS、runtime secret、JWT、safeStorage、所有权、日志和文件路径。
- 验收：无未解决 P0/P1；越权矩阵和本机恶意请求测试通过。

#### PERF-01 性能与 SQLite 专项

- 范围：列表索引、并发唯一冲突、busy_timeout、导出内存/耗时和事务长度。
- 验收：个人常规数据量常用操作 2 秒内反馈；大导出不长时间持有事务；busy 转 50301。

#### PKG-01 打包

- 构建顺序：后端 `uv sync --frozen` 与测试 -> PyInstaller `onedir` -> 根 `npm ci`/质量检查 -> `npm run build` 生成 `electron/out` -> `electron-builder --win`。
- 交付物：`electron/out/{main,preload,renderer}`、PyInstaller `onedir`、Alembic 迁移和许可证 `extraResources`、`electron/electron-builder.yml`、Windows x64 安装包。
- 资源规则：sidecar/迁移放在 `process.resourcesPath` 下固定目录且不进入 ASAR；生产 `files` 排除 `src`、测试、`.env`、锁文件和源码配置，但保留 Electron 运行所需依赖。
- 验收：Node.js 22.12+ LTS 构建无 engine 警告；`electron-builder --dir` 解包检查资源位置正确；无 Python/Node/uv 的干净机可启动；数据只写 `userData`；许可证清单与 lock 文件一致。

#### PKG-02 升级与卸载验证

- 场景：electron-vite production build/preview、首次安装、上一版本升级、迁移备份、迁移失败、应用退出、sidecar 崩溃、卸载/重装。
- 验收：升级保留数据和历史快照；失败不带病运行；卸载不误删用户数据。

#### REL-01 发布评审

- 交付物：验收报告、已知问题、依赖/许可证清单、发布版本与回滚说明；同步更新全部 `ai-docs`。
- 门禁：所有 P0/P1 任务 DONE；安全/升级测试通过；无未批准架构偏差。

## 5. 建议并行批次

在不突破依赖的前提下可按以下批次分配 Agent：

| 批次 | 可并行任务 | 合并前同步点 |
|---|---|---|
| A | DESK-01、BE-01 | 工程目录和根命令确认 |
| B | FE-01、DESK-02、BE-02、DB-01（最多按可用人数） | 配置、启动契约、数据库 session 接口 |
| C | DESK-03、DB-02、TPL-01 | runtime secret、备份和模板领域边界 |
| D | API-01、AUTH-01 | bootstrap 事务与本地 API 安全契约 |
| E | AUTH-02 | 鉴权契约冻结 |
| F | USER-01、TPL-02、SET-01、FE-AUTH-01 | 认证后业务契约与前端会话 |
| G | BACKUP-01、FE-USER-01、FE-TPL-01、FE-SET-01、DAILY-01 | 字段/设置/用户接口稳定 |
| H | FE-BACKUP-01、DAILY-02、DAILY-04 | 日报详情响应冻结；随后 DAILY-03/前端日报 |
| I | EXPORT-01、WEEK-01、FE-DAILY-01 | 日报查询契约已稳定 |
| J | EXPORT-02、WEEK-02、FE-DAILY-02 | 文件和周报内容契约冻结 |
| K | FE-EXPORT-01、WEEK-03、FE-WEEK-01 | 重生成契约冻结 |
| L | FE-WEEK-02、GOV-01 | 全链路联调 |

同一批次不代表可忽略表内依赖。涉及共享文件（应用装配、ORM metadata、全局路由、根配置）的任务合并前必须由集成负责人协调。

## 6. 首批可领取任务

DESK-01 已按 electron-vite 实现，不重做。后续顺序：

1. 先完成 DESK-01 独立代码审查；通过后将 `IN_REVIEW` 改为 `DONE`。
2. 按中央状态完成 BE-01 及其审查。
3. DESK-01 通过后可启动 `FE-01`、`DESK-03`。
4. DESK-01 与 BE-01 均为 `DONE` 后启动 `DESK-02`。
5. `GOV-01`、`PKG-01` 按 Node.js 22.12+ 和 electron-vite `out/` 口径执行。

## 7. 风险与阻塞登记

| ID | 事项 | 当前决策/处理 | 状态 |
|---|---|---|---|
| R-01 | 首发跨平台范围 | V1 仅 Windows 10/11 x64 | Accepted default |
| R-02 | 周报重生成历史丢失 | 显式强提示后覆盖；V1 无版本恢复 | Accepted default |
| R-03 | 管理员数据权限 | 只能管理账号，不能读他人业务内容 | Accepted default |
| R-04 | SQLite 磁盘泄露 | V1 不整库加密；密码/Token 按安全方案保护 | Accepted default |
| R-05 | electron-vite/Electron/electron-builder 上游漂移 | Electron 与锁文件保持固定；根/electron engines 已收敛到 Node.js 22.12+，Reviewer 使用 Node 22.14.0/npm 10.9.2 执行 `npm ci` 无 EBADENGINE 且锁文件未变化 | Mitigated |
| R-06 | PyInstaller 体积/杀软误报 | PKG-01/02 做签名策略和干净机验证 | Open |
| R-07 | electron-vite HMR 导致 sidecar 重复启动 | DESK-02 生命周期管理必须幂等并覆盖热重载测试 | Open |
| R-08 | PyInstaller sidecar 被打入 ASAR 或路径错误 | PKG-01 使用 `extraResources`；DESK-02 只从 `process.resourcesPath` 解析 | Open |

## 8. 代码审查队列

| Task | Author | Reviewer | 状态 | P0/P1 | 结论/链接 |
|---|---|---|---|---|---|
| DESK-01 | 桌面平台工程师 Agent | 首席架构师/技术负责人 | APPROVED（验收通过） | 0/0 | 窄范围复审：导航实现通过 12 用例，但缺少持久化安全回归测试；镜像 P2 按用户指示未复核；2026-08-05 验收通过，转 DONE；`docs/electron/代码审查.md` |
| BE-01 | Python 后端基础设施工程师 Agent | 首席架构师/技术负责人 | APPROVED（复审通过，待提交） | 0/0 | `Approved`；历史 2 P2、1 P3 均已关闭；当前未关闭问题为 0；`docs/backend/代码审查.md` |

审查者不得与作者为同一 Agent。若团队工具限制无法满足，必须由首席架构师执行最终复审。

## 9. 独立任务说明索引

| Task | 文件 | 主责角色 | 当前状态 |
|---|---|---|---|
| DESK-01 | `ai-docs/tasks/DESK-01.md` | 桌面平台工程师 Agent | DONE |
| BE-01 | `ai-docs/tasks/BE-01.md` | Python 后端基础设施工程师 Agent | IN_REVIEW |
