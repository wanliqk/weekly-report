# 当前开发进度

> 快照日期：2026-08-06
> 当前分支：`v1`
> 原则：本文件只记录当前工作树可验证的实现事实；设计目标不等于完成。

## 1. 总体状态

- 当前已完成阶段：阶段 1 工程基线、阶段 2 Desktop Bootstrap、阶段 3 数据基础与 API Foundation、阶段 4 认证与用户管理、阶段 5 模板、设置与日报闭环、阶段 6 查询导出与桌面保存。
- 已完成提交：`3a9fdbc`（工程基线）、`7386cae`（Desktop Bootstrap）、`8480515`（数据基础与 API Foundation）、`b6b1b47`（补充编码规则）、`1a50e75`（认证与用户管理）、`00e647f`（关闭阶段 4 并启动阶段 5 的状态文档）、`1d965fe`（模板、设置与日报闭环）。阶段 6 实现提交待创建（本文件随该提交一并交付）。
- 当前所在阶段：阶段 6 查询导出与桌面保存已完成；阶段 7 周报闭环尚未开始。
- 阶段 3 实现状态：`DB-01`、`DB-02`、`DB-03`、`API-01`、`QA-03` 均已实现、通过质量门禁并创建独立提交；独立 Reviewer 审查尚待补齐（非阻塞）。
- 阶段 4 实现状态：六项任务均已完成实现、自测、质量门禁、独立审查与提交 `1a50e75`，统一为 `DONE`。
- 阶段 5 实现状态：七项任务均已完成实现、自测、质量门禁、独立审查与提交 `1d965fe`，统一为 `DONE`。
- 阶段 6 实现状态：五项任务（`EXPORT-01`/`EXPORT-02`/`DESK-04`/`FE-05`/`QA-06`）均已完成实现、自测、质量门禁、独立审查（含专项安全审查），统一为 `DONE`。
- 当前阻塞：无业务/技术决策阻塞。
- AI 上下文治理批次：12 份 `ai-docs/` 文档、启动路由和维护规则已完成交叉复核，随独立文档阶段提交交付；未混入后续阶段实现。

## 2. 已实现事实

### 工程与工具链

- 根目录是 npm workspace，当前 workspace 为 `electron`。
- 已存在根 `package-lock.json` 和后端 `uv.lock`。
- 根命令已提供开发、前端 lint、类型检查、测试、构建和 Windows 打包入口。
- Electron 使用 Electron 39、electron-vite 5、Vue 3、TypeScript、Vue Router、Pinia、Element Plus、Axios 和 Vitest。
- 后端使用 Python 3.12、FastAPI、Uvicorn、Pydantic Settings、SQLAlchemy 2.x（异步）、Alembic、aiosqlite；Argon2id、PyJWT 已用于阶段 4 认证，openpyxl 仍只是声明依赖。
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

### 首次管理员初始化（阶段 4 新增，AUTH-01）

