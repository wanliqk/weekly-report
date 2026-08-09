# 系统架构基线

> 状态：V1 架构已实现；第二版方案已确认，BE-10A 数据/认证基线、BE-10B 日报聚合/管理员撤销/用户安全删除、BE-10C 周报/导出/统计适配均已实现
> 更新日期：2026-08-07
> 原始方案：`docs/方案设计.md`

## 0. 文档定位与事实边界

> **第二版事实边界**：第 1.1 节和 `progress.md` 仍描述当前 V1 实现快照（截至阶段 9）；第二版目标以本文第 13 节和 `docs/方案设计.md` 的 2026-08-07 增量为准，BE-10A/BE-10B/BE-10C 的真实落地事实见 `progress.md` 对应章节。FE-10/QA-10 仍是尚未实现的目标，不得视为完成。

- 本文件描述 V1 的目标架构、依赖方向和不可突破的安全边界，不以“已批准”表示代码已经完成。
- 产品范围以 `docs/需求理解.md` 为准，技术设计以 `docs/方案设计.md` 为准；本文件是供 Agent 快速恢复上下文的提炼版，不得反向覆盖上游文档。
- “当前已实现”只能依据当前 `v1` 工作树、`ai-docs/progress.md` 和已完成任务判断；禁止根据本文件中的目标描述宣称功能完成。
- 设计与实现不一致时，先记录到 `ai-docs/issues.md`，再修正文档或取得确认；不得通过其他分支或 Git 历史补全实现。

## 1. 架构目标

目标采用“Electron 桌面壳 + Vue 3 渲染进程 + FastAPI 本地 sidecar + SQLite”的单机多用户桌面架构。所有业务规则只存在于 FastAPI，Electron 只承载桌面能力，Vue 只通过 REST API 访问数据。

```text
目标运行形态：

Electron Main
├─ 单实例、窗口、userData、sidecar 生命周期、safeStorage、保存对话框
├─ Preload 白名单桥接
└─ Vue 3 Renderer
   └─ Axios -> 127.0.0.1:动态端口
                 │ Bearer JWT + X-Runtime-Secret
                 ▼
             FastAPI（单进程/单 worker）
             API -> Service -> Repository -> SQLAlchemy -> SQLite
                              ├─ Alembic/备份
                              └─ Excel 临时文件
```

### 1.1 当前实现快照（2026-08-06）

已完成阶段 1 工程基线（提交 `3a9fdbc`）、阶段 2 Desktop Bootstrap（提交 `7386cae`）、阶段 3 数据基础与 API Foundation（提交 `8480515`）、阶段 4 认证与用户管理（提交 `1a50e75`）、阶段 5 模板、设置与日报闭环（提交 `1d965fe`）、阶段 6 查询导出与桌面保存（提交 `d6ab86e`）、阶段 7 周报闭环（提交 `346b0ea`）、阶段 8 设置能力与受控备份（提交 `00caa33`）和阶段 9 质量与发布（独立审查完成）。V1 规划的全部 9 个阶段已交付；发布链路仍缺代码签名与正式多杀软兼容性矩阵测试（非阻塞，见 `issues.md` RISK-003）：

