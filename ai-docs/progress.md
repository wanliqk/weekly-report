# 当前开发进度

> 快照日期：2026-08-05
> 当前分支：`v1`
> 原则：本文件只记录当前工作树可验证的实现事实；设计目标不等于完成。

## 1. 总体状态

- 当前已完成阶段：阶段 1 工程基线、阶段 2 Desktop Bootstrap、阶段 3 数据基础与 API Foundation（代码与测试已完成，待创建阶段提交）。
- 已完成提交：`3a9fdbc`（工程基线）、`7386cae`（Desktop Bootstrap）。
- 当前应进入阶段：阶段 4 认证与用户管理（阶段 3 提交后）。
- 阶段 3 实现状态：`DB-01`、`DB-02`、`DB-03`、`API-01`、`QA-03` 均已实现并通过质量门禁，尚未创建阶段提交。
- 当前阻塞：无业务/技术决策阻塞。
- AI 上下文治理批次：12 份 `ai-docs/` 文档、启动路由和维护规则已完成交叉复核，随独立文档阶段提交交付；未混入后续阶段实现。

## 2. 已实现事实

### 工程与工具链

- 根目录是 npm workspace，当前 workspace 为 `electron`。
- 已存在根 `package-lock.json` 和后端 `uv.lock`。
- 根命令已提供开发、前端 lint、类型检查、测试、构建和 Windows 打包入口。
- Electron 使用 Electron 39、electron-vite 5、Vue 3、TypeScript、Vue Router、Pinia、Element Plus、Axios 和 Vitest。
- 后端使用 Python 3.12、FastAPI、Uvicorn、Pydantic Settings、SQLAlchemy 2.x（异步）、Alembic、aiosqlite；Argon2、JWT、openpyxl 仍只是声明依赖，业务层尚未使用。
- 根 `npm run dev` 只调用 `npm run dev --workspace electron`；`concurrently` 依赖已移除。`dev:backend`（`uv run --directory backend python -m app`）保留作为独立手动调试入口。

### Electron/Vue sidecar 生命周期（阶段 2，已提交 `7386cae`）

- `electron/src/main/sidecar/` 模块群：`manager.ts`（状态机 `idle/starting/ready/failed/stopping/stopped`，对外映射为 `pending/ready/failed`）、`paths.ts`（开发/生产路径解析）、`secret.ts`（`crypto.randomBytes(32)` 生成 64 位十六进制 runtime secret）、`health-check.ts`（轮询 `/health`）、`process-kill.ts`（Windows 下统一走 `taskkill /pid <pid> /t /f` 终止整棵进程树）、`log-buffer.ts`（有界环形缓冲区 + 密钥脱敏）、`create-runtime-deps.ts`。
- `electron/src/main/index.ts`：`whenReady()` 中注册 IPC bridge 并启动 sidecar；`before-quit`、`SIGINT`/`SIGTERM`、`uncaughtException`、`process.on('exit')` 均已挂接清理逻辑。
- 开发模式直接 spawn `backend/.venv/Scripts/python.exe -m app`（不经过 `uv run`），生产模式解析 `process.resourcesPath/sidecar/weekly-report-backend.exe`（该可执行文件本身由后续 `PKG-01` 产出，当前找不到时按类型化失败处理）。
- 端口获取机制：后端自己 `bind(port=0)` 后向 stdout 打印一行 JSON（`{"event":"sidecar_ready","port":<port>}`），Main 解析该行获得真实端口。
- runtime secret 只通过子进程环境变量 `WEEKLY_REPORT_RUNTIME_SECRET` 传递，仅在 Main 内存持有；已验证生产构建产物中不出现该常量名或任何密钥值。
- IPC：`electron/src/main/ipc/register-runtime-bridge.ts` 提供 4 个受信任 frame 校验的 channel。Preload 新增 `window.runtimeBridge.{sidecar,api}` 命名空间方法，未暴露通用 `ipcRenderer`。
- Renderer 新增 Pinia store（`stores/sidecar.ts`）、`StartupView.vue`、`api/client.ts`；`App.vue` 在 sidecar 未就绪时渲染 `StartupView` 而非业务路由。
- 已知残余风险：Electron 被外部强杀时孤儿进程防护仍不完整（需 Windows Job Object），记入 `issues.md` ISS-010。

### FastAPI 健康契约与 runtime secret 校验（阶段 2，已提交）

- `backend/app/__main__.py` 手动构造 `uvicorn.Config` + 自定义 `Server` 子类，绑定成功后打印结构化端口行。
- `Settings` 含 `runtime_secret: str | None`（非 `test` 环境必须 ≥32 字符）、`log_dir`/`backup_dir: Path`（阶段 3 新增）；均经 `field_validator` 解析为绝对路径。
- `RuntimeSecretMiddleware`：`secrets.compare_digest` 恒定时间比较；豁免路径为 `/health`、`/docs`、`/openapi.json`；中间件顺序 `TrustedHost → RuntimeSecret → CORS → RequestId`。
- `/health` 契约已达目标：`{"code":0,"msg":"success","data":{"status":"ok","version":"0.1.0"}}`，响应头含 `Cache-Control: no-store`。
- 错误码 `40103`（运行期密钥缺失或无效，HTTP 401）。