- `backend/app/core/clock.py`：`Clock = Callable[[], datetime]` 类型别名 + `utc_now()` 默认实现，供 Service 以关键字参数注入固定时间，测试可替换（coding-rule.md 4.3 要求的模式，供后续 Service 复用）。
- `backend/app/core/security.py`：`hash_password`/`verify_password`，基于 `argon2-cffi` 的 `PasswordHasher`（Argon2id 默认参数）；`verify_password` 捕获 `VerifyMismatchError`/`InvalidHash` 返回 `False`，不向上抛出。
- `backend/app/repositories/user.py::UserRepository`：`any_exists()`（`SELECT COUNT(*)`）供 `bootstrap-status` 使用；`create_if_no_users_exist()` 是本任务的关键并发安全点——用单条 `INSERT ... SELECT ... WHERE NOT EXISTS (SELECT id FROM users)` 把“判空”和“写入”折进同一条 SQLite 语句，利用 SQLite 单写者锁把两个并发调用天然串行化，第二个调用命中 `WHERE NOT EXISTS` 为假从而插入 0 行，返回 `False` 让 Service 抛 `AlreadyInitializedError`；不依赖任何新表或应用层锁。已用两个真实并发 `asyncio.gather` 调用验证（`test_concurrent_bootstrap_attempts_only_ever_create_one_admin`，额外手动重复执行 5 次未出现 flaky）。
- `backend/app/repositories/user_settings.py`、`backend/app/repositories/template.py`：薄封装（`add`/`add_template`/`add_version`），职责仅为 `session.add()` + `flush()`，不含业务判断。
- `backend/app/services/bootstrap.py::BootstrapService`：`is_initialized()`；`bootstrap_admin()` 在同一 `AsyncSession`（同一事务）内完成 `users`（原子守卫插入）→ 重新 `session.get()` 刷新以取回 `token_version`/`is_active`/`created_at` 等由 SQLite `DEFAULT` 填充的列 → `user_settings` → `report_templates`（`current_version_no=1`）→ `template_versions`（`version_no=1`，两个核心字段 `today_work`/`tomorrow_plan`，均 `required=true`/`enabled=true`，`field_key` 各自独立 ULID）→ 最终统一 `commit()`；失败路径抛 `AlreadyInitializedError`（`code=40001`，未在 `api.md` 新增专用错误码，复用已登记的通用业务规则校验码）。
- `backend/app/services/user.py::normalize_username`：`strip().casefold()`，是 `uq_users_username_normalized` 唯一约束背后的规范化规则，供 `AUTH-01` 和未来 `USER-01` 共用同一实现，避免两处判重逻辑漂移。
- `backend/app/schemas/system.py` + `backend/app/api/v1/system.py`：`GET /api/v1/system/bootstrap-status`（匿名，仍需 `X-Runtime-Secret`）、`POST /api/v1/system/bootstrap-admin`（同上）。请求校验：`username` 3–64 字符、`password` 8–128 字符、`display_name` 1–100 字符；密码最小长度 8 位是本任务新增的输入校验基线（上游文档未给出具体数值，已记录到 `decisions.md`）。响应只返回账号元数据（`id`/`username`/`display_name`/`role`/`is_active`/`created_at`），不回传密码或哈希。已注册进 `backend/app/main.py`。

### 认证与用户管理（阶段 4，AUTH-02 / USER-01）

- `backend/app/core/access_token.py`：HS256、24 小时 JWT，强制声明 `sub`/`role`/`ver`/`iat`/`exp`/`jti`，拒绝过期、篡改、缺失或类型错误的 Token。
- `backend/app/core/jwt_secret.py`：首次启动在数据目录独占创建 256-bit 随机签名密钥，后续重启复用；格式损坏时拒绝使用。测试环境可显式注入，生产不使用硬编码密钥。
- `backend/app/services/auth.py` 与 `backend/app/api/dependencies.py`：登录、当前用户、改密、退出及 admin 鉴权依赖已实现；每次鉴权同时检查用户存在、启用状态、角色和 `token_version`。未知用户执行 dummy Argon2 校验，避免明显时序差异；改密后旧 Token 立即失效。
- `backend/app/services/user.py` 与 `backend/app/repositories/user.py`：管理员分页查询、创建、更新角色/状态、重置密码已实现；新用户、设置、默认模板和首个版本同事务创建；大小写无关重复用户名安全回滚；角色/状态变更和重置密码递增 `token_version`。
- 末位有效管理员保护使用条件更新而非“先查再写”，覆盖并发禁用场景；普通用户调用管理 API 返回 `40301`，不存在资源返回 `40401`。管理响应仅含账号元数据，不返回密码哈希、`token_version` 或业务正文。
- `backend/app/core/middleware.py` 已为 `/api/v1/*` 业务响应统一增加 `Cache-Control: no-store`。

### 桌面认证与用户界面（阶段 4，FE-01 / FE-02）