- 根目录已建立 npm workspace；`npm run dev` 现在只启动 electron-vite，Electron Main 在 `whenReady()` 中自行拉起并管理 FastAPI sidecar（开发模式直接 spawn `backend/.venv/Scripts/python.exe -m app`，不经过 `uv run`）。
- Electron 已实现单实例、窗口安全选项、禁止新窗口和跨地址导航；已有 `electron/src/main/sidecar/` 子进程管理模块（动态端口获取、runtime secret 生成、健康检查轮询、Windows 下 `taskkill /pid /t /f` 进程树终止）和 `electron/src/main/ipc/register-runtime-bridge.ts`（5 个受信任 frame 校验的 IPC channel，含阶段 6 新增的导出保存）。
- Preload 已有受限的 `window.runtimeBridge.{sidecar,api,token,exportFile}` 命名空间，未暴露通用 `ipcRenderer`；Token 由 Main 的 `safeStorage` 加密持久化，不可用时显式失败且无明文回退。文件保存对话框已在阶段 6 `DESK-04` 实现：`ExportFileSaver` 对文件名和字节内容双重校验后才调用系统级“另存为”，实际写入路径始终取自该对话框自身返回值，renderer 提供的名称只影响默认建议名。
- FastAPI 已建立应用工厂、精确 CORS/Trusted Host（含 `expose_headers=["Content-Disposition"]`）、请求 ID 中间件、`RuntimeSecretMiddleware`（除 `/health`/`/docs`/`/openapi.json` 外强制校验 `X-Runtime-Secret`）、达到目标契约的 `GET /health`（含 `version` 字段和 `Cache-Control: no-store`），以及统一异常处理基础（`AppError`/Pydantic 422 归一化/`OperationalError`→50301/兜底 500，均不泄露堆栈）。
- SQLAlchemy 异步 Engine/Session、SQLite PRAGMA、10 张业务表 ORM、V1 初始迁移与 BE-10A V2 迁移、迁移前备份均已实现。V2 已增加日期容器/管理员审计和强制改密字段，移除自动归档设置，并将旧日报与周报快照无损升级；日报多条目/撤销/日期归档、下游聚合和 Electron 页面仍按 10B～10D 分阶段实现。
- 手动整库备份（`BACKUP-01`）已实现：admin 触发 `PRAGMA wal_checkpoint(TRUNCATE)` + `sqlite3.Connection.backup()` 生成一致性快照，用进程内 `BackupRegistry`（不落业务表）以随机 ULID 映射文件路径/创建者/过期时间，15 分钟懒过期加启动残留清理，仅创建该备份的 admin 本人可下载。`/settings` 页面（`FE-07`）已实现自动归档开关、固定时区展示、企业微信占位（零外部请求）和管理员整库备份创建/保存交互，复用阶段 6 已审查的 Electron 保存对话框白名单模式（新增独立的 `.db` 文件名/大小校验器，不与导出共享白名单以避免互相放宽）。
- `build/sidecar/weekly-report-backend.exe` 已由真实 PyInstaller `onedir` 构建产出（42.69 MB/148 文件），在剥离 PATH（无 Python/uv）的隔离环境下验证可独立启动、通过 `/health`、正确建表。`electron-builder.yml` 的 `extraResources` 已把它放入打包产物的 `resources/sidecar/`（不进 ASAR）；生产模式下 Electron 会向 sidecar 子进程注入指向 `app.getPath('userData')` 的数据目录环境变量（阶段 9 新增，此前从未被验证过，见 `issues.md` ISS-014）。真实 NSIS 安装包已产出并在本机完成安装/升级/卸载验证（阶段 9 `PKG-02`/`REL-01`，未使用独立干净虚拟机，该限制已与用户确认），过程中另发现并修复两个真实打包缺陷（`issues.md` ISS-015 主进程模块打包遗漏、ISS-016 npm workspace 作用域包名导致安装产物异常）。Playwright E2E 套件（阶段 9 `QA-09`）已交付并纳入 `npm run test:e2e`，覆盖初始化→登录→模板→日报→导出→周报主链路及四条失败路径。

后续实现必须逐阶段把真实进度更新到 `progress.md`；本节只用于防止将目标架构误读为现状。

## 2. 固定技术栈

| 层 | 技术 |
|---|---|
| 桌面 | Electron 39、electron-vite 5、TypeScript |
| 前端 | Vue 3、TypeScript、Vite、Vue Router、Pinia、Element Plus、Axios；位于 `electron/src/renderer` |
| 后端 | Python 3.12、FastAPI、Uvicorn、Pydantic |
| 数据 | SQLAlchemy 2.x、aiosqlite、Alembic、SQLite WAL |
| 认证/导出 | JWT HS256、Argon2id、openpyxl |
| 工具 | Node.js 22.12+ LTS、npm 10+ 与根 `package-lock.json`；uv/`uv.lock`、Ruff、mypy、ESLint、Prettier |
| 测试 | pytest、httpx、Vitest、Playwright |
| 打包 | electron-vite build、PyInstaller `onedir`、electron-builder |

未经架构评审，不得更换数据库、后端框架、桌面框架、认证模型或引入第二套业务服务。

## 3. 分层与依赖规则

### 3.1 Electron