### 数据持久化基础（阶段 3 新增，DB-01/DB-02/DB-03）

- `backend/app/db/engine.py::create_engine()`：`sqlite+aiosqlite` 异步引擎，`connect` 事件监听器在每个新连接上设置 `PRAGMA foreign_keys=ON`、`journal_mode=WAL`、`synchronous=NORMAL`、`busy_timeout=5000`；已用真实连接验证这四个 PRAGMA 的实际值。
- `backend/app/db/session.py`：`async_sessionmaker` 工厂 + FastAPI `get_db_session` 依赖（尚无路由消费，供后续业务任务直接使用）。
- `Settings.database_path` 属性 = `data_dir/weekly-report.db`，匹配 `architecture.md` §4.3 的开发期路径 `.local-data/weekly-report.db`。
- `backend/app/core/ulid.py`：纯 stdlib 实现的 ULID 生成（不引入第三方依赖），48 位毫秒时间戳 + 80 位随机数，26 位 Crockford Base32，按时间字典序单调。
- `backend/app/models/`：`database.md` 全部 8 张表（`users`、`user_settings`、`report_templates`、`template_versions`、`daily_reports`、`weekly_reports`、`weekly_report_sources`、`export_jobs`）已用 SQLAlchemy 2.0 `Mapped`/`mapped_column` 建模，字段类型、`NOT NULL`、`DEFAULT`、`CHECK`、唯一约束、索引（含 `DESC` 排序索引）、外键 `ondelete="RESTRICT"` 均按 `database.md` 逐项对照实现。
- `backend/alembic/`：async 模板 scaffold；`env.py` 的 `target_metadata = Base.metadata`，URL 由 `Settings`/`config.attributes` 动态提供（不依赖 `alembic.ini` 里的占位符）；初始迁移 `3f6f955b87bb_initial_schema.py` 通过 `--autogenerate` 生成后补齐了自动生成器无法识别的 4 个表达式索引（`DESC` 排序，SQLAlchemy/SQLite 已知限制），已验证"空库 `upgrade head`"成功且 `alembic_version` 落到唯一 head。
- `backend/app/db/migrate.py::run_startup_migrations()`：启动时比较当前 revision 与 head；一致则直接跳过（不产生备份、不重复执行）；数据库文件已存在但落后于 head 时，先执行 `PRAGMA wal_checkpoint(TRUNCATE)` 再用 `sqlite3.Connection.backup()` 做一致性快照到 `backup_dir/weekly-report-<UTC时间戳>.db`，成功后才调用 `alembic upgrade head`；只保留最新 10 份备份（`MAX_BACKUPS_TO_KEEP`），写入和轮转删除前都做路径边界校验（解析后必须落在 `backup_dir` 内）；备份或迁移失败时异常直接向上抛出，不吞错、不继续启动。已接入 `__main__.main()`，在 `ensure_runtime_directories()` 之后、创建 FastAPI app 之前执行。

### 统一异常与响应基础（阶段 3 新增，API-01）

- `backend/app/core/errors.py::AppError`：业务异常基类（`code`/`http_status`/`message`/`data`），供后续 Service 层子类化使用（本阶段未新增具体业务错误码，避免抢跑未定义契约）。
- `register_exception_handlers()` 已接入 `create_app()`，覆盖四类：
  - `RequestValidationError`（FastAPI/Pydantic 422）→ 统一转换为 `code=40001`、`HTTP 400`，`data.errors` 返回脱敏字段定位（不含 `body` 前缀）。
  - `AppError` → 使用异常自带的 `code`/`http_status`/`message`/`data`。
  - `sqlalchemy.exc.OperationalError` → `code=50301`、`HTTP 503`，不泄露驱动原始报错文本。
  - 兜底 `Exception` → `code=50001`、`HTTP 500`，`logger.exception` 记录（含 request id），响应体不含堆栈或异常消息。
- 已验证：注册这些处理器后 `TestClient` 默认的“重新抛出未处理异常”行为不会触发（异常在 Starlette `ExceptionMiddleware` 层被正确截获），且外层 `RequestIdMiddleware` 仍能给这些错误响应加上 `X-Request-Id`。

### 已记录的阶段验证

工程基线（阶段 1）交付记录（历史）：`npm ci`、lint、typecheck、`npm test`（1 项前端测试）、`npm run build`、`uv sync --frozen`、`uv run ruff/mypy/pytest`（3 项后端测试）均已通过。