- Electron Main 新增 `SecureTokenStore`，使用 `safeStorage.encryptString/decryptString` 和 `userData/access-token.bin` 保存 Token；preload 仅暴露受信任 frame 的 `token.get/set/clear`，不可用时返回明确状态且不明文回退。
- renderer Axios client 只从内存读取 Bearer Token，同时携带运行期密钥；统一解析 `{code,msg,data}`，收到 `40102` 时清理 Token 并返回登录页。
- Pinia auth store 覆盖首次初始化、safeStorage 恢复后 `/auth/me` 校验、登录、改密与退出；数据库仍需初始化时会清理陈旧 Token。
- Router 已接入 setup/login/app layout/admin users，并按 sidecar、初始化、登录和 admin 角色守卫；用户管理页支持列表、创建、角色/状态编辑与密码重置，对敏感变更展示确认。
- renderer 未使用 `localStorage` 或 `sessionStorage`，未在日志中记录 Token、密码、签名密钥或 runtime secret。

### 模板、设置与日报后端（阶段 5，TEMPLATE-01 / SETTING-01 / DAILY-01 / DAILY-02）

- 模板 API 已实现当前版本、不可变发布和历史摘要；Service 强制六类字段规则、核心字段不可删除且至少启用一个、既有 `field_key` 稳定、新字段由服务端生成 ULID，并以条件更新和唯一约束处理并发版本冲突。
- 个人设置 API 已实现 `auto_archive_on_submit` 读写，时区固定为 `Asia/Shanghai`；能力 API 固定返回 `wecom_sync:false`，未定义或调用任何企业微信同步接口。
- 日报 API 已实现按日期创建、详情、日期/状态分页查询、草稿保存、提交和归档。Repository 的详情、列表和条件更新均带 `owner_id`；同一用户同日唯一冲突返回 `40901` 与已有日报 ID。
- 创建日报时在同一数据库事务读取当前模板版本并写入完整快照；历史、未来和闰日均允许。后续保存/提交始终按快照校验，不读取当前模板解释旧日报。
- 状态机固定为 `draft → submitted → archived`：草稿保存、提交和归档使用 `status + version + owner_id` 条件更新；版本冲突为 `40904`，非法状态为 `40902`。自动归档在提交同一条条件更新中原子写入提交/归档状态和时间。
- 字段校验拒绝未知/停用字段、错误类型、无效/重复选项、布尔冒充数字及 `NaN/Infinity`；提交时额外检查必填字段，统一返回 `42201` 字段错误。

### 模板与日报界面（阶段 5，FE-03 / FE-04）

- `/templates` 已实现字段新增、删除、排序、启停、必填、六类类型/选项配置、核心字段保护、不可变版本发布和历史摘要展示；既有稳定键只由后端返回并原样提交。
- `/daily`、`/daily/new`、`/daily/:id` 已实现日期/状态筛选、稳定分页、空态、Asia/Shanghai 默认日期、重复日期跳转、模板快照动态表单、草稿保存、提交/归档确认和只读状态展示。
- 前端收到 `42201` 会把错误映射回字段；收到 `40904` 会保留当前输入并明确提示版本冲突。时间显示固定使用 `Asia/Shanghai`，未提前混入阶段 8 的设置/企业微信占位 UI。

### 导出后端（阶段 6，EXPORT-01 / EXPORT-02）