- Main：管理进程、路径、窗口和 OS 能力。
- Preload：通过 `contextBridge` 暴露最小白名单；禁止暴露通用 IPC、任意路径或命令执行。
- electron-vite 仅负责 main、preload、renderer 的开发与构建，不提供本项目业务服务层；Electron Main/Preload 不实现日报、周报、用户等业务规则，也不访问 SQLite。
- 桌面工程根固定为 `electron/`：`src/main`、`src/preload`、`src/renderer` 分别对应三个运行上下文，统一由 `electron/electron.vite.config.ts` 配置。

### 3.2 Frontend

- `views` 负责页面编排，`components` 负责可复用展示和输入。
- `stores` 只保存跨页面状态；列表筛选优先存 URL query。
- `api` 是 HTTP 唯一入口，页面不得直接使用 Axios。
- 服务端数据类型集中在 `types` 或契约生成目录，禁止页面自行复制接口结构。

### 3.3 Backend

固定依赖方向：`API -> Service -> Repository -> Model/DB`。

- API：协议转换、依赖注入、鉴权入口；不写 ORM、不承载状态机。
- Service：业务规则、事务边界、状态机和跨 Repository 协作。
- Repository：带所有者约束的数据读写；不做业务状态判断。
- Model/DB：映射、约束、连接和迁移，不依赖上层。

禁止反向依赖和跨层捷径；共享基础能力只能放入 `core`，且不得形成“万能工具类”。

## 4. 进程与数据生命周期

### 4.1 目标启动流程（尚未实现）

1. Electron 获取单实例锁和 `userData`。
2. 主进程选择可用回环端口，生成一次启动有效的随机 `runtime_secret`。
3. 以环境变量或参数向 sidecar 传入端口、数据目录、日志目录和运行期密钥。
4. FastAPI 设置 SQLite PRAGMA，执行迁移前备份和迁移，完成必要初始化。
5. 健康检查成功后才展示业务窗口；失败进入可诊断错误页。

### 4.2 目标退出流程（尚未实现）

1. 停止接受新业务请求。
2. 关闭数据库连接和后台导出资源。
3. 正常终止 sidecar；超时后由主进程终止子进程。
4. 不删除 `userData` 中的数据库、备份和日志。

### 4.3 目标运行期目录

| 用途 | 开发 | 生产 |
|---|---|---|
| 数据库 | `.local-data/weekly-report.db` | `userData/data/weekly-report.db` |
| 日志 | `.local-data/logs/` | `userData/logs/` |
| 导出临时文件 | `.local-data/temp/exports/` | `userData/temp/exports/` |
| 备份 | `.local-data/backups/` | `userData/backups/` |
| 手动备份临时文件 | `.local-data/temp/manual-backups/` | `userData/temp/manual-backups/` |

`.local-data/` 必须加入 `.gitignore`。安装目录视为只读，不得存放运行期数据。

## 5. 安全边界

以下均是实现必须满足的目标安全约束；当前已落地情况以 1.1 节和 `progress.md` 为准。

- FastAPI 只绑定 `127.0.0.1`，端口动态分配，Uvicorn 固定一个 worker。
- 所有业务 API 同时校验 Bearer JWT 和 `X-Runtime-Secret`；后者不能替代用户认证。
- `runtime_secret` 由 Main 每次启动随机生成，经最小 preload 契约交给 renderer 的 API 客户端并仅在内存使用；不得进入任何 Vite 构建变量、持久化存储或日志。
- `contextIsolation=true`、`nodeIntegration=false`、`sandbox=true`。
- 生产只加载应用自有资源，使用严格 CSP；CORS 使用精确白名单，禁止 `*`。
- JWT 由主进程 `safeStorage` 加密持久化，renderer 只保留运行期值，不写 `localStorage`。
- 外部链接只允许校验后的 HTTPS 域名，并交由系统浏览器打开。
- 所有 Repository 查询携带 `current_user.id`；默认对越权资源返回 404。
- 日志、异常和导出任务记录不得包含密码、Token、运行期密钥或完整正文。

## 6. 一致性与并发

- 数据库唯一约束是同日报/周报重复创建的最终防线。
- 日报和周报更新携带 `version`，使用条件更新实现乐观锁；冲突返回 40904。
- 状态转换、自动归档、周报生成/重生成和模板发布由 Service 在单事务内完成。
- Excel 在短事务内取得数据快照，在事务外写文件，避免长时间占用 SQLite 写锁。
- SQLite 设置 `WAL`、`foreign_keys=ON`、`busy_timeout=5000`、`synchronous=NORMAL`。
- 捕获数据库繁忙并返回 50301，不做可能重复写入的隐式重试。

