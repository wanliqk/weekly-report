# 当前开发进度

> 快照日期：2026-08-05
> 当前分支：`v1`
> 原则：本文件只记录当前工作树可验证的实现事实；设计目标不等于完成。

## 1. 总体状态

- 当前已完成阶段：阶段 1 工程基线、阶段 2 Desktop Bootstrap（代码与测试已完成，待创建阶段提交）。
- 已完成提交：`3a9fdbc`（工程基线）。
- 当前应进入阶段：阶段 3 数据基础与 API Foundation（阶段 2 提交后）。
- 阶段 2 实现状态：`DESK-02`、`BE-02`、`DESK-03`、`QA-02` 均已实现并通过质量门禁，尚未创建阶段提交。
- 当前阻塞：无业务/技术决策阻塞。
- AI 上下文治理批次：12 份 `ai-docs/` 文档、启动路由和维护规则已完成交叉复核，随独立文档阶段提交交付；未混入阶段 2 实现。

## 2. 已实现事实

### 工程与工具链

- 根目录是 npm workspace，当前 workspace 为 `electron`。
- 已存在根 `package-lock.json` 和后端 `uv.lock`。
- 根命令已提供开发、前端 lint、类型检查、测试、构建和 Windows 打包入口。
- Electron 使用 Electron 39、electron-vite 5、Vue 3、TypeScript、Vue Router、Pinia、Element Plus、Axios 和 Vitest。
- 后端使用 Python 3.12、FastAPI、Uvicorn、Pydantic Settings，并已声明 SQLAlchemy、Alembic、aiosqlite、Argon2、JWT 和 openpyxl 依赖（业务层尚未使用）。
- 根 `npm run dev` 已改为只调用 `npm run dev --workspace electron`；`concurrently` 依赖已移除。`dev:backend`（`uv run --directory backend python -m app`）保留作为独立手动调试入口。

### Electron/Vue sidecar 生命周期（阶段 2 新增）

- 新增 `electron/src/main/sidecar/` 模块群：`manager.ts`（状态机 `idle/starting/ready/failed/stopping/stopped`，对外映射为 `pending/ready/failed`）、`paths.ts`（开发/生产路径解析，不依赖 electron 全局，纯函数可测）、`secret.ts`（`crypto.randomBytes(32)` 生成 64 位十六进制 runtime secret）、`health-check.ts`（轮询 `/health`）、`process-kill.ts`（Windows 下统一走 `taskkill /pid <pid> /t /f` 终止整棵进程树）、`log-buffer.ts`（有界环形缓冲区 + 密钥脱敏）、`create-runtime-deps.ts`（组装真实依赖，仍不直接依赖 electron）。
- `electron/src/main/index.ts` 已接入：`whenReady()` 中注册 IPC bridge 并启动 sidecar；`before-quit`、`SIGINT`/`SIGTERM`、`uncaughtException`、`process.on('exit')` 均已挂接清理逻辑。
- 开发模式直接 spawn `backend/.venv/Scripts/python.exe -m app`（不经过 `uv run`），生产模式解析 `process.resourcesPath/sidecar/weekly-report-backend.exe`（该可执行文件本身由后续 `PKG-01` 产出，当前找不到时按类型化失败处理，不会崩溃）。
- 端口获取机制：后端自己 `bind(port=0)` 后向 stdout 打印一行 JSON（`{"event":"sidecar_ready","port":<port>}`），Main 解析该行获得真实端口，不做“预探测端口再传参”的竞态方案。
- runtime secret 只通过子进程环境变量 `WEEKLY_REPORT_RUNTIME_SECRET` 传递，仅在 Main 内存持有；已验证生产构建产物 `electron/out/renderer`、`electron/out/preload` 中不出现该常量名或任何密钥值。
- IPC：`electron/src/main/ipc/register-runtime-bridge.ts` 提供 4 个受信任 frame 校验的 channel（获取状态快照、状态变化推送、重试、获取 API 配置）。
- Preload（`electron/src/preload/index.ts`）新增 `window.runtimeBridge.{sidecar,api}` 命名空间方法，未暴露通用 `ipcRenderer`；原有 `window.desktop.platform` 保持不变。
- Renderer 新增 Pinia store（`stores/sidecar.ts`）、`StartupView.vue`（pending/failed 态展示，failed 态可重试并显示脱敏日志）、`api/client.ts`（等待 runtime config 就绪后创建 axios 实例，供后续业务任务使用）；`App.vue` 在 sidecar 未就绪时渲染 `StartupView` 而非业务路由。