- `backend/app/schemas/export.py`：`ExportCreateRequest` 用 `model_validator` 强制 `report_ids` 与 `filter` 二选一（都提供或都不提供均拒绝）、`report_ids` 非空；`ExportFilter` 校验 `date_from<=date_to`。
- `backend/app/repositories/daily_report.py` 新增 `list_owned_archived_by_ids`/`list_owned_archived_by_range`：均同时按 `owner_id` 与 `status='archived'` 过滤，按 `work_date ASC, id ASC` 排序供导出使用；不改变既有查询方法。
- `backend/app/services/export.py::ExportService`：
  - `_resolve_reports` 对显式 `report_ids` 去重后按同一查询同时校验所有权与归档状态，缺失/非本人/非归档的 ID 统一判定为“不可导出”，整体拒绝并在 `data.invalid_report_ids` 列出问题 ID（`40001`）；不做部分导出。
  - `plan_export_columns` 是纯函数：按各日报模板快照的时间顺序合并 `field_key`，历史新增字段追加在后，标签取该字段最近一次出现时的文案（`field_key` 不变，标签变化不拆列）；两个不同 `field_key` 恰好得到相同表头文本时，用 `field_key` 末 4 位加后缀消歧。
  - `build_export_workbook` 是纯函数（`asyncio.to_thread` 卸载），基础列（工作日期/提交时间/归档时间，`Asia/Shanghai` 显示）在前，动态列在后；对以 `=` 开头的字符串值加前缀单引号防止被 Excel/openpyxl 提升为可执行公式（CWE-1236），`+`/`-`/`@` 前缀不处理（openpyxl 不会将其识别为公式，且中文日报常用 `-`/`+` 作列表符号）。
  - `create()` 在同一次调用内完成校验、生成、落盘和状态落库（`succeeded`/`failed` 两种终态），不引入后台任务队列；生成失败会被捕获并记录 `error_message`，不抛出到 HTTP 层。
  - `get_download()`、`_expire_if_needed()`、`cleanup_expired()` 均先做 24 小时懒过期判断（`succeeded` 且 `expires_at` 已过则转 `expired` 并删除文件），再在实际删除/读取文件前调用 `_resolve_within_export_dir` 校验路径解析后确实落在 `export_temp_dir` 内。
  - `run_startup_export_cleanup`（`backend/app/__main__.py::_cleanup_expired_exports`）在 `ensure_runtime_directories`/`run_startup_migrations` 之后、创建 FastAPI app 之前执行，扫描全部用户的到期文件（非 owner 过滤，属于维护性清理，不是业务查询）。
  - `backend/app/core/timezone.py`：固定 UTC+8 常量偏移（不用 `zoneinfo`，避免 Windows 上依赖可选 `tzdata` 包），供导出文件内 `Asia/Shanghai` 时间显示使用。
  - `backend/app/core/clock.py` 新增 `as_naive_utc()`：SQLite `DateTime()` 列往返后丢失 `tzinfo`（数值仍是正确 UTC），与 `Clock` 返回的 tz-aware 值比较前必须先归一化，否则直接抛 `TypeError`（已在服务层和 Repository 查询边界统一处理）。
- `backend/app/api/v1/exports.py`：`POST /api/v1/daily-report-exports`、`GET /api/v1/daily-report-exports/{id}`、`GET /api/v1/daily-report-exports/{id}/file` 均已实现并接入 `main.py`；文件下载响应设置标准 xlsx MIME 和安全 ASCII 文件名（`daily-report-export-<Asia/Shanghai 时间戳>.xlsx`），不返回内部路径。
- `backend/app/main.py` 的 `CORSMiddleware` 新增 `expose_headers=["Content-Disposition"]`：真实 Electron 联调发现，若不显式暴露该响应头，renderer 端 `fetch`/`axios` 读取不到服务端生成的文件名（浏览器 CORS 响应头默认安全列表不含 `Content-Disposition`），会静默回退成通用默认文件名；已加回归测试固定该行为。
- `backend/pyproject.toml` 为 `openpyxl`（无内联类型标注）新增 `[[tool.mypy.overrides]] ignore_missing_imports`。

### 桌面保存与导出交互（阶段 6，DESK-04 / FE-05）

- `electron/src/main/export/file-saver.ts::ExportFileSaver`：`suggestedName` 先经 `path.basename()` 再匹配 `^[A-Za-z0-9._-]{1,150}\.xlsx$`，`data` 必须是非空且不超过 25MB 的 `Uint8Array`；校验通过后才调用注入的 `dialog.showSaveDialog`，实际写入路径始终取自该系统对话框自身的返回值，renderer 提供的文件名只影响对话框默认建议名，从不决定真实写入位置。
- `electron/src/main/ipc/register-runtime-bridge.ts` 新增 `export:save-file` handler，与既有 channel 一样先校验 `event.senderFrame === window.webContents.mainFrame`；`electron/src/preload/index.ts` 暴露 `window.runtimeBridge.exportFile.save(suggestedName, data)`，未暴露通用文件系统能力。
- `electron/src/renderer/src/api/client.ts` 新增 `requestBinary()`：以 `responseType:'arraybuffer'` 下载文件并从 `Content-Disposition` 解析文件名；错误路径下会把 axios 返回的 `ArrayBuffer` 错误体尝试解码为 JSON，避免真实业务错误码被降级成通用 `50001`。
- `/daily` 列表页新增复选列与“导出所选”“导出当前筛选（仅归档）”按钮：创建任务→若 `record_count>0` 则下载字节并调用 `exportFile.save`→按 `saved`/`canceled`/`failed` 展示对应提示；命中 `40001` 时把 `invalid_report_ids` 映射为当前页可见的工作日期展示，而非裸 ULID。

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