## 7. 可观测性与恢复

- API 入口生成或接收请求 ID，响应回传 `X-Request-Id`，日志用其关联。
- 日志按天轮转并限制保留天数，记录模块、耗时和脱敏错误类型。
- 每次迁移前 checkpoint 并创建时间戳备份；默认保留最近 10 份。
- 手动整库备份仅 admin 可创建；后端生成短期文件并经 API 下载，Electron 只负责保存到用户选择位置。界面必须明确备份含全体用户业务数据。
- 删除过期备份或临时文件前必须解析绝对路径并验证仍位于目标目录。
- 迁移失败立即停止启动，不得跳过迁移继续运行。

## 8. 发布架构

以下发布流程已在阶段 9（`PKG-01`/`PKG-02`/`REL-01`）全部落地并经真实构建/安装验证，不再是目标占位。

- 开发模式下 Electron Main 直接 spawn `backend/.venv/Scripts/python.exe -m app`（不经过 `uv run`，避免其包装进程在 Windows 下导致 Node 持有错误 pid、清理不掉真正的解释器进程）；生产后端用 PyInstaller `onedir` 打包为 sidecar（`backend/weekly-report-backend.spec`，已产出真实 `build/sidecar/weekly-report-backend.exe`，42.69 MB/148 文件）。
- 生产包不依赖目标机器已有 Python、uv、Node.js 或全局环境变量；已在剥离 PATH（仅 `System32`/`Windows`）的隔离环境下真实验证独立启动成功。
- 根 npm workspace 通过 `npm ci` 安装；`npm run build` 调用 electron-vite，将 main、preload、renderer 统一输出到 `electron/out/`。main 进程构建对 `@electron-toolkit/utils` 显式排除外部化（强制打包，见 `issues.md` ISS-015）——npm workspace 依赖提升会导致 electron-builder 的默认依赖收集间歇性遗漏该模块，造成打包后主进程随机启动失败。
- `electron-builder` 使用 `electron/electron-builder.yml` 打包 `electron/out/`；PyInstaller sidecar、Alembic 迁移和许可证通过 `extraResources` 放入 `process.resourcesPath` 下的固定子目录，已用 `npm run build:unpack`/`npm run build:win` 真实验证 `resources/sidecar/` 内容正确。
- PyInstaller 可执行文件及其 `onedir` 依赖不放入 ASAR；生产启动只从 `process.resourcesPath` 解析（已用 `win-unpacked` 真实构建验证 `app.isPackaged=true`/`is.dev=false` 分支）。
- **命名约定**：生产 sidecar 可执行文件命名为 `weekly-report-backend.exe`，放在 `process.resourcesPath/sidecar/weekly-report-backend.exe`（对应 `electron-builder.yml` 的 `extraResources: {from: ../build/sidecar, to: sidecar}`）。该常量定义在 `electron/src/main/sidecar/constants.ts` 的 `PROD_SIDECAR_EXECUTABLE_NAME`；`electron/src/main/sidecar/paths.ts` 已实现该路径解析、"文件不存在则返回类型化失败"逻辑，以及生产分支向 `userData` 注入数据目录环境变量（`issues.md` ISS-014），均已被真实生产二进制触发验证。
- `electron/package.json` 的 `name` 字段不得使用 npm scope 前缀（`@scope/name`）——electron-builder 在本项目的 NSIS 配置（`oneClick: true`、`perMachine: false`）下会用该字段（而非 `productFilename`）拼装默认安装目录名，且不处理 scope 前缀，会产出畸形目录名和完全无效的空安装（`issues.md` ISS-016）；`nsis.artifactName` 同理必须用 `${productFilename}` 而非 `${name}`。
- 每次发布已在本机验证干净安装、首次初始化、从上一版升级（同版本号重装模拟）数据保留和卸载不误删用户数据；未在独立干净虚拟机上复测，该限制已与用户确认（`issues.md` ISS-017）。

## 9. 架构决策记录