阶段 2 Desktop Bootstrap（提交 `7386cae`）：`npm ci`（636 包）、lint（0 error/0 warning）、typecheck（0 错误）、`npm test`（9 文件 36 项）、`npm run build`、`npm run test:integration`（真实子进程，2 项）、后端 `ruff`/`mypy`（20 文件）/`pytest`（17 项）均通过；手动冒烟确认单一 sidecar 进程、健康检查真实通过、退出无孤儿进程；构建产物扫描确认无密钥泄露。过程中发现并修复了一个真实 bug：uv 管理的 venv `python.exe` 是启动器 shim，会再 fork 真正跑 uvicorn 的孙进程，`child.kill()` 无法级联终止，已改为 Windows 下统一 `taskkill /pid /t /f`。

阶段 3 数据基础与 API Foundation 本次交付实际执行并通过：

- `npm run lint`、`npm run typecheck`：前端未受影响（本阶段为后端专属，无 Electron/Vue 改动），复核通过。
- `uv sync --directory backend --frozen`：锁文件一致，未新增第三方依赖（ULID 用 stdlib 自实现）。
- `uv run --directory backend ruff check .`、`ruff format --check .`：0 error。
- `uv run --directory backend mypy`（strict，`files = ["app", "tests", "alembic"]`，共 40 个源文件）：0 错误。
- `uv run --directory backend pytest -q`：**45 项测试全部通过**（阶段 2 遗留 17 项 + 本阶段新增 28 项：ULID 3、DB engine/PRAGMA 4、统一异常处理器 4、Alembic 迁移 4、备份轮转与失败停止启动 8、ORM 约束/乐观锁/事务回滚 5）。
- 手动冒烟：`uv run --directory backend python -m app` 真实启动，观察到日志 `Running upgrade  -> 3f6f955b87bb, initial schema`，随后 `/health` 可访问；用 `sqlite3`/Python 直接检查 `.local-data/weekly-report.db`，确认 8 张业务表 + `alembic_version` 均已正确创建。
- `git status --short`：除预期新增/修改文件外无遗留改动。

## 3. 尚未实现

以下均为设计目标，当前不得标记为完成：

- 开发/生产 sidecar 路径解析中，生产分支的 PyInstaller `onedir` 产物本身（`PKG-01`，阶段 9）——`build/sidecar/` 仍是空占位目录。
- safeStorage Token 生命周期（阶段 2 只搭了 preload 命名空间骨架，未接入具体 Token 存取）。
- Repository、Service 层完全未实现（`app/repositories/`、`app/services/` 仍是空壳）；本阶段的"所有权过滤""乐观锁"只在 ORM/SQL 层面验证了模式可行，尚未有业务代码强制执行。
- JWT 鉴权、Argon2 密码哈希的实际使用、所有权隔离的 API 层落地。
- 首次管理员、登录、用户管理、模板、设置、日报、导出和周报全部业务能力。
- Playwright E2E、PyInstaller 和 Windows 安装/升级验证。
- Windows Job Object 级别的孤儿进程彻底防护（ISS-010，非阻塞）。
- admin 手动整库备份 API（`BACKUP-01`，阶段 8）——DB-03 的自动迁移前备份机制与之相关但不是同一功能，手动备份走独立的短期下载文件流程。

## 4. 当前运行方式

根 `npm run dev` 只启动 `electron-vite dev`；Electron Main 自行拉起并管理 FastAPI sidecar。sidecar 启动时会自动执行 `ensure_runtime_directories()` → `run_startup_migrations()`（首次运行即完成建表）→ 启动 Uvicorn。`dev:backend` 脚本仍保留，供脱离 Electron 单独调试后端时使用（需自行在 `.env` 设置 `WEEKLY_REPORT_RUNTIME_SECRET`，非 `test` 环境启动都会走同样的迁移检查）。

页面启动流程：窗口创建后立即显示，`App.vue` 根据 sidecar 状态在 `StartupView`（pending/failed）与业务路由（ready）之间切换。

## 5. 下一检查点

阶段 3 已满足以下目标，待创建独立 Conventional Commit 后进入阶段 4：

1. ✅ `uv run alembic upgrade head` 在空库上成功执行，`alembic_version` 指向唯一 head（自动化测试验证）。
2. ✅ `PRAGMA foreign_keys`、`journal_mode`、`busy_timeout`、`synchronous` 的实际连接值有自动化验证。
3. ✅ 唯一约束、CHECK、所有权过滤（ORM 层）、乐观锁（ORM 层）、事务回滚、数据库繁忙映射、迁移失败停止启动均有测试。
4. ✅ migration、Model 字段命名与 `database.md` 一致（8 张表、约束、索引均逐项对照实现）。
5. ✅ 阶段 3 质量门禁通过；独立 Reviewer 审查与 Conventional Commit 待用户确认后执行。

阶段 4（认证与用户管理）启动前提醒：`AUTH-01` 需要 Repository/Service 分层的第一个真实落地案例，应作为后续 Agent 建立分层范式的参考点，而不是简单在 Router 里直接操作 Model。