阶段 4 认证与用户管理当前工作树实际执行并通过：

- `uv sync --directory backend --frozen`：锁文件一致，共检查 46 个包。
- `uv run --directory backend ruff check .`、`ruff format --check .`：0 error，66 个文件格式合规。
- `uv run --directory backend mypy`（strict，66 个源文件）：0 错误。
- `uv run --directory backend pytest`：**94 项测试全部通过**，覆盖初始化并发、JWT 过期/篡改、登录错误、运行期密钥与 JWT 双校验、改密/重置/禁用旧 Token 失效、创建关联数据、重复用户名事务回滚、非 admin 权限和并发末位管理员保护。
- `npm run lint`、`npm run typecheck`：通过。
- `npm test`：**12 个文件 49 项测试全部通过**，包含 safeStorage Token Store/IPC、auth store 和 API client。
- `npm run test:integration --workspace electron`：真实后端进程 **2 项通过**，连续启动使用不同动态端口且退出后无孤儿进程。
- `npm run build`：main/preload/renderer 生产构建通过；仅有 `@vueuse/core` 的第三方 PURE 注释位置提示，不影响产物。
- `git diff --check`：通过；敏感模式扫描未发现 local/sessionStorage、Token/密码/密钥日志或构建变量泄露。
- 主 Agent 按 `dev-workflow` 完成安全、Python、TypeScript/Vue 自审，审查中发现并修复：用户名去空白后的最小长度校验、已登录用户根路由绕过应用布局、确认框取消导致未处理 Promise。独立 Reviewer 已完成审查，阶段 4 无未解决 P0/P1。

阶段 5 模板、设置与日报闭环当前工作树实际执行并通过：

- `uv run --directory backend ruff check .`、`ruff format --check .`：0 error，81 个文件格式合规。
- `uv run --directory backend mypy`（strict，81 个源文件）：0 错误。
- `uv run --directory backend pytest`：**117 项测试全部通过**，覆盖模板不可变版本/稳定键/核心字段、设置、同日并发、历史/未来/闰日、快照、必填/类型/有限数值、状态非法、手工/自动归档、乐观锁和所有权隔离。
- `npm run lint`、`npm run typecheck`：通过。
- `npm test`：**14 个文件 54 项测试全部通过**，新增模板字段规则和日报动态表单纯函数测试。
- `npm run test:integration --workspace electron`：真实后端进程 **2 项通过**，阶段 5 未破坏动态端口和退出清理链路。
- `npm run build`：main/preload/renderer 生产构建通过；仅有 `@vueuse/core` 第三方 PURE 注释位置提示，renderer 主 JS 约 2.85 MB，继续由 ISS-007 跟踪。
- `git diff --check`：通过。主 Agent 按 `dev-workflow` 完成安全、并发、Python、TypeScript/Vue 自审，修复非有限数值、固定时区显示及跨阶段 UI 混入问题；独立审查完成，当前无未解决 P0/P1。

阶段 6 查询导出与桌面保存当前工作树实际执行并通过：