| ADR | 决策 | 状态 | 约束理由 |
|---|---|---|---|
| ADR-001 | Electron 与 FastAPI 使用回环 REST | Accepted | 边界清晰、便于独立测试和未来迁移 Web |
| ADR-002 | Node 不承载业务，FastAPI 是唯一业务入口 | Accepted | 避免双业务栈与双写 SQLite |
| ADR-003 | SQLite 单实例、单 worker | Accepted | 符合本地部署和 SQLite 写模型 |
| ADR-004 | 不可变模板版本 + 日报 JSON 快照 | Accepted | 确保历史展示稳定并可追溯 |
| ADR-005 | 业务动态内容使用结构化 JSON | Accepted | 字段常变且无复杂字段值查询需求 |
| ADR-006 | HTTP 状态 + `{code,msg,data}` | Accepted | 保留协议语义和稳定业务错误 |
| ADR-007 | 24h JWT + `token_version` | Accepted | 支持密码变更/禁用后立即失效 |
| ADR-008 | 周报确认后覆盖重生成 | Accepted for V1 | 控制实现复杂度且避免静默丢数据 |
| ADR-009 | 导出任务记录 + 二进制下载 | Accepted | 支持状态反馈和临时文件治理 |
| ADR-010 | V1 主键统一使用 ULID 文本 | Accepted | 兼顾前端可用性、全局生成与大致时间有序；避免两种 ID 混用 |
| ADR-011 | 手动整库备份仅 admin，通过短期下载文件交付 | Accepted | 备份包含所有用户数据，需限制权限且不向 renderer 暴露内部路径 |
| ADR-012 | electron-vite 5 替换 electron-egg，作为 Electron 唯一开发/构建工具 | Accepted | 与现有 `electron/src/main|preload|renderer` 结构一致，减少框架层并保留 Vite/TypeScript 工具链 |
| ADR-013 | Node.js 22.12+ LTS、npm 10+ 作为开发/CI/发布基线 | Accepted | 满足 electron-vite 5 与当前 Electron 构建依赖的兼容区间，避免 Node 20 工具链警告 |

## 10. electron-vite 工程约束

- 项目实际桌面根为 `electron/`；不得再创建独立根 `frontend/` 或 electron-egg controller/service 目录。
- `electron/electron.vite.config.ts` 是 main/preload/renderer 的唯一 electron-vite 配置入口；默认构建输出保持 `electron/out/{main,preload,renderer}`。
- electron-vite 默认按 `MAIN_VITE_`、`PRELOAD_VITE_`、`RENDERER_VITE_` 区分环境变量。运行期密钥、JWT 和用户数据不得进入任何 Vite 构建变量；尤其禁止使用会跨上下文暴露的通用 `VITE_` 前缀保存敏感值。
- renderer 依赖由 Vite 打包；main/preload 的运行时依赖需结合 electron-vite externalization 与 electron-builder 文件收集规则审查。禁止依赖“开发环境 node_modules 恰好存在”的幻影依赖。
- preload 继续保持 sandbox。需要第三方依赖时应避免引入，或明确配置为可在 sandbox 下完整打包；不得通过 `sandbox=false` 规避构建问题。
- electron-vite 的 HMR/主进程热重载可能重复触发启动逻辑。DESK-02 必须确保每个 Electron 实例最多一个 sidecar，并在重载/退出路径可靠清理。

## 11. 官方参考

- electron-vite 仓库：<https://github.com/alex8088/electron-vite>
- electron-vite 文档：<https://electron-vite.org/>
- 工程结构与 preload：<https://electron-vite.org/guide/dev>
- 生产构建：<https://electron-vite.org/guide/build>
- 分发与 ASAR：<https://electron-vite.org/guide/distribution>

## 12. 架构变更门禁

以下修改属于核心架构变更，Agent 不得直接提交：技术栈替换、层级依赖变化、表拆并、主键策略变化、鉴权/所有权变化、状态机变化、周报来源或重生成语义变化、数据目录或 sidecar 生命周期变化。

变更流程：在对应 `ai-docs` 文件记录动机、备选方案、兼容性和迁移影响 -> 技术负责人批准 -> 更新任务和验收标准 -> 才能改代码。

每个技术方案阶段完成并通过适用质量门禁后，必须复核工作树并创建独立的 Conventional Commit；不得混入下一阶段，也不得在未获用户明确授权时推送远端。

## 13. 第二版目标架构（CR-20260807-01）

