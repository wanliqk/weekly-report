# 系统架构基线

> 状态：已批准（V1，桌面工具链变更已纳入）  
> 更新日期：2026-08-04  
> 原始方案：`docs/方案设计.md`

## 1. 架构目标

采用“Electron 桌面壳 + Vue 3 渲染进程 + FastAPI 本地 sidecar + SQLite”的单机多用户桌面架构。所有业务规则只存在于 FastAPI，Electron 只承载桌面能力，Vue 只通过 REST API 访问数据。

```text
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

### 4.1 启动

1. Electron 获取单实例锁和 `userData`。
2. 主进程选择可用回环端口，生成一次启动有效的随机 `runtime_secret`。
3. 以环境变量或参数向 sidecar 传入端口、数据目录、日志目录和运行期密钥。
4. FastAPI 设置 SQLite PRAGMA，执行迁移前备份和迁移，完成必要初始化。
5. 健康检查成功后才展示业务窗口；失败进入可诊断错误页。

### 4.2 退出

1. 停止接受新业务请求。
2. 关闭数据库连接和后台导出资源。
3. 正常终止 sidecar；超时后由主进程终止子进程。
4. 不删除 `userData` 中的数据库、备份和日志。

### 4.3 目录

| 用途 | 开发 | 生产 |
|---|---|---|
| 数据库 | `.local-data/weekly-report.db` | `userData/data/weekly-report.db` |
| 日志 | `.local-data/logs/` | `userData/logs/` |
| 导出临时文件 | `.local-data/temp/exports/` | `userData/temp/exports/` |
| 备份 | `.local-data/backups/` | `userData/backups/` |
| 手动备份临时文件 | `.local-data/temp/manual-backups/` | `userData/temp/manual-backups/` |

`.local-data/` 必须加入 `.gitignore`。安装目录视为只读，不得存放运行期数据。

## 5. 安全边界

- FastAPI 只绑定 `127.0.0.1`，端口动态分配，Uvicorn 固定一个 worker。
- 所有业务 API 同时校验 Bearer JWT 和 `X-Runtime-Secret`；后者不能替代用户认证。
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

- 开发后端由 `uv run` 启动；生产后端用 PyInstaller `onedir` 打包为 sidecar。
- 生产包不得依赖目标机器已有 Python、uv、Node.js 或全局环境变量。
- 根 npm workspace 通过 `npm ci` 安装；`npm run build` 调用 electron-vite，将 main、preload、renderer 统一输出到 `electron/out/`。
- `electron-builder` 使用 `electron/electron-builder.yml` 打包 `electron/out/`；PyInstaller sidecar、Alembic 迁移和许可证通过 `extraResources` 放入 `process.resourcesPath` 下的固定子目录。
- PyInstaller 可执行文件及其 `onedir` 依赖不得放入 ASAR；生产启动只能从 `process.resourcesPath` 解析，不得依赖源码目录、`cwd` 或开发机绝对路径。
- 每次发布必须验证干净机安装、首次初始化、从上一版升级、数据保留和卸载不误删用户数据。

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