### FastAPI 健康契约与 runtime secret 校验（阶段 2 新增）

- `backend/app/__main__.py` 改为手动构造 `uvicorn.Config` + 自定义 `Server` 子类，绑定成功后打印上述结构化端口行；不再依赖 `app.main` 模块级单例（该单例已移除，避免仅仅 import 模块就因缺少配置而报错）。
- `Settings` 新增 `runtime_secret: str | None`（非 `test` 环境必须 ≥32 字符，否则启动时报错）与 `log_dir: Path`；`data_dir`/`log_dir` 经 `field_validator` 解析为绝对路径。
- 新增 `backend/app/core/paths.py::ensure_runtime_directories()`，只在 `__main__.main()` 真正启动前调用，不放进 Settings 校验器。
- 新增 `RuntimeSecretMiddleware`（`backend/app/core/middleware.py`）：`secrets.compare_digest` 恒定时间比较；豁免路径为 `/health`、`/docs`、`/openapi.json`；中间件注册顺序为 `TrustedHost → RuntimeSecret → CORS → RequestId`，确保 CORS 预检 OPTIONS 请求不被拦截。
- `/health` 契约已达目标：`{"code":0,"msg":"success","data":{"status":"ok","version":"0.1.0"}}`，响应头含 `Cache-Control: no-store`，且是唯一豁免 `X-Runtime-Secret` 的端点。
- 新增错误码 `40103`（运行期密钥缺失或无效，HTTP 401）。

### 已记录的阶段验证

工程基线（阶段 1）交付记录（历史）：`npm ci`、`npm run lint`、`npm run typecheck`、`npm test`（1 项前端测试）、`npm run build`、`uv sync --frozen`、`uv run ruff/mypy/pytest`（3 项后端测试）均已通过；生产 renderer 构建敏感信息扫描与 `git diff --check` 已执行。

阶段 2 本次交付实际执行并通过：

- `npm ci`（636 个包，全新安装成功）。
- `npm run lint`（根 + electron，0 error 0 warning）。
- `npm run typecheck`（`tsc` + `vue-tsc`，0 错误）。
- `npm test`（Vitest，9 个测试文件、36 项测试全部通过，覆盖 sidecar 状态机、路径解析、日志脱敏、密钥生成、健康检查轮询、Windows 进程树终止、IPC 受信任 frame 校验、Pinia store）。
- `npm run build`（electron-vite production build 成功）。
- `npm run test:integration --workspace electron`（真实拉起 `backend/.venv` Python 解释器，验证动态端口分配、真实 `/health` 通过、`stop()` 后进程树完全消失、两次连续启动端口不同；2 项测试通过）。
- `uv sync --directory backend --frozen`、`uv run ruff check .`、`uv run mypy`（strict，20 个源文件）、`uv run pytest -q`（17 项测试，含新增的 runtime secret 中间件测试、Settings 校验测试、真实子进程端口上报测试）均通过。
- `git diff --check`：无空白/冲突标记问题。
- 手动冒烟（`npm run dev` 真实运行）：Electron 拉起唯一 `backend/.venv/Scripts/python.exe` 子进程（已确认该子进程本身还会派生一个真正执行 uvicorn 的孙进程，见下方“阶段 2 发现的问题”）；用外部 `curl` 访问 sidecar 自报的动态端口 `/health` 成功；用 `CloseMainWindow()` 模拟正常关闭窗口后，`tasklist`/`Get-Process` 确认 electron 与全部 python 进程（含孙进程）均已清理，无孤儿进程；构建产物 `electron/out/renderer`、`electron/out/preload` 中未出现 `RUNTIME_SECRET`/密钥相关字符串。