> **实现状态**：13.1～13.4 的后端目标已全部随 `BE-10A`/`BE-10B`/`BE-10C` 落地。Electron/Vue 界面适配是 `FE-10` 的未完成目标。

### 13.1 领域拆分

- `daily_reports` 变为同日可多篇的来源条目；保留 `draft/submitted/archived` 以兼容追溯，但不再提供单篇归档入口。**已实现**：`POST /daily-reports/{id}/archive` 已随 `BE-10B` 移除。
- 新增 `daily_report_days`，以 `(user_id, work_date)` 唯一表示日期容器和不可变正式日报；`open/archived` 是日期关闭状态。**已实现**（`BE-10A` 建表，`BE-10B` 落地归档事务）。
- 日期行是创建、保存、删除、提交、admin 撤销和日期级归档的共同写入互斥点。SQLite 下通过短事务中的条件 `UPDATE` 取得写锁并复查状态。**已实现**：`DailyReportDayRepository.touch_open_for_write`/`insert_entry_if_day_open`，已用真实并发测试验证创建与归档互斥、双管理员并发互删末位保护。
- 新增 `admin_audit_events` 记录撤销提交和用户删除；只存白名单元数据和原因，禁止正文/模板快照。**已实现**（`BE-10A` 建表，`BE-10B` 落地两类写入事务）。
- 周报、导出和完成日期统计只读取 `daily_report_days.status=archived` 的正式快照；来源条目不重复参与正式结果。**已实现**（`BE-10C`）：`WeeklyReportService`/`ExportService`/`StatisticsService` 均改读 `daily_report_days`，不再查询条目级 `daily_reports.status='archived'`。

### 13.2 服务和依赖

```text
API
├─ DailyReportService          # 条目创建幂等、保存、删除、提交（已实现）
├─ DailyReportDayService       # 月历、日期详情、正式归档事务（已实现）
├─ AdminDailyReportService     # 最小元数据、撤销与审计（已实现）
├─ StatisticsService          # 当前用户月份聚合和连续天数（已实现，BE-10C）
├─ WeeklyReportService         # 读取日期级正式快照（已实现，BE-10C）
└─ ExportService               # 一日期一正式记录（已实现，BE-10C）
        ↓
Repository -> Model/SQLite
```

模块仍严格遵循 API -> Service -> Repository -> Model/DB。管理员跨所有者的撤销是专用 Service/Repository 的窄权限例外，普通 Daily Repository 继续强制 owner 过滤；管理员查询 SQL 不选择正文列（`AdminSubmittedEntry` dataclass 由原始列选择构造，已通过独立安全审查确认）。

### 13.3 认证与安全

- 首次 bootstrap 在同一事务创建普通用户和固定 `admin`；密码分别 Argon2id 哈希。
- `users.must_change_password` 强制默认 admin 和被重置密码的用户先改密。认证基础依赖允许 `/auth/me`、改密和退出；业务依赖返回 `40303`。
- admin 仍默认不能查看他人正文。本次只开放待归档条目的必要元数据、撤销动作和脱敏审计。
- Electron Main/preload、回环 REST、runtime secret、safeStorage、CSP、单 sidecar/单 worker边界均不改变，也不新增 AI/外部网络能力。

### 13.4 一致性和迁移

- 日期级归档在一个事务内复查无草稿、构造版本化快照、批量归档来源并关闭日期；重复/并发请求最多得到一个正式日报。
- 创建使用 renderer 生成的 `client_request_id` 区分真实多次创建与同一请求重试。
- V1 每条日报迁移为一个同 ID 日期容器和一个来源条目；旧 archived 构造单来源正式快照，旧 draft/submitted 保持开放。
- `weekly_report_sources` 外键改指日期容器，历史 ID 保持不变；周报 JSON 逐行升级。无法无损降级时拒绝 downgrade，以升级前自动备份恢复。

### 13.5 第二版 ADR

