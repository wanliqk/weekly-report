# 当前开发进度

> 快照日期：2026-08-05
> 当前分支：`v1`
> 原则：本文件只记录当前工作树可验证的实现事实；设计目标不等于完成。

## 1. 总体状态

- 当前已完成阶段：阶段 1 工程基线。
- 已完成提交：`3a9fdbc`（工程基线）。
- 当前应进入阶段：阶段 2 Desktop Bootstrap。
- 阶段 2 实现状态：尚未开始。
- 当前阻塞：无业务/技术决策阻塞；可按 `task.md` 从 `DESK-02`、`BE-02` 开始。
- AI 上下文治理批次：12 份 `ai-docs/` 文档、启动路由和维护规则已完成交叉复核，随独立文档阶段提交交付；未混入阶段 2 实现。

## 2. 已实现事实

### 工程与工具链

- 根目录是 npm workspace，当前 workspace 为 `electron`。
- 已存在根 `package-lock.json` 和后端 `uv.lock`。
- 根命令已提供开发、前端 lint、类型检查、测试、构建和 Windows 打包入口。
- Electron 使用 Electron 39、electron-vite 5、Vue 3、TypeScript、Vue Router、Pinia、Element Plus、Axios 和 Vitest。
- 后端使用 Python 3.12、FastAPI、Uvicorn、Pydantic Settings，并已声明 SQLAlchemy、Alembic、aiosqlite、Argon2、JWT 和 openpyxl 依赖。

### Electron/Vue 骨架

- Electron Main 已实现单实例锁、基础窗口生命周期和最小安全窗口配置。
- BrowserWindow 已启用 `contextIsolation` 和 sandbox，禁用 `nodeIntegration`。
- 新窗口默认拒绝，非当前页面导航被阻止。
- Preload 当前只暴露只读 `platform`，尚未暴露 API 基址、运行期密钥或 Token 能力。
- Renderer 已接入 Router、Pinia 和 Element Plus，仅有工程状态首页和一个 Vitest 工具函数测试。

### FastAPI 骨架

- 后端默认只允许配置为 `127.0.0.1`，端口允许使用 0，Uvicorn 固定单 worker。
- 已有基础 `/health`，当前返回统一成功外形和 `data.status=ok`。
- 已有请求 ID 中间件，可保留安全调用方 ID，非法 ID 会被替换。
- 已配置精确开发 CORS origin 和 Trusted Host 基线。
- 已有 3 个健康/请求 ID 测试。

### 已记录的阶段验证

工程基线交付记录显示以下命令已通过：

- `npm ci`，且根锁文件未变化。
- `npm run lint`。
- `npm run typecheck`。
- `npm test`（当时 1 项前端测试通过）。
- `npm run build`。
- `uv sync --directory backend --frozen`。
- `uv run --directory backend ruff check .`。
- `uv run --directory backend mypy`。
- `uv run --directory backend pytest`（3 项后端测试通过）。
- 生产 renderer 构建敏感信息扫描与 `git diff --check`。

用户另已确认当前工作树执行 `npm install` 和 `npm run dev` 成功。

## 3. 尚未实现

以下均为设计目标，当前不得标记为完成：

- Electron 启停 FastAPI sidecar、动态端口预留、随机 runtime secret、健康等待、失败页和退出清理。
- 开发/生产 sidecar 路径解析和 PyInstaller 产物。
- API 基址/运行期头的安全 preload bridge，以及 safeStorage Token 生命周期。
- 完整健康契约中的后端版本和 `Cache-Control: no-store`。
- SQLAlchemy Engine/Session、SQLite PRAGMA、ORM、Alembic 迁移、自动/手动备份。
- 统一异常、runtime secret 校验、JWT 鉴权和所有权隔离。
- 首次管理员、登录、用户管理、模板、设置、日报、导出和周报全部业务能力。
- Playwright E2E、sidecar 集成测试、PyInstaller 和 Windows 安装/升级验证。

## 4. 当前运行方式

根 `npm run dev` 当前使用 `concurrently` 独立启动：

- `uv run --directory backend python -m app`
- `npm run dev --workspace electron`

这只是开发期双进程编排，不是目标架构中的 Electron Main 托管 sidecar。当前页面也不会等待后端健康成功后再展示。

## 5. 下一检查点

阶段 2 完成时必须能证明：

1. Electron 每实例最多启动一个 sidecar，并使用 `127.0.0.1` 动态端口和每次启动随机密钥。
2. 完整 `/health` 成功后才进入业务窗口；启动失败有可操作且脱敏的错误界面。
3. 正常退出、异常退出、重载和重复实例不会遗留 sidecar。
4. renderer 只能通过最小 preload 契约在内存取得 API 基址和 runtime secret；密钥不得进入 Vite 变量、持久化存储或日志，也不得暴露内部数据路径或通用 IPC。
5. 阶段 2 质量门禁与审查通过，创建独立 Conventional Commit 后再进入阶段 3。