- `uv run --directory backend ruff check .`、`ruff format --check .`：0 error，89 个文件格式合规。
- `uv run --directory backend mypy`（strict，89 个源文件）：0 错误。
- `uv run --directory backend pytest`：**140 项测试全部通过**（阶段 5 遗留 117 项 + 本阶段新增 23 项：动态列规划纯函数 5、导出 Service 直连测试 10——含跨模板合并/公式注入防护/失败落库/懒过期删除/路径边界拒绝/启动清理扫描、导出 API 测试 8——含互斥校验、混合状态整体拒绝、所有权隔离 404、CORS `Content-Disposition` 暴露回归）。
- `npm run lint`、`npm run typecheck`：通过。
- `npm test`：**16 个文件 76 项测试全部通过**，新增 `ExportFileSaver` 白名单校验、IPC 受信任帧校验、导出 API 客户端（含二进制下载与 CORS 错误体解码）、`invalid_report_ids` 展示映射测试。
- `npm run test:integration --workspace electron`：真实后端进程 **2 项通过**，阶段 6 未破坏动态端口和退出清理链路。
- `npm run build`：main/preload/renderer 生产构建通过；仅有 `@vueuse/core` 第三方 PURE 注释位置提示（ISS-007 继续跟踪）。
- `git diff --check`：通过。
- 真实环境手动验证（`npm run dev` 真实启动 Electron + 真实后端，非测试替身）：完成首次初始化→登录→创建日报→填写→提交→归档→在 `/daily` 勾选/筛选触发导出→系统原生“另存为”对话框弹出并显示服务端生成的带时间戳文件名→保存后 Toast 提示成功→用 `openpyxl` 校验磁盘上的真实文件内容与页面输入完全一致→再次导出并点击“取消”验证“已取消保存”提示。过程中发现并修复一个真实缺陷：`CORSMiddleware` 未 `expose_headers` 导致 renderer 读不到服务端文件名、保存对话框回退为通用默认名；修复后重启真实环境复现并确认已解决，已补充回归测试固定该行为。
- 独立安全专项审查（`security-review` 流程，含二次假阳性复核）：识别出 Excel 公式注入风险——自由文本字段以 `=` 开头时会被 openpyxl 提升为可执行公式，导出文件被他人在 Excel 中打开时可能触发；已修复（仅对 `=` 前缀转义，不影响中文场景常见的 `-`/`+` 列表符号），并补充专项测试覆盖公式防护与列表符号不受影响两种场景。除该项外未发现文件白名单、路径越界、所有权隔离、CORS 放宽等方向的可利用漏洞。
- 主 Agent 自审：无跨层访问、无临时接口、日志/异常未见密码/JWT/密钥/完整正文；独立审查完成，阶段 6 无未解决 P0/P1。

## 3. 尚未实现

以下均为设计目标，当前不得标记为完成：

- 开发/生产 sidecar 路径解析中，生产分支的 PyInstaller `onedir` 产物本身（`PKG-01`，阶段 9）——`build/sidecar/` 仍是空占位目录。
- 周报对应的 Repository/Service/API 与前端页面尚未实现（阶段 7）；个人设置/企业微信占位/手动备份 UI 属于阶段 8 `FE-07`，尚未实现。
- Playwright E2E、PyInstaller 和 Windows 安装/升级验证。
- Windows Job Object 级别的孤儿进程彻底防护（ISS-010，非阻塞）。
- admin 手动整库备份 API（`BACKUP-01`，阶段 8）——DB-03 的自动迁移前备份机制与之相关但不是同一功能，手动备份走独立的短期下载文件流程。

## 4. 当前运行方式

根 `npm run dev` 只启动 `electron-vite dev`；Electron Main 自行拉起并管理 FastAPI sidecar。sidecar 启动时会自动执行 `ensure_runtime_directories()` → `run_startup_migrations()`（首次运行即完成建表）→ 启动 Uvicorn。`dev:backend` 脚本仍保留，供脱离 Electron 单独调试后端时使用（需自行在 `.env` 设置 `WEEKLY_REPORT_RUNTIME_SECRET`，非 `test` 环境启动都会走同样的迁移检查）。

页面启动流程：窗口创建后立即显示，`App.vue` 先根据 sidecar 状态展示 `StartupView`（pending/failed）；ready 后恢复 safeStorage Token 并调用 `/auth/me` 校验，再按 bootstrap、登录和角色状态进入对应路由。

## 5. 下一检查点

阶段 3 已满足以下目标，独立提交 `8480515` 已创建：