| ADR | 决策 | 状态 | 约束理由 |
|---|---|---|---|
| ADR-014 | 日期容器 1:n 日报来源条目 | Accepted for V2（`BE-10B`） | 表达同日多篇、日期关闭、唯一正式结果和来源追溯 |
| ADR-015 | 日期行保存版本化不可变正式快照 | Accepted for V2（`BE-10B`） | 周报/导出稳定且不依赖模板后续变化（周报/导出改读仍是 `BE-10C`） |
| ADR-016 | 日期行作为该日全部写操作的并发互斥点 | Accepted for V2（`BE-10B`） | SQLite 下确定地协调创建、撤销与归档；已用并发测试验证 |
| ADR-017 | admin 撤销使用专用最小元数据查询和独立审计 | Accepted for V2（`BE-10B`） | 满足操作能力而不扩大正文权限；已通过独立安全审查 |
| ADR-018 | 有业务账号不物理删除，只允许停用 | Accepted for V2（`BE-10B`） | 避免级联数据损失并保持外键追溯 |
| ADR-019 | 周报、导出和完成统计只读取日期级正式日报 | Proposed for V2 | 每个完成日期只参与一次，消除重复汇总；待 `BE-10C` 实现 |

## 14. 企业微信同步目标架构（CR-20260808-02）

> 实现状态：数据层、Electron 凭证桥、协议 Client、字段 Mapper、连接/同步编排 Service 与公开/Main-only API（`WECOM-02..06`）均已实现并通过独立审查；Renderer（`WECOM-07`）仍是目标设计。当前 `wecom_sync=false` 和占位 UI 不变，具体事实以 `progress.md`/`task.md` 为准。

```text
Renderer --公开 REST--> WeCom API/Service --> Repository/SQLite
   │                              │
   └--窄 IPC--> Electron Main     └--> integrations/wecom Client
                   │                          ▲
                   ├─安全登录窗口             │ 单次内存 Cookie jar
                   └─safeStorage 凭证----------┘
```

### 14.1 分层

- Electron Main：`WeComAuthWindowController`、`WeComCredentialStore`、`WeComBridgeClient`；只负责登录、系统加密和凭证桥，不承载同步状态机。
- FastAPI：`WeComConnectionService`、`WeComDailyMapper`、`WeComSyncService`；所有写操作继续遵循 API -> Service -> Repository -> Model/DB。
- 出站适配：`backend/app/integrations/wecom` 集中实现模板组合、日报列表和 multipart 提交三个内部接口。
- Renderer：公开 REST 负责业务数据，`runtimeBridge.wecom` 只暴露连接、断开和按 `record_id` 执行，不能读取 Cookie 或发送任意 URL。

### 14.2 凭证与内部鉴权

- Cookie jar 以完整结构保存到 Electron `safeStorage` 加密文件；SQLite 只存随机 `credential_slot`。
- 新增每次启动随机的 `main_bridge_secret`，只存在 Electron Main 和 sidecar 内存。携带 Cookie 的 `/api/v1/internal/wecom/**` 同时校验 Main-only secret 与用户 JWT。
- 现有 runtime secret 对 renderer 可见，因此不得复用为 Cookie 端点的唯一保护。
- 企业微信外部调用在 SQLite 事务外执行；状态预留和最终落库分别使用短事务与 `attempt_token` 条件写。

### 14.3 同步状态

`pending -> syncing -> succeeded/failed/auth_required/schema_changed/duplicate_detected/uncertain`。只有能证明远端未受理的 `failed` 可人工重试；超时、崩溃或提交响应契约异常进入 `uncertain`，必须先远端对账。

### 14.4 新增 ADR

| ADR | 决策 | 状态 | 理由 |
|---|---|---|---|
| ADR-020 | 生产登录使用 Electron 隔离 BrowserWindow，不打包 Python Playwright | Accepted for design | 复用现有 Chromium 和生命周期，同时保留人工验证 |
| ADR-021 | Cookie 用 `safeStorage`，业务库只存凭证槽位 | Accepted for design | 数据库备份不应携带可用会话 |
| ADR-022 | 新增 Main-only secret，凭证执行端点同时校验 JWT | Accepted for design | runtime secret 已进入 renderer，不能保护 Cookie |
| ADR-023 | FastAPI 出站 Client + Electron 凭证桥 | Accepted for design | 业务幂等/状态集中在 Service，Main 不承载业务状态机 |
| ADR-024 | 日期正式日报 + 目标指纹为同步幂等键 | Accepted for design | 同目标不重复，不同目标可显式同步 |
| ADR-025 | 可能已受理的失败统一进入 `uncertain` | Accepted for design | 防止自动重试制造重复日报 |