### 阶段 2 发现的问题（已修复，记录供审查参考）

- 手动冒烟测试发现：`backend/.venv/Scripts/python.exe`（uv 管理的虚拟环境）本身是一个启动器 shim，会再 fork 一个真正运行 uvicorn 的子进程（grandchild）。Windows 下 `ChildProcess.kill()` 只终止 Node 记录的那一个 pid，不会级联到孙进程，会导致“看起来已优雅退出，实际留下孤儿 uvicorn 进程”。已将 `process-kill.ts` 改为 Windows 下统一走 `taskkill /pid <pid> /t /f`（按进程树终止），不再尝试先 `kill()` 再按超时升级；已通过手动 `CloseMainWindow()` 测试和集成测试（`isPidAlive` 断言）验证修复有效。

## 3. 尚未实现

以下均为设计目标，当前不得标记为完成：

- 开发/生产 sidecar 路径解析中，生产分支的 PyInstaller `onedir` 产物本身（`PKG-01`，阶段 9）——当前只有路径解析和"文件不存在则走失败态"的逻辑，`build/sidecar/` 仍是空占位目录。
- safeStorage Token 生命周期（本阶段只搭了 preload 命名空间骨架，未接入具体 Token 存取）。
- SQLAlchemy Engine/Session、SQLite PRAGMA、ORM、Alembic 迁移、自动/手动备份。
- 统一异常响应转换（422 归一化）、JWT 鉴权和所有权隔离。
- 首次管理员、登录、用户管理、模板、设置、日报、导出和周报全部业务能力。
- Playwright E2E、PyInstaller 和 Windows 安装/升级验证。
- Windows Job Object 级别的孤儿进程彻底防护（当前 `taskkill /t /f` 覆盖正常退出/崩溃/重载/信号场景；Electron 被外部强杀时仍有残余风险，已记入 `issues.md`）。

## 4. 当前运行方式

根 `npm run dev` 现在只启动 `electron-vite dev`；Electron Main 在 `app.whenReady()` 中自行拉起并管理 FastAPI sidecar 子进程（开发模式直接 spawn `backend/.venv/Scripts/python.exe -m app`），不再需要 `concurrently` 双进程编排。`dev:backend` 脚本仍保留，供需要脱离 Electron 单独调试后端时使用（需自行在 `.env` 设置 `WEEKLY_REPORT_RUNTIME_SECRET`）。

页面启动流程：窗口创建后立即显示，`App.vue` 根据 sidecar 状态在 `StartupView`（pending/failed）与业务路由（ready）之间切换，不再是"不等待后端就直接展示业务首页"。

## 5. 下一检查点

阶段 2 已满足以下目标，待创建独立 Conventional Commit 后进入阶段 3：

1. ✅ Electron 每实例最多启动一个 sidecar，使用 `127.0.0.1` 动态端口和每次启动随机密钥。
2. ✅ 完整 `/health` 成功后才进入业务窗口；启动失败有可操作且脱敏的错误界面（`StartupView` 展示原因与重试按钮）。
3. ✅ 正常退出、异常退出（模拟）、重复实例（单实例锁沿用阶段 1 实现）不会遗留 sidecar；HMR 重载场景的防重复拉起已通过 `start()` 幂等性单元测试验证（本沙箱环境文件监听未能实测触发真实重载，已记录为环境限制）。
4. ✅ renderer 只能通过最小 preload 契约在内存取得 API 基址和 runtime secret；已扫描构建产物确认密钥不进入 Vite 变量、持久化存储或日志，也不暴露内部数据路径或通用 IPC。
5. ✅ 阶段 2 质量门禁通过；独立 Reviewer 审查与 Conventional Commit 待用户确认后执行。