1. ✅ `uv run alembic upgrade head` 在空库上成功执行，`alembic_version` 指向唯一 head（自动化测试验证）。
2. ✅ `PRAGMA foreign_keys`、`journal_mode`、`busy_timeout`、`synchronous` 的实际连接值有自动化验证。
3. ✅ 唯一约束、CHECK、所有权过滤（ORM 层）、乐观锁（ORM 层）、事务回滚、数据库繁忙映射、迁移失败停止启动均有测试。
4. ✅ migration、Model 字段命名与 `database.md` 一致（8 张表、约束、索引均逐项对照实现）。
5. ✅ 阶段 3 质量门禁通过并创建独立提交；独立 Reviewer 审查仍待补齐（非阻塞）。

阶段 4（认证与用户管理）六项任务已完成实现、自测、质量门禁、独立审查与提交 `1a50e75`，统一为 `DONE`：

1. ✅ 空库原子创建 admin + `user_settings` + `report_templates` + `template_versions`（同一事务，自动化测试验证）。
2. ✅ 重复初始化安全失败，含真实并发场景（`asyncio.gather` 双重调用，仅一个成功，自动化测试验证，额外重复执行 5 次无 flaky）。
3. ✅ 密码使用 Argon2id 哈希，不落明文、不回传哈希。
4. ✅ 默认模板核心字段（今日工作内容/明日工作计划）与 `database.md` 3.4 节 JSON 结构一致。
5. ✅ 24h JWT、持久化签名密钥、用户实时状态/角色/`token_version` 校验、登录/改密/退出与 admin 依赖完成。
6. ✅ 管理员用户查询、创建、角色/状态修改、重置密码、关联默认数据和并发末位管理员保护完成。
7. ✅ safeStorage Token 桥接、初始化/登录/布局/鉴权守卫/40102 处理及用户管理界面完成，renderer 无普通 Web Storage 持久化。
8. ✅ 后端 94 项、前端 49 项、真实 sidecar 集成 2 项及生产构建全部通过；主 Agent 自审无未解决 P0/P1。
9. ✅ 独立 Reviewer 审查完成，无未解决 P0/P1；阶段 4 已关闭。

阶段 5 七项任务已完成实现、自测、质量门禁、独立审查与提交 `1d965fe`，统一为 `DONE`：

1. ✅ 模板六类字段规则、核心字段、稳定键、不可变发布和历史摘要已实现。
2. ✅ 自动归档设置、固定 Asia/Shanghai 和 `wecom_sync:false` 能力 API 已实现。
3. ✅ 日报唯一创建、快照、稳定查询、所有权过滤、草稿/提交/归档状态机和乐观锁已实现。
4. ✅ 模板编辑、动态字段、日报列表/创建/详情、确认与冲突反馈已实现。
5. ✅ 后端 117 项、前端 54 项、真实 sidecar 集成 2 项及生产构建全部通过；主 Agent 自审无未解决 P0/P1。
6. ✅ 独立 Reviewer 审查完成，无未解决 P0/P1；实现提交 `1d965fe` 已创建，阶段 5 正式关闭。

阶段 6 五项任务已完成实现、自测、质量门禁、独立审查（含专项安全审查），统一为 `DONE`：

1. ✅ 导出条件互斥校验（ID/筛选二选一）、仅本人归档日报约束、混合状态整体拒绝已实现。
2. ✅ 跨模板 `field_key` 动态列合并与同名消歧已实现。
3. ✅ xlsx 线程卸载生成、标准 MIME/安全文件名、24h 懒过期与启动清理、路径边界校验已实现。
4. ✅ Electron 保存对话框白名单（文件名/字节双重校验、受信任帧、写入路径始终取自系统对话框）已实现。
5. ✅ 日报列表勾选/筛选导出、处理中状态、不可导出列表提示已实现。
6. ✅ 后端 140 项、前端 76 项、真实 sidecar 集成 2 项及生产构建全部通过；真实 `npm run dev` 环境完成含原生保存对话框的全链路手动验证。
7. ✅ 独立审查（含专项安全审查）完成，发现并修复 Excel 公式注入与 CORS 文件名暴露两项真实问题，均已补充回归测试；无未解决 P0/P1。实现提交待创建，阶段 6 正式关闭。
