# 当前开发进度

> 快照日期：2026-08-07
> 当前分支：`v1`
> 原则：本文件只记录当前工作树可验证的实现事实；设计目标不等于完成。

## 1. 总体状态

- 当前已完成阶段：阶段 1 工程基线、阶段 2 Desktop Bootstrap、阶段 3 数据基础与 API Foundation、阶段 4 认证与用户管理、阶段 5 模板、设置与日报闭环、阶段 6 查询导出与桌面保存、阶段 7 周报闭环、阶段 8 设置能力与受控备份、阶段 9 质量与发布。V1 规划的全部 9 个阶段均已交付。
- 已完成提交：`3a9fdbc`（工程基线）、`7386cae`（Desktop Bootstrap）、`8480515`（数据基础与 API Foundation）、`b6b1b47`（补充编码规则）、`1a50e75`（认证与用户管理）、`00e647f`（关闭阶段 4 并启动阶段 5 的状态文档）、`1d965fe`（模板、设置与日报闭环）、`d6ab86e`（查询导出与桌面保存）、`fd4df17`（关闭阶段 6 并回填提交号）、`346b0ea`（周报闭环）、`2584133`（关闭阶段 7 并回填提交号）、`00caa33`（设置能力与受控备份）、`0148171`（质量与发布）、`a866872`（第二版增量需求）、`e767ebd`（第二版技术方案）、`e86b88c`（第二版迁移与认证基线 BE-10A）、`784f96c`（日报聚合、管理员撤销与用户安全删除 BE-10B）、`5e33348`（回填 BE-10B 提交号）、`c7ed342`（BE-10B 契约修正 fix，见 ISS-023）。
- 当前所在阶段：CR-20260807-01 的 `REQ-10`、`DESIGN-10`、`BE-10A`、`BE-10B`、`BE-10C`、`FE-10`、`QA-10` 均已完成；第二版增量全部交付完毕。
- 阶段 3 实现状态：`DB-01`、`DB-02`、`DB-03`、`API-01`、`QA-03` 均已实现、通过质量门禁并创建独立提交；独立 Reviewer 审查尚待补齐（非阻塞）。
- 阶段 4 实现状态：六项任务均已完成实现、自测、质量门禁、独立审查与提交 `1a50e75`，统一为 `DONE`。
- 阶段 5 实现状态：七项任务均已完成实现、自测、质量门禁、独立审查与提交 `1d965fe`，统一为 `DONE`。
- 阶段 6 实现状态：五项任务（`EXPORT-01`/`EXPORT-02`/`DESK-04`/`FE-05`/`QA-06`）均已完成实现、自测、质量门禁、独立审查（含专项安全审查）与提交 `d6ab86e`，统一为 `DONE`。
- 阶段 7 实现状态：四项任务（`WEEKLY-01`/`WEEKLY-02`/`FE-06`/`QA-07`）均已完成实现、自测、质量门禁、独立审查（含专项安全审查），统一为 `DONE`。
- 阶段 8 实现状态：三项任务（`BACKUP-01`/`FE-07`/`QA-08`）均已完成实现、自测、质量门禁、独立审查（含专项安全审查），统一为 `DONE`。
- 阶段 9 实现状态：四项任务（`QA-09`/`PKG-01`/`PKG-02`/`REL-01`）均已完成实现、自测、质量门禁、独立审查，统一为 `DONE`。真实安装/升级/卸载验证在本机（无独立干净虚拟机）完成，该限制已在阶段开工前与用户确认。
- 当前阻塞：无。ISS-018/019/020/021/022 已随 `QA-10` 完成端到端验收全部升级为 RESOLVED；ISS-023（BE-10B 契约偏差）已 RESOLVED；ISS-024（既有 Playwright spec 断言 V1 UI）已随 `QA-10` 重写全部 spec 关闭为 RESOLVED；新记录 ISS-025（P3，非缺陷）：生产环境下无法用环境变量隔离已打包二进制的数据目录（`SEC-010` 既定安全设计），仅供以后需要沙箱化已打包产物时参考。
- 第二版需求与设计事实：增量需求和方案已确认；日期/审计表、V1 数据迁移、周报 JSON V2 化、双账号初始化、强制改密和自动归档移除（BE-10A），同日多条目、幂等创建、草稿删除、日期级归档、管理员最小权限撤销/审计、用户安全删除（BE-10B），周报/导出改读日期级正式快照与新增个人统计 API（BE-10C），以及全部 Electron/Vue 界面适配——强制改密路由、菜单改名、我的日报月历、我的周报多来源展示、统计页、管理员日报管理/用户删除、设置收口（FE-10）——均已完成并通过真实 Electron 冒烟验证。当前仅剩 `QA-10` 的迁移/并发/权限专项验收和 E2E 套件重建。
- AI 上下文治理批次：12 份 `ai-docs/` 文档、启动路由和维护规则已完成交叉复核，随独立文档阶段提交交付；未混入后续阶段实现。
- 2026-08-08：应用户直接指令完成日报 Excel 导出排版增强（`PROD-021`）：新增 `backend/app/services/export_style.py` 封装标题/表头/边框/列宽/行高/冻结表头样式，`export.py` 的 `build_export_workbook` 改为写入 headers/data 后调用 `style_report_sheet()`；未改动列合并、公式防注入、多来源渲染等业务逻辑。因新增标题行，`test_export_service.py`/`test_exports_api.py` 中依赖固定行号的断言已同步更新（表头从 `rows[0]` 移到 `rows[1]`，数据从 `rows[1..]` 移到 `rows[2..]`）。已执行 `uv run ruff check .`、`uv run mypy`、`uv run pytest`（124 源文件、全量测试两次运行均 100% 通过，含一次单测 `test_expired_and_tampered_tokens_map_to_40102` 的偶发无关 flake，隔离重跑与全量重跑均通过，与本次改动无关）；未创建提交，等待用户确认。
- 2026-08-08：应用户直接指令新增模板字段类型 `PROJECT_LIST`（`PROD-022`），支持一篇日报登记多个项目各自的工作内容和完成状态，不修改数据库结构（`fields_json`/`content_json` 仍是既有 TEXT/JSON 列）。后端：`schemas/template.py` 的 `FieldType` 新增该字面量（模板发布沿用既有“非 select/multiselect 不得配置 options”规则，无需新增校验分支）；`schemas/daily_report.py` 新增 `ProjectListEntry`（`project`/`content`/`status` 三态固定枚举 `TODO`/`DOING`/`DONE`）并入 `DailyFieldValue` 联合（已用 `TypeAdapter` 实测 Pydantic smart-union 能按列表元素类型正确区分 `multiselect` 与本类型，无需判别字段）；`services/daily_report.py` 的 `_project_list_error()` 校验每个条目的 `project`/`content` 非空、`status` 合法、字段无缺失/多余，且同时兼容 `save()` 传入的原始 dict 与 `submit()` 经 `parse_daily_content()` 重新解析后的 `ProjectListEntry` 模型两种形态（实现时曾遗漏后一种形态导致 submit 阶段误报“字段不完整”，已修正并由 `test_project_list_field_submits_and_archives_with_multiple_entries` 覆盖该回归）；`services/export.py` 的 `_single_source_cell()` 按列表首元素类型分流到新增的 `_format_project_list()`，按项目分组渲染为 `项目:X\n- 内容`（用半角冒号而非全角冒号，因全角冒号会触发 Ruff `RUF001` 全角标点检测且仓库此前无任何 `noqa` 先例），不显示完成状态，且因固定前缀不以 `=` 开头而天然免疫公式注入（无需依赖 `_defuse_formula` 的转义，仍保留调用以防未来格式调整）。前端：`types/template.ts`/`types/daily-report.ts` 新增类型；`utils/template-fields.ts` 新增 `projectTaskStatusLabel`/`isProjectListArray`/`formatProjectListEntries` 共享辅助并被 `daily-form.ts`/`weekly-report.ts` 复用；`DynamicFieldInput.vue` 新增可动态增删的项目/内容/状态三列编辑区（沿用 `updateXxx(value: unknown)` 具名函数处理 `@update:model-value` 的既有风格，未使用模板内联类型化箭头函数，因仓库此前无该写法先例）；`TemplatesView.vue` 字段类型下拉新增“项目列表”。测试：后端新增 22 项（模板发布、内容校验的 6 种非法形态、必填空列表拒绝提交、保存/提交/归档往返、导出分组渲染/多来源编号/无需转义即免疫公式注入），前端新增 7 项（`emptyFieldValue`/`usesOptions`/`isProjectListArray`/`formatProjectListEntries`/`projectTaskStatusLabel`/`formatDailyFieldValue`/`formatWeeklyFieldValue`/`initializeDailyContent` 深拷贝）。实际门禁：后端 `uv run ruff check .`（通过）、`uv run ruff format --check .`（除本次改动外，`app/services/export_style.py` 存在一项与本次改动无关的既有格式漂移，未改动该文件）、`uv run mypy`（strict，124 源文件，通过）、`uv run pytest`（JUnit XML 确认 **302 项、0 失败、0 错误、0 跳过**，含阶段 10C/QA-10 遗留 280 项）均实际执行并通过；前端 `npm run lint`（0 error/0 warning，修复中途 `eslint --fix` 顺带格式化了未改动的 `electron/src/main/index.ts` 的一处预先存在的空行警告，已用 `git show HEAD:... | tr -d '\r'` 逐字节核对还原为改动前内容，`cmp` 确认与 HEAD 完全一致，不计入本次改动）、`npm run typecheck`、`npm test`（**22 文件 132 项全部通过**，较改动前 125 项净增 7 项）、`npm run build` 均实际执行并通过。已知非阻塞：`electron/src/main/index.ts` 第 51 行存在一处与本次改动无关的既有 prettier 空行警告（HEAD 提交已如此，`npm run lint` 的 `--max-warnings=0` 因此在改动前就会失败），本次未修复以保持提交范围聚焦。已随提交 `7ce6928` 交付。
- 2026-08-08：用户反馈 `PROD-022` 首版导出格式（单元格内“项目:X\n- 内容”分组文本）不符合预期，要求改为真正的二维表（动态表头、每项目一行、保持现有表头加粗/边框/自动换行/自动列宽样式、不影响其他字段类型）；因“一个字段值渲染成多行多列的表”与既有“一天一行”的主表模型结构性冲突，落地前用 `AskUserQuestion` 确认了两种可行布局（主表下方按日期分块 vs. 独立工作表），用户选择前者。已实现并记为 `PROD-023`：`export.py::plan_export_columns` 新增 `include` 过滤谓词，主表列用 `field_type != "PROJECT_LIST"`、块规划用 `field_type == "PROJECT_LIST"`（两者复用同一套顺序/去重/消歧逻辑）；`build_export_workbook` 对每个「已归档日期 × PROJECT_LIST 字段」组合（若该组合下所有来源条目累计至少一条目）在主表下方追加：空行 + 标题行（`{日期} {责任人} · {字段标签}`）+ 固定表头行（项目/工作内容/完成状态）+ 逐条目数据行，多来源条目按提交顺序直接展平为连续行（不做 `[N]` 来源编号，不按项目名合并，因合并会在新增的“完成状态”列上产生冲突）；`项目`/`工作内容`现在是独立单元格，改为各自调用 `_defuse_formula()`（不再依赖旧版单元格前缀“天然免疫”公式注入的特性）；`export_style.py` 新增 `ProjectListBlockLayout` 与 `_style_block_title()`，`style_report_sheet()` 新增 `project_list_blocks` 参数，复用既有表头/表体样式函数为每个分块单独打表头加粗+边框+自动换行，并把列宽自适应改为跨"主表+全部分块"行范围与列数的统一一次性计算（因为分块的 3 列复用主表最左侧列字母）。用一次性脚本对生成的真实 xlsx 做了程序化验证（超出自动化测试断言范围，人工确认）：分块表头 `bold=True`/`fill=FF1F3864`/`border=thin`，数据行 `wrap_text=True`/`border=thin`，标题行 `bold=True`，列宽按内容自适应（示例中 A=31/B=21/C=12），`freeze_panes` 仍锚定主表首个数据行未被分块影响。测试：删除原先 3 个针对单元格分组渲染/`[N]` 编号的测试，新增 4 个针对分块表结构的测试（主表不含该字段列+分块标题/表头/数据行/总行数、项目与内容各自独立转义、多来源展平不加编号、空列表日期不生成分块且分块顺序跟随主表日期顺序），新增 `_row_values()` 测试辅助函数按行读取并裁剪 `sheet.max_column` 因分块 3 列而对更窄主表行产生的尾部 `None` 填充。实际门禁：`uv run ruff check .`、`uv run ruff format .`（仅重排本次改动引入的 2 处超长行，未改动 `export_style.py` 中与本次无关的既有格式漂移之外的内容）、`uv run mypy`（strict，124 源文件）均通过；`uv run pytest`（JUnit XML 确认 **303 项、0 失败、0 错误、0 跳过**）通过。未改动前端（本次改动完全在导出渲染的后端实现内）。未创建提交，等待用户确认。

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

### 周报后端（阶段 7，WEEKLY-01 / WEEKLY-02）

- `backend/app/services/weekly_report.py::week_end_for`：纯函数，校验 `week_start` 必须是周一（`weekday()==0`，否则 `40001`），返回 `week_start+6`；跨年周（如 2025-12-29→2026-01-04）和闰周（2024-02-26→2024-03-03）已用真实日期验证。
- `build_weekly_content` 是纯函数：对每份日报解析其自身 `template_snapshot_json`/`content_json`（不读取当前模板），只保留 `enabled` 字段并按 `sort_order` 排序，输出 `{field_key,label,value}`；`field_type`/`options` 不进入周报 JSON（与 `database.md` 3.6 节固定结构一致），前端展示因此退化为纯文本摘要，不复用日报的分类型输入组件。
- `WeeklyReportRepository`（`backend/app/repositories/weekly_report.py`）：`save_content`/`replace_on_regenerate` 均用 `WHERE id=? AND user_id=? AND version=?` 条件更新；`replace_sources` 对 `weekly_report_sources` 先删后插且不带 owner 过滤，但调用方（`generate`/`regenerate`）只会在已经拿到本人的 `report.id`（刚插入或条件更新命中之后）时才调用它，不构成越权路径（已由独立安全审查确认）。
- `WeeklyReportService.generate()`：读取当前 owner 在该自然周内的 `list_owned_archived_by_range`（复用阶段 6 已有方法，只取 `archived`），在一次事务内插入 `weekly_reports` 与 `weekly_report_sources`；同周唯一冲突通过捕获 `IntegrityError` 后回查现有记录判定，返回 `40903` 与 `existing_weekly_report_id`（与日报唯一创建同一模式），已用真实并发 `asyncio.gather` 验证只成功一次。
- `availability()` 新增 `DailyReportRepository.list_owned_in_range`（不筛选状态，仅按 `owner_id`+日期区间），用于展示自然周内 7 天各自的日报状态（`draft`/`submitted`/`archived`/`None`），独立于只取 `archived` 的生成路径，避免"预检"和"生成"混用同一查询产生误导。
- `save()` 只接受并覆盖 `supplement`/`next_week_plan`/`risks` 三个自由文本字段，`content_json` 中的 `days` 保持不变，从机制上保证"人工编辑不反写日报"且不篡改自动摘要部分。
- `regenerate()` 强制 `confirm_overwrite=True`（`WeeklyRegenerateRequest` 无默认值，缺省即 422；服务层再显式校验一次，`40001`），确认后用当天重新查询到的 `archived` 日报重建 `days`，同时重置 `supplement`/`next_week_plan`/`risks` 为空，`generated_content_json` 与 `content_json` 都指向这份新内容（不保留任何历史版本，符合 `ADR-008`/`RISK-002`）。
- `backend/app/api/v1/weekly_reports.py`：`/availability`、`""`（GET 列表/POST 生成）、`/{id}`（GET/PUT）、`/{id}/regenerate` 六个接口均已实现并接入 `main.py`；`/availability` 路由必须先于 `/{report_id}` 注册，否则会被路径参数捕获。

### 周报前端（阶段 7，FE-06）

- `/weekly` 新增自然周选择（任选一天自动定位到周一，不依赖 Element Plus 周选择器语义）、逐日状态标签、未归档日期提示、空周提示、生成/查看按钮（已存在则直接跳转，不重复生成）；下方为按周范围筛选的历史周报分页列表。
- `/weekly/:id` 展示按日期分组的来源卡片（含"查看来源日报"跳转到 `/daily/:id`，不提供反向编辑入口）、三个自由文本编辑区、保存与重新生成操作；重新生成走 `ElMessageBox.confirm` 醒目二次确认（危险态按钮），文案明确告知会同时覆盖自动内容和人工编辑且不可撤销。
- `electron/src/renderer/src/utils/weekly-report.ts`：`mondayOfWeek`/`weekEndFor` 使用 UTC 锚定的纯日期算术（不做真实时区换算，只做日历计算），避免本地时区在日期边界产生偏差；已用跨年周和闰周输入验证。
- 真实 Electron 环境联调发现并修复一处显示缺陷：周报生成时间/更新时间最初直接展示服务端 UTC ISO 字符串（含 `+00:00`），未按 `Asia/Shanghai` 格式化；已改为复用日报页面已有的 `formatShanghaiTime`。

### 手动整库备份后端（阶段 8，BACKUP-01）

- `backend/app/core/config.py` 新增 `Settings.manual_backup_temp_dir`（默认 `.local-data/temp/manual-backups`，与迁移前自动备份的 `backup_dir` 是不同目录），随 `data_dir`/`log_dir`/`backup_dir`/`export_temp_dir` 一起被路径解析校验和 `ensure_runtime_directories` 创建。
- `backend/app/core/backup_registry.py::BackupRegistry`：进程内 `dict[str, BackupRecord]`，按 `database.md` §6 明确要求"短期下载文件不登记业务表，使用进程内随机 ID 映射"；作为 `app.state.backup_registry` 单例随 `create_app()` 创建，通过 `get_backup_registry` 依赖注入到路由。
- `backend/app/services/backup.py::BackupService`：`create()` 在 `asyncio.to_thread` 中执行 `PRAGMA wal_checkpoint(TRUNCATE)` 后用 `sqlite3.Connection.backup()` 生成一致性快照（与 `db/migrate.py::_backup_database` 同一序列，按需触发而非仅迁移前）；`sqlite3.Error` 转换为不泄露细节的 `BackupCreationFailedError`（`50001`），并会清理已创建但未写完的目标文件，避免中途失败留下残留（独立审查发现的真实缺陷，已修复并补充回归测试）。`get_download()` 校验 `owner_id` 与当前 admin 一致（不一致或不存在统一 `40401`，不用 `40301`/`40302` 区分以避免暴露备份是否存在）、15 分钟懒过期（过期即删除文件并移出注册表）、路径解析后确实落在 `manual_backup_temp_dir` 内。`create()` 每次调用都会先清理注册表中已过期的条目。
- `cleanup_stale_manual_backups()`：应用启动时对 `manual_backup_temp_dir` 做目录级清理——由于注册表纯内存、进程重启即清空，任何仍在该目录下的 `*.db` 文件必然是上一次进程未走到 15 分钟过期就退出（如崩溃）留下的残留，可无条件删除；已接入 `backend/app/__main__.py::main()`，在 `run_startup_migrations` 之后执行。
- `backend/app/api/v1/system.py` 新增 `POST /api/v1/system/backups`、`GET /api/v1/system/backups/{id}/file`，均要求 `get_current_admin`；创建响应只含 `id`/`file_name`/`expires_at`，不返回内部路径；下载响应 `media_type="application/vnd.sqlite3"` 并设置安全 `Content-Disposition` 文件名。

### 设置与企业微信占位/整库备份界面（阶段 8，FE-07）

- `electron/src/renderer/src/views/SettingsView.vue`（新路由 `/settings`，`AppLayout.vue` 导航新增"个人设置"入口，所有登录用户可见）：三张卡片——自动归档开关（复用既有 `/settings/me` API，切换后离开页面再返回会重新拉取并保持已保存状态）、企业微信占位（按钮点击只触发本地 `ElMessage`提示"企业微信同步功能暂未开放"，不调用任何企业微信相关接口或 `shell.openExternal`）、`v-if="authStore.isAdmin"` 的管理员整库备份区（`ElMessageBox.confirm` 醒目二次确认，文案明确"备份文件包含全体用户的账号、日报和周报数据"）。管理员分支的显示只是 UX 优化，服务端 `get_current_admin` 独立强制权限。
- `electron/src/renderer/src/api/system.ts`：`createManualBackup()`/`downloadManualBackupFile()`，后者复用既有 `requestBinary()` 从 `Content-Disposition` 解析文件名。
- `electron/src/main/backup/file-saver.ts::BackupFileSaver`：结构上镜像阶段 6 已审查的 `ExportFileSaver`，但保持独立的类和白名单（文件名正则要求 `.db` 后缀、单独的 100MB 字节上限），不与导出共享同一校验器，避免任一方放宽白名单时意外影响另一方。`electron/src/main/ipc/register-runtime-bridge.ts` 新增 `backup:save-file` IPC channel，与既有 channel 一样先校验 `event.senderFrame === window.webContents.mainFrame`；`electron/src/preload/index.ts` 暴露 `window.runtimeBridge.backupFile.save(suggestedName, data)`。实际写入路径始终取自系统"另存为"对话框自身返回值。

### 生产模式 sidecar 环境变量注入（阶段 9，随 PKG-02/REL-01 发现并修复，ISS-014/SEC-010）

- `electron/src/main/sidecar/paths.ts::SidecarLaunchPlan` 新增 `env` 字段：开发分支为空对象（沿用仓库相对 `.local-data/` 默认值），生产分支由新增的 `productionDataDirEnv(userDataPath)` 计算 `WEEKLY_REPORT_{DATA,LOG,BACKUP,EXPORT_TEMP,MANUAL_BACKUP_TEMP}_DIR`（均在 `userDataPath` 下）与 `WEEKLY_REPORT_ENVIRONMENT=production`。`ResolveLaunchPlanOptions` 新增 `userDataPath` 字段。
- `manager.ts::doStart()` 把 `launchPlan.plan.env` 合并进子进程 `env`（在 `WEEKLY_REPORT_PORT`/运行期密钥之前，允许后两者始终覆盖）。`index.ts::getLaunchOptions()` 新增 `userDataPath: app.getPath('userData')`。
- 这是一个真实的、此前从未被验证过的生产路径缺口：此前生产 sidecar 会退回 `Settings` 的仓库相对默认值，PyInstaller 冻结后实际解析到安装目录内部，直接违反"安装目录只读"的安全边界；真实安装后首次启动会尝试写入只读目录而失败。已在 `paths.test.ts`/`manager.test.ts`/`manager.integration.test.ts` 补充/更新对应单元测试。

### PyInstaller onedir sidecar 构建（阶段 9，PKG-01）

- `backend/pyproject.toml` 新增 `[dependency-groups] build = ["pyinstaller==6.21.0"]`（独立于 `dev`，仅打包时需要），`backend/uv.lock` 同步更新。
- `backend/sidecar_entrypoint.py`：PyInstaller 入口包装（委托给 `app.__main__.main()`），确保 `backend/` 本身（而非仅 `app/`）落到 `sys.path`，与 `python -m app` 行为一致。
- `backend/weekly-report-backend.spec`：onedir 构建 spec，逐条注释记录每个 `collect_submodules`/`collect_all`/`excludes` 存在的真实原因（均由实际构建失败反推，非预先猜测）：`collect_submodules("alembic")`（过滤 `.testing`，否则 `ModuleNotFoundError: No module named 'alembic.op'` 且会带入整个 pytest/mypy）、`collect_submodules("sqlalchemy.dialects.sqlite")`/`collect_submodules("aiosqlite")`（SQLAlchemy URL scheme 动态派发，静态分析看不到）、`collect_all("argon2")`/`collect_all("_argon2_cffi_bindings")`（cffi 编译后端动态加载）、`collect_submodules("uvicorn")`、`excludes=["mypy", "pydantic.mypy"]`（`pyinstaller-hooks-contrib` 的 `hook-pydantic.py` 会无条件带入整个 mypy）、`EXE(..., contents_directory=".")`（PyInstaller ≥6.0 默认把非 exe 内容放进 `_internal/` 子目录，与 `migrate.py` 按 `sys.executable` 同级目录解析 `alembic.ini` 的假设冲突，恢复旧版扁平布局）。
- `backend/app/db/migrate.py`：新增 `_resolve_alembic_ini_path()`，`getattr(sys, "frozen", False)` 为真时相对 `sys.executable` 所在目录解析 `alembic.ini`，否则保持原 `__file__` 相对路径；`backend/tests/test_migrate_backup.py` 新增两条测试覆盖冻结/非冻结分支。
- 构建命令：`uv run --directory backend pyinstaller weekly-report-backend.spec --distpath ../build/_pyinstaller-dist --workpath ../build/_pyinstaller-work --noconfirm`，随后把 `build/_pyinstaller-dist/weekly-report-backend/*` 整体搬到 `build/sidecar/`（`weekly-report-backend.exe` 直接位于该目录顶层，匹配 `constants.ts::PROD_SIDECAR_EXECUTABLE_NAME` 和 `paths.ts` 的生产路径解析）；中间产物目录已加入根 `.gitignore`。
- 产物实测 42.69 MB / 148 个文件；把整个 `build/sidecar/` 复制到仓库外的临时目录，用清空至仅 `System32`/`System32\Wbem`/`Windows` 的 `PATH`（不含任何 Python/uv）直接启动 `weekly-report-backend.exe`：stdout 输出 `{"event":"sidecar_ready","port":<port>}`，`GET /health` 返回 `{"code":0,"msg":"success","data":{"status":"ok","version":"0.1.0"}}`，生成的 SQLite 库含全部 8 张业务表 + `alembic_version`；`taskkill /pid <cmd.exe pid> /t /f` 确认 PyInstaller 引导程序会再 fork 一层真正的工作进程，必须按进程树终止（与既有 Electron 侧的 `taskkill /t /f` 约定一致），验证后无残留进程。
- `build/sidecar/README.md` 占位说明已随真实产物落地删除。

### Playwright E2E 套件（阶段 9，QA-09）

- 新增真实、可复用的 E2E 基础设施（非一次性脚本）：`electron/playwright.config.ts`（`testDir: ./e2e`、`workers: 1`、`retries: 0`，未配置浏览器 `projects`，因为全部测试只驱动 Electron 本身，从不启动 Chromium/Firefox/WebKit）；`@playwright/test`、`playwright-core` 已作为正式 `electron/package.json` devDependencies 落地（随根 `package-lock.json` 一起提交，非临时 `--no-save` 安装）。
- `electron/e2e/helpers/app.ts`：`launchApp()`/`closeApp()` 用每测试独立的临时目录设置 `WEEKLY_REPORT_*_DIR` 环境变量隔离数据（从未触碰仓库 `.local-data/`），`closeApp()` 内含孤儿 sidecar 兜底清理（仅匹配本仓库 `backend/.venv` 解释器且父进程已不存在时才终止，不误杀无关进程）；`bootstrapAdmin`/`login`/`logout`、Element Plus 专用的 `formField`/`expectMessage`/`confirmMessageBox` 辅助函数；`stubSaveDialog()` 通过 `ElectronApplication.evaluate()` 在主进程上下文猴子补丁 `dialog.showSaveDialog`，避免导出/备份保存流程被真实原生对话框阻塞。
- 五个测试文件：`primary-path.spec.ts`（初始化→登录→新增并发布模板字段→创建/保存草稿/提交/归档日报→导出并校验磁盘上的真实 xlsx→生成周报→编辑三个自由文本区→保存→"查看来源日报"验证跳转回同一日报）、`auth-failures.spec.ts`（密码错误的清晰提示且表单不被清空）、`daily-validation.spec.ts`（必填字段留空的字段级 `42201` 错误与其余输入保留）、`admin-guard.spec.ts`（非管理员看不到"用户管理"导航和 `/settings` 备份区块，且强制访问 `#/admin/users` 会被路由守卫拦回 `/daily`）、`stale-version-conflict.spec.ts`（用真实 fetch 模拟并发编辑把版本从 1 推进到 2，再验证仍持旧版本的 UI 保存被 `40904` 拒绝而非静默覆盖，并在服务端二次核实版本和内容未被污染）。
- `npm run test:e2e`（根）→ `npm run test:e2e --workspace electron` → `npm run build && playwright test`：每次运行都先重新构建，保证测试的是当前源码而非过期产物。
- 排查并修复一处真实的测试竞态（不是隐藏起来，而是在文档中记录）：`page.waitForURL(/#\/daily\/.+/)` 这类宽松正则会被仍处于 `/daily/new` 创建表单页面的当前 URL 提前满足，导致拿到字面量 `"new"` 当作报告 ID；改为只匹配真实 ULID 形态的 `DAILY_DETAIL_URL_PATTERN`/`WEEKLY_DETAIL_URL_PATTERN` 后连续多次全量重跑无 flaky。

### Windows 安装包与真实发布验证（阶段 9，PKG-02/REL-01）

- `electron/electron-builder.yml` 的 `extraResources` 已把 `PKG-01` 产出的 `build/sidecar/` 整体复制到打包产物的 `resources/sidecar/`（不进 ASAR，`asarUnpack` 未包含它，`app.asar.unpacked` 内容仅有 `resources/icon.png`）。
- 真实执行 `npm run build:unpack`（`electron-builder --dir`）产出 `electron/dist/win-unpacked/`，直接启动其中的 `weekly-report.exe`（此时 `app.isPackaged` 为真、`is.dev` 为假，第一次真正走生产分支的 sidecar 路径解析），用 `--user-data-dir` 指向隔离临时目录，Playwright 驱动确认到达初始化界面、生成的 SQLite 库含全部 8 张业务表 + `alembic_version`——这是 `PKG-01`（sidecar 本体）、上一节的环境变量注入修复、以及打包结构三者第一次共同被验证。
- 真实执行 `npm run build:win`（`electron-builder --win --x64`）产出 NSIS 安装包 `weekly-report-0.1.0-setup.exe`（约 120 MB，`oneClick: true`、`perMachine: false`，即无 UAC、按当前用户安装）；`Get-AuthenticodeSignature` 确认安装包和内部可执行文件均为 `NotSigned`（V1 未购买签名证书，属已知、已记录风险，见 `issues.md` RISK-003）。
- 真实安装/升级/卸载验证在**当前开发机**上完成（未使用独立干净 Windows 虚拟机；该限制已在阶段开工前与用户明确确认并按用户选择的"在本机做深度真实验证"方案执行，而非仅做结构性检查）：
  - 安装：双击运行安装包，确认安装到 `%LOCALAPPDATA%\Programs\weekly-report-electron\`，桌面快捷方式与开始菜单项正确创建，注册表 `HKCU\...\Uninstall\{GUID}` 写入正确的 `DisplayName`/`DisplayVersion`/`UninstallString`/`QuietUninstallString`。
  - 真实使用：通过 UI Automation 驱动和 Playwright 两种方式分别验证（见下方缺陷记录），确认能正常引导首个管理员、登录、创建日报，数据落在真实 `%APPDATA%\weekly-report-electron\data\weekly-report.db`（而非安装目录），核对表结构与写入内容均正确。
  - 升级：对同一安装目录重新运行安装包（模拟版本升级的覆盖安装路径），确认重新安装前创建的管理员账号和日报记录在重新安装后依然存在且未被清空或覆盖。
  - 卸载：运行 `Uninstall weekly-report.exe`；使用 `QuietUninstallString`（`/currentuser /S`）能正确移除安装目录下的全部程序文件、桌面快捷方式和注册表项，且**用户数据目录 `%APPDATA%\weekly-report-electron\` 完全不受影响**，`data/weekly-report.db` 卸载后依然可读、内容不变——满足 `architecture.md` §7 "卸载不删用户数据"的目标要求。
- 过程中发现并修复三个真实缺陷（细节见 `issues.md` ISS-014/ISS-015/ISS-016）：① 生产 sidecar 未收到 `userData` 环境变量（已在上一节修复）；② 打包后主进程间歇性 `Cannot find module '@electron-toolkit/utils'`——用 5 次连续全新安装+启动和 1 次完整 Playwright 驱动反复确认修复后不再复现；③ npm workspace 作用域包名致使 NSIS 安装包完全无法生成、且早期一次安装产出功能上完全无效的空目录（已用 `${productFilename}` 与去作用域包名双重修复，重新验证正常）。另记录一项非阻塞观察（`ISS-017`）：直接调用非静默 `UninstallString` 在本环境表现为无操作，`QuietUninstallString`（Windows 现代"设置"应用的默认调用方式）验证正常；卸载后偶尔残留一个空安装目录（无文件、无数据影响，被系统索引进程短暂持有句柄）。

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

阶段 7 周报闭环当前工作树实际执行并通过：

- `uv run --directory backend ruff check .`、`ruff format --check .`：0 error，96 个文件格式合规。
- `uv run --directory backend mypy`（strict，96 个源文件）：0 错误。
- `uv run --directory backend pytest`：**169 项测试全部通过**（阶段 6 遗留 140 项 + 本阶段新增 29 项：周一校验/跨年周/闰周纯函数 7、周报 Service 直连测试 14——含并发同周唯一、乐观锁冲突、人工内容不反写日报、重生成整体覆盖、所有权 404、周报 API 测试 8——含互斥所有权隔离与 40903/40904/40001 错误码）。
- `npm run lint`、`npm run typecheck`：通过。
- `npm test`：**17 个文件 91 项测试全部通过**，新增周一定位/跨年周纯函数、`existing_weekly_report_id` 提取、周报字段展示格式化测试。
- `npm run test:integration --workspace electron`：真实后端进程 **2 项通过**，阶段 7 未破坏动态端口和退出清理链路。
- `npm run build`：main/preload/renderer 生产构建通过；仅有 `@vueuse/core` 第三方 PURE 注释位置提示（ISS-007 继续跟踪）。
- `git diff --check`：通过。
- 真实环境手动验证（`npm run dev` 真实启动 Electron + 真实后端，非测试替身）：进入 `/weekly` 自动定位到本周（任选一天自动吸附到周一）→逐日状态标签正确反映真实归档/草稿/无日报状态→点击生成→周报正确汇总已归档日报的字段内容→保存本周补充/下周计划/问题风险成功且版本递增→"查看来源日报"正确跳转到对应 `/daily/:id` 详情页→返回后列表页正确显示"查看本周周报"（不重复生成）→点击重新生成弹出醒目二次确认（危险态按钮+明确覆盖提示）→确认后生成时间/版本更新且此前保存的人工文本被清空重建。过程中发现并修复一处真实的时间显示缺陷：周报生成/更新时间原样展示服务端 UTC ISO 字符串，未转换为 `Asia/Shanghai` 显示；已复用现有 `formatShanghaiTime` 修正并通过同一真实环境复验。
- 独立安全专项审查（`security-review` 流程）：逐项核查所有权隔离（6 个接口的每条查询）、`replace_sources` 缺 owner 过滤但不可达越权路径、乐观锁 WHERE 条件是否同时锁定 `user_id`、`confirm_overwrite` 服务端强制校验、SQL 注入、XSS，未发现可利用漏洞。
- 主 Agent 自审：无跨层访问、无临时接口、日志/异常未见密码/JWT/密钥/完整正文；独立审查完成，阶段 7 无未解决 P0/P1。

阶段 8 设置能力与受控备份当前工作树实际执行并通过：

- `uv run --directory backend ruff check .`、`ruff format --check .`：0 error，100 个文件格式合规。
- `uv run --directory backend mypy`（strict，100 个源文件）：0 错误。
- `uv run --directory backend pytest`：**184 项测试全部通过**（阶段 7 遗留 169 项 + 本阶段新增 15 项：`test_backup_service.py` 9 项——生成有效 SQLite 快照、跨管理员下载被拒、懒过期删除、未知/越权 ID 拒绝、路径边界拒绝、创建时清理已过期条目、目的目录缺失的类型化失败、备份复制中途失败时清理残留文件、启动残留清理；`test_system_backup_api.py` 5 项——创建并下载、响应不含内部路径、非管理员 403、跨管理员 404、匿名 401；另有 1 项 MIME 常量断言）。
- `npm run lint`、`npm run typecheck`：通过。
- `npm test`：**18 个文件 107 项测试全部通过**（阶段 7 遗留 91 项 + 本阶段新增 16 项：`BackupFileSaver` 白名单/大小校验 12 项、`register-runtime-bridge` 新增 `backup:save-file` 受信任帧与 payload 校验 4 项）。
- `npm run test:integration --workspace electron`：真实后端进程 **2 项通过**，阶段 8 未破坏动态端口和退出清理链路。
- `npm run build`：main/preload/renderer 生产构建通过；仅有 `@vueuse/core` 第三方 PURE 注释位置提示（ISS-007 继续跟踪）。
- `git diff --check`：通过（仅常规 LF→CRLF 提示，无实际空白错误）。
- 真实环境手动验证：由于本阶段无法用鼠标/键盘人工操作 GUI，改用 Playwright `_electron` 驱动 `npm run build` 产出的真实 Electron 二进制（`node_modules/electron/dist/electron.exe`，从 `electron/` 目录以 `electron .` 方式启动，复现 `npm run dev` 的开发期路径解析），并通过环境变量将 `WEEKLY_REPORT_DATA_DIR`/`WEEKLY_REPORT_MANUAL_BACKUP_TEMP_DIR` 等指向隔离的临时目录（全程未读写仓库 `.local-data/`）。完整走通：首次初始化→登录→`/settings` 渲染三张卡片→切换自动归档开关后导航离开再返回，服务端 `GET /settings/me` 确认状态已持久化→点击企业微信占位按钮，全程网络请求日志确认零非回环（127.0.0.1 以外）请求，只弹出本地提示→点击整库备份触发醒目敏感性确认对话框→确认后调用真实 `POST /system/backups` + `GET /system/backups/{id}/file`，把下载字节交给（桩接管原生对话框返回固定路径的）`backup:save-file` IPC，磁盘上写入的文件已用 Python `sqlite3` 打开校验并核对表结构、且头 16 字节匹配标准 SQLite 文件头→再次创建备份并让保存对话框返回"已取消"，确认前端展示"已取消保存"→新建非管理员账号并以其身份登录，确认 `/settings` 页不出现"整库手动备份"区块且导航不出现"用户管理"。
- 独立安全专项审查（沙盒 Agent 全文审查 + 实际重跑质量门禁，不采信先前结果）：逐项核查管理员权限（`get_current_admin` 与既有末位管理员保护同一模式）、跨管理员越权隔离（40401 而非 40301/40302，避免暴露备份是否存在，与本文档其他资源的所有权隔离约定一致）、路径穿越（`backup_id` 从不参与文件路径拼接以外的用途，`_resolve_within_backup_dir` 提供纵深防御）、信息泄露（响应/日志均未出现内部路径、密钥或正文）、企业微信零外部请求（全文 grep 未发现任何网络请求或 `shell.openExternal` 路径）、Electron IPC 受信任帧校验和白名单契约。发现并修复一项真实问题：`BackupService.create()` 在 `sqlite3.Connection.backup()` 中途失败（如磁盘写满）时未清理已创建的目标文件，已加 `unlink(missing_ok=True)` 清理并补充回归测试（`test_create_removes_a_partially_written_file_when_the_backup_copy_fails`）；除此之外未发现可利用的 P0/P1。
- 主 Agent 自审：无跨层访问（手动备份按 `database.md` §6 设计有意跳过 Repository 层，Router 本身不含原始 SQL 或直接文件 I/O）、无临时接口、日志/异常未见密码/JWT/密钥/完整正文；独立审查完成，阶段 8 无未解决 P0/P1。

阶段 9 质量与发布当前工作树实际执行并通过：

- `uv run --directory backend ruff check .`、`ruff format --check .`：0 error，101 个文件格式合规。
- `uv run --directory backend mypy`（strict，100 个源文件）：0 错误。
- `uv run --directory backend pytest`：**186 项测试全部通过**（阶段 8 遗留 184 项 + 本阶段新增 2 项：`_resolve_alembic_ini_path` 冻结/非冻结分支）。
- `npm run lint`、`npm run typecheck`：通过。
- `npm test`：**18 个文件 108 项测试全部通过**（阶段 8 遗留 107 项 + 本阶段新增 1 项：`SidecarLaunchPlan.env` 生产环境变量注入）。
- `npm run test:integration --workspace electron`：真实后端进程 **2 项通过**，阶段 9 未破坏动态端口和退出清理链路。
- `npm run test:e2e`：Playwright **5 项测试全部通过**（详见上一节"Playwright E2E 套件"），连续多次重跑无 flaky。
- `npm run build`、`npm run build:unpack`、`npm run build:win`：均实际执行并成功产出 `electron/out/**`、`electron/dist/win-unpacked/**`、`electron/dist/weekly-report-0.1.0-setup.exe`。
- `git diff --check`：通过（仅常规 LF→CRLF 提示，无实际空白错误）。
- 真实 PyInstaller 构建与隔离环境冒烟、真实 electron-builder 打包、真实本机安装/升级/卸载全链路验证：详见上一节"PyInstaller onedir sidecar 构建"和"Windows 安装包与真实发布验证"，过程中发现并修复三个真实缺陷（`ISS-014`/`ISS-015`/`ISS-016`，含一个 P0：打包后主进程间歇性无法启动）。
- 独立审查：审查了本阶段全部代码改动（sidecar 环境变量注入、PyInstaller spec、`electron.vite.config.ts` 打包排除、`electron-builder.yml`/`package.json` 命名修复）与真实验证记录的一致性，重新执行本节列出的全部命令并复核结果；未发现未解决的 P0/P1。
- 主 Agent 自审：三个真实缺陷（含一个 P0）均已修复并经真实环境反复验证不再复现，而非仅理论修复；未在文档中记录任何未经真实执行验证的结果；诚实记录了本环境无法覆盖"独立干净虚拟机"这一 `REL-01` 原始验收条件的部分，并在动手前与用户确认了替代方案。

### 第二版迁移与认证基线（阶段 10A，BE-10A）

- 新增 Alembic revision `8b1d4e6f2a90`：创建 `daily_report_days`、`admin_audit_events`，增加 `users.must_change_password`，重建 `daily_reports`、`weekly_report_sources` 和 `user_settings`。升级前先预检 V1 周报 JSON，升级后显式核对日报/归档/周报来源行数并执行 `PRAGMA foreign_key_check`。
- V1 每篇日报一对一迁移为日期容器：ID 原样复用；旧草稿/已提交对应开放日期，旧归档对应带 `schema_version=2` 单来源正式快照。日报正文、模板快照、版本和时间保持不变。
- 既有周报的 `generated_content_json`、`content_json`、`source_snapshot_json` 均升级为 V2 日期/来源结构；当前周报 API 通过兼容解析器继续返回 V1 展示模型，BE-10C 再正式切换下游契约。有限 downgrade 会还原单来源周报 JSON；出现同日多条目、管理员审计或不可逆周报快照时明确拒绝。
- 首次初始化 API 已替换为 `POST /api/v1/system/bootstrap`：原子创建输入的普通用户和固定 `admin`，两份密码独立 Argon2id 哈希，双方默认设置/模板/模板版本在同一事务创建；普通用户名规范化后为 `admin` 时拒绝。
- 默认管理员 `must_change_password=true`；`/auth/me`、本人改密和登出在临时密码状态下可用，其余业务依赖统一返回 `40303`。本人改密清除标志并递增 Token 版本；管理员重置任意账号密码会重新设置强制改密。
- `auto_archive_on_submit` 已从模型、设置 API 和数据库移除，日报提交固定停在 `submitted`。为保持 BE-10A 阶段兼容，旧日报 API 暂时仍维持同日一篇，旧单篇归档会同时关闭日期并生成正式单来源快照；BE-10B 将替换为真正的同日多条目/日期级事务。
- 实际门禁：后端 Ruff、mypy、pytest 199 项、`git diff --check`；根工作区 lint、typecheck、Vitest 108 项和生产 build 均通过。

### 第二版日报聚合、管理员撤销与用户安全删除（阶段 10B，BE-10B）

- `backend/app/repositories/daily_report_day.py`（新增 `DailyReportDayRepository`）：`get_for_owner_by_date`/`list_month` 只读查询；`touch_open_for_write` 是日期行并发互斥的核心——对 `status='open'` 做条件 `UPDATE`，作为调用方事务内的第一条写语句提前抢占 SQLite 单写者锁，之后再读取当天条目即可保证不被并发创建/提交打断（`database.md` §8.2/ADR-016）；`finalize_archive` 完成状态翻转；`delete_if_empty_open` 供草稿删除后清理空日期容器。
- `backend/app/repositories/daily_report.py` 新增/替换：`get_by_client_request_id`、`list_by_day`、`insert_entry_if_day_open`（复用 `AUTH-01` 的 `INSERT ... SELECT ... WHERE EXISTS` 单语句模式，把"日期是否仍为 open"的判断折进插入语句本身，关闭创建与归档之间的竞态窗口）、`delete_draft`、`count_by_day`、`archive_entries`（批量把当天全部 `submitted` 条目翻为 `archived`）、`revoke_submission`、`list_submitted_awaiting_archive`/`get_submitted_metadata`（管理员专用，只做原始列选择，SQL 层面就不触碰 `content_json`/`template_snapshot_json`，返回 `AdminSubmittedEntry` dataclass）。移除了 V1 兼容桥的 `archive_submitted`/`archive_day`/`get_by_work_date`。
- `backend/app/services/daily_report.py::DailyReportService.create()`：先按 `client_request_id` 查已有条目，同用户同日期则幂等返回，跨日期/跨用户复用同一 key 返回 `40908`；否则获取或创建当天的 `DailyReportDay`（`UNIQUE(user_id, work_date)` 冲突时捕获 `IntegrityError` 重试，最多 3 次），再用 `insert_entry_if_day_open` 原子写入新草稿；日期已归档返回 `40905`。新增 `delete()`（仅 `draft` 可删，删除后若日期容器已无任何条目则一并清理该空 `open` 日期行）；`submit()` 保持不自动归档；旧的单篇 `archive()` 方法已删除。
- `backend/app/services/daily_report_day.py`（新增 `DailyReportDayService`）：`month_summary()` 逐日返回状态、草稿/已提交/归档计数、能否创建/归档及禁用原因（`disabled_reason`）；`get_detail()` 对开放日期返回条目列表，对已归档日期额外返回不可变 `archive_snapshot`（`build_day_archive_snapshot` 纯函数按 `submitted_at ASC, id ASC` 折叠全部已提交条目）；`archive()` 实现日期级归档事务——`touch_open_for_write` 抢锁复查 `open` → 读取当天条目 → 有草稿则 `40906`、无已提交条目则 `40907` → 构造快照、批量翻转条目为 `archived`、翻转日期容器为 `archived` 并写入 `source_count`/`archived_by`/`archived_at`；日期已归档时重复调用幂等返回既有结果而不改写归档时间（与 `api.md` §13.2 一致）。
- `backend/app/services/admin_daily_report.py`（新增 `AdminDailyReportService`）：`list_submitted()`/`revoke_submission()`/`list_audit_events()`。撤销要求 `{version,reason}`，条件 `UPDATE` 命中即把条目由 `submitted` 打回 `draft`（清空 `submitted_at`、版本 +1），同一事务写入 `admin_audit_events`（`action=daily_submission_revoked`，`metadata_json` 只含 `work_date` 白名单字段，正文/模板快照绝不写入）；所有者一侧 `GET /daily-reports/{id}` 通过 `DailyReportService.last_revocation()` 查询同一张审计表，向本人展示最近一次撤销原因和时间。
- `backend/app/services/user.py::UserService.delete_user()`：自我删除直接拒绝；确认用户名须与目标账号 `username` 精确一致（非规范化比较）；`has_business_records()` 检查 `daily_report_days`/`weekly_reports`/`export_jobs` 三张表（`daily_reports` 通过日期容器传递覆盖）；无业务记录时在同一事务内先删除 `user_settings`/`template_versions`/`report_templates` 脚手架数据，再对 `users` 做条件 `DELETE`（复用 `update_account` 同款末位有效管理员保护谓词）；末位管理员保护和业务记录检查均以数据库当前状态为准，且捕获检查后仍发生业务记录写入的并发场景（`IntegrityError` → `40910`，`ON DELETE RESTRICT` 兜底）。删除成功写入 `admin_audit_events`（`action=user_deleted`）。
- API 层新增/变更：`app/api/v1/daily_reports.py` 的 `POST`/`PATCH` 已改为要求 `client_request_id`，新增 `DELETE /daily-reports/{id}`，移除 `POST /daily-reports/{id}/archive`；新增 `app/api/v1/daily_report_days.py`（`GET ''`月历、`GET '/{work_date}'`详情、`POST '/{work_date}/archive'`）；新增 `app/api/v1/admin_daily_reports.py`（`GET /admin/daily-reports/submitted`、`POST /admin/daily-reports/{id}/revoke-submission`、`GET /admin/audit-events`）；`app/api/v1/users.py` 新增 `DELETE /users/{id}`。均已接入 `main.py` 并校验 `get_current_user`/`get_current_admin`。
- 已知范围边界（记录供 `BE-10C` 承接，非本阶段缺陷）：`WeeklyReportService`/`ExportService` 仍读取 `daily_reports.status=='archived'` 的条目级查询，尚未切换为按 `daily_report_days.archive_snapshot_json` 的日期级正式快照聚合；真实多条目日期归档后，周报/导出在同一日期出现多条 `archived` 条目时的聚合语义尚不正确（`weekly_report_sources` 按 `daily_report_day_id` 主键会与多来源写入冲突）。`test_exports_api.py`/`test_weekly_reports_api.py` 的 `_archive` 测试夹具已同步改为调用新的 `POST /daily-report-days/{work_date}/archive`，但覆盖场景仍是每日单条目，未验证多条目下游行为。
- 实际门禁：后端 `uv run ruff check .`、`ruff format --check .`、`mypy`（strict，115 个源文件）、`pytest`（**242 项通过**，阶段 10A 遗留 199 项 + 本阶段新增 43 项）均通过；根工作区 `npm run lint`、`npm run typecheck`、`npm test`（18 文件 108 项）、`npm run build` 作为回归检查全部通过（未修改任何 Electron/Vue 文件）；`git diff --check` 通过（仅 LF→CRLF 提示）。独立安全专项审查（沙盒 Agent 独立读取 diff）逐项核查所有权隔离、管理员正文泄露、SQL 注入、用户删除权限提升、确认/原因绕过、`client_request_id` 跨用户信息泄露、审计日志注入，未发现 P0/P1；识别一项低置信度（4/10）非漏洞信息项已记录不阻塞交付。实现提交 `784f96c` 已创建，阶段 10B 正式关闭。

### BE-10B 契约修正（提交 `c7ed342`，随 BE-10C 前置发现）

启动 BE-10C 前完整核对 `docs/方案设计.md` 第二版章节全文（此前 BE-10B 只依据 `ai-docs/api.md` 的精简摘要实现），发现并修正五处响应契约偏差，记为 ISS-023（已 RESOLVED）：

- 条目响应（`GET/POST/PATCH/submit /daily-reports...`）补齐 `day_id`。
- 创建接口响应补齐 `created`（幂等复用为 `false`，新建为 `true`）；`DailyReportService.create()` 相应改为返回 `(entry, created)` 元组。
- 月历摘要（`GET /daily-report-days?month=`）改为稀疏返回（只含存在 `daily_report_days` 记录的日期），字段 `disabled_reason` 更名 `archive_disabled_reason` 并补齐 `day_id`；日期详情接口同步改名。
- 用户列表/详情（`GET /users`、`GET /users/{id}`）补齐 `can_delete`/`cannot_delete_reason`；新增 `UserRepository.has_business_records_bulk()`/`count_active_admins()` 避免逐用户 N+1 查询。
- 撤销信息（`GET /daily-reports/{id}`）补齐 `last_revocation.actor_username`，复用既有 `admin_audit_events.actor_username_snapshot` 列，未新增数据库列。

新增/更新自动化测试覆盖以上字段，后端 244 项全部通过（阶段 10B 遗留 242 项 + 本次新增 2 项：用户列表删除资格三态、创建幂等 `created` 标记 —— 实际共新增/调整数项断言，完整门禁结果见下）。

### 第二版周报、导出与统计适配（阶段 10C，BE-10C）

- `backend/app/schemas/weekly_report.py`：`WeeklyDay` 从单一 `daily_report_id`+`fields` 改为 `daily_report_day_id`+`entries: list[WeeklyDayEntry]`（每个来源条目独立保留 `daily_report_id`/`submitted_at`/`fields`），结构与磁盘上 `schema_version=2` 的 JSON 形状一致，不再需要序列化/反序列化时的展平或分组转换。
- `backend/app/services/weekly_report.py`：`parse_weekly_content()` 移除了 V1 遗留的展平兼容分支（BE-10A 迁移已保证全部历史行是 `schema_version=2`，不再存在需要兼容的旧结构）；`build_weekly_content()` 改为接收 `list[DailyReportDay]`，对每天调用 `parse_day_archive_snapshot()` 解析其不可变正式快照，只保留每个来源条目自身模板快照中仍 `enabled` 的字段；`_serialize_weekly_content()` 直接从 `WeeklyContent` 序列化（不再需要额外的 `reports` 参数做 ID 反查）；`generate()`/`regenerate()` 改为查询 `DailyReportDayRepository.list_archived_in_range()`（日期级，替换原来的 `DailyReportRepository.list_owned_archived_by_range()` 条目级查询）；`_sources_for()` 一天一条 `WeeklyReportSource`（不再可能因同日多来源条目产生 `(weekly_report_id, daily_report_day_id)` 主键冲突）。`availability()` 逐日状态改为基于日期容器状态 + 当天条目构成推导（`archived`；`open` 时按是否存在草稿/已提交派生 `draft`/`submitted`/`None`），`archived_count`/`non_archived_dates` 相应改为按日期计数/去重，不再可能因同日多条目产生重复日期。
- `backend/app/repositories/weekly_report.py`：`WeeklySource.daily_report_id` 字段更名为 `daily_report_day_id`（此前字段名具有误导性——实际一直存的是 `day_id`）。
- `backend/app/schemas/export.py`：`ExportCreateRequest.report_ids` 更名 `daily_report_day_ids`（方案 §9.2）。
- `backend/app/services/export.py`：`_resolve_days()`/`plan_export_columns()`/`build_export_workbook()` 改为按 `daily_report_day_ids` 或日期范围过滤 `daily_report_days.status='archived'`，一日期一行；基础列新增"来源条目数"；新增 `_multi_source_cell()`——字段在单个日期的多篇来源中都有值时，按提交顺序渲染为 `[1] 值\n[2] 值`（保留来源边界，方案 §9.2），只有单一来源时保持原始类型（数字列不因合并逻辑被迫转成字符串）；`=` 公式注入防护（`SEC-006`）对每个来源值和合并后的整体文本值均生效。`ExportSelectionInvalidError.data` 的字段名同步改为 `invalid_daily_report_day_ids`。
- 新增 `backend/app/core/month_range.py::parse_month_range()`：从 `daily_report_days.py` 的私有 `_parse_month` 提炼为共享工具，供日历和统计两个接口复用，避免重复实现同一 `YYYY-MM` 解析/校验逻辑。
- 新增 `backend/app/services/statistics.py::StatisticsService`：`GET /api/v1/statistics/monthly?month=YYYY-MM`（新增 `backend/app/api/v1/statistics.py`）。`compute_effective_range()`（纯函数）按当前月/历史月/未来月返回不同的分母天数（当前月截至 Asia/Shanghai 今天、历史月为整月、未来月为 0）；`compute_completion_rate()`（纯函数）分母为 0 时返回 `None`（前端显示 `--`），否则四舍五入到小数点后一位；`compute_streak()`（纯函数）实现"今天已完成则从今天向前，今天未完成但昨天完成则从昨天向前，否则为 0"的连续天数规则，与所选月份无关，始终基于 Asia/Shanghai 今天计算。`daily_report_count` 统计工作日期在所选月且状态为 `submitted`/`archived` 的来源条目（新增 `DailyReportRepository.count_submitted_or_archived_in_range()`），日期级正式日报本身不重复计数；`weekly_report_count` 按 `week_start` 所在月统计（新增 `WeeklyReportRepository.count_by_week_start_range()`）；`days` 复用 `DailyReportDayService.month_summary()` 的稀疏月历摘要。
- 实际门禁：后端 `uv run ruff check .`、`ruff format --check .`、`mypy`（strict，123 个源文件）、`pytest`（**280 项通过**，阶段 10B 遗留 246 项 + 本阶段新增 34 项：完成率/有效范围/连续天数纯函数 14 项、统计服务直连测试 5 项——含跨用户隔离、统计 API 测试 5 项——含权限与月份格式校验、`parse_month_range` 纯函数测试 10 项——含独立安全审查发现的 `date.MAXYEAR` 边界回归）均通过；根工作区 `npm run lint`、`npm run typecheck`、`npm test`（18 文件 108 项）、`npm run build` 作为回归检查全部通过（未修改任何 Electron/Vue 文件，renderer 现有周报/导出代码仍是 V1 形状，适配是 `FE-10` 的既定范围）；`git diff --check` 通过（仅 LF→CRLF 提示）。
- 独立安全专项审查（沙盒 Agent 独立读取 diff）逐项核查所有权隔离（`WeeklyReportService`/`ExportService`/`StatisticsService` 全部新增/改写查询均按 `owner_id` 过滤）、导出 `daily_report_day_ids` 越权（跨用户/未归档/不存在统一归入同一错误列表，不区分具体原因）、统计跨用户泄露、SQL 注入、多来源单元格公式注入防护回归，未发现 P0/P1。发现并修复一项真实的低严重度问题：`app/core/month_range.py::parse_month_range()` 对 `9999-12`（`date.MAXYEAR` 的 12 月）会在 `try/except` 之外计算下月首日导致未捕获 `ValueError`（500 而非预期的 `40001`），已把该计算移入 `try` 块并补充 `tests/test_month_range.py`（10 项，含该回归场景）。
- 已知的 ISS-013（JWT 篡改测试偶发假阳性，与本次改动无关的历史遗留问题）在本阶段全量跑批中复现一次，单独重跑通过，不阻塞交付。

### 第二版 Electron/Vue 界面（阶段 10D，FE-10）

- 路由与守卫：新增 `/change-password`（仅 `must_change_password=true` 时可进入，否则重定向 `/daily`）、`/statistics`、`/admin/daily-reports`；`router/index.ts` 的 `beforeEach` 新增强制改密拦截，`api/client.ts` 新增 `onPasswordChangeRequired` 钩子在命中 `40303` 时兜底跳转；菜单改名为“我的日报/我的周报/统计/模板管理/设置”，新增“日报管理”“用户管理”两个仅 admin 可见入口；原 `AppLayout.vue` 头部的弹窗式改密已移除，改密统一收口到 `/settings`。
- 我的日报（`DailyListView.vue`）：改为月历（`el-calendar` 自定义 `date-cell`/`header` 插槽）+ 选中日期详情两栏布局，月历读取 `GET /daily-report-days?month=`，逐日状态由纯函数 `dayCellStatus()` 派生为 `none/draft/submitted/mixed/archived` 五态并同时用文字和色块表达（不仅靠颜色）；创建改为携带 `client_request_id`（`crypto.randomUUID()`，每次新建操作生成一次）；新增草稿删除（`DELETE /daily-reports/{id}`）；新增日期级归档按钮（禁用时用服务端返回的中文原因做 `el-tooltip` 提示）；归档后展示 `archive_snapshot.entries[]` 的多来源正式日报卡片，不再有单篇归档入口。导出入口也从旧列表页迁移到这里：页头“导出本月已归档日报”（按当前显示月的日期范围筛选归档日期）+ 归档日期面板的“导出当天正式日报”（单日期 `daily_report_day_ids`）；这一项在首次实现时被遗漏（旧列表视图整体替换为日历时未搬迁导出逻辑），在真实 Electron 冒烟验证阶段发现并当场补回，未产生独立提交。
- 日报详情（`DailyDetailView.vue`）：移除单篇归档按钮/逻辑（收口到日历页的日期级归档），新增草稿删除按钮和 `last_revocation`（管理员撤销原因/时间/操作者）提示；`40905`（日期已归档）统一提示并跳回日历。
- 我的周报（`WeeklyDetailView.vue`）：按日期卡片下改为渲染 `entries[]` 多个来源子卡片，来源跳转从 `/daily/{entry_id}` 改为 `/daily?date={work_date}`；`WeeklyListView.vue` 的可用性展示逻辑未变（后端状态枚举不变）。
- 统计页（新增 `StatisticsView.vue`，`/statistics`）：月历复用与“我的日报”一致的组件（只读，点击日期跳转 `/daily?date=...`），四张指标卡（完成率、已写日报、已写周报、当前连续记录），`completion_rate=null` 时显示 `--`（`formatCompletionRate()` 纯函数）。
- 管理员：新增 `AdminDailyReportsView.vue`（`/admin/daily-reports`，待归档条目最小元数据列表 + 撤销弹窗 + 审计记录筛选表格，均不展示任何正文字段）；`UsersView.vue` 新增删除按钮，`can_delete=false` 时按 `cannot_delete_reason` 展示中文提示并禁用，真正删除要求精确匹配原始用户名 + 填写原因。
- 设置页（`SettingsView.vue`）：移除“提交后自动归档”开关，新增“修改密码”卡片。
- 全局：`main.ts` 新增 `ElementPlus` 的 `zh-cn` locale 配置，避免新引入的 `el-calendar` 显示英文星期表头。
- 实际门禁：`npm run lint`（0 error/0 warning）、`npm run typecheck`、`npm test`（**22 个文件 125 项测试全部通过**，阶段 9 遗留 108 项 + 本阶段新增 17 项）、`npm run test:integration`（真实 sidecar，2 项）、`npm run build` 均实际执行并通过；`git diff --check` 通过（仅 LF→CRLF 提示）。后端本阶段未改动，沿用 `BE-10C` 280 项结果。
- 真实环境验证：用项目既有 Playwright `_electron` 驱动能力写了两次一次性冒烟脚本（隔离临时数据目录，未触碰仓库 `.local-data/`；验证后均已删除，未纳入正式套件）：① 主链路——完整走通双账号初始化→默认 `admin` 强制改密（导航栏在该页不可见）→改密后重新登录→日历创建/保存/提交→日期级归档并看到合并正式日报→生成周报确认来源内容展示→统计页无 `NaN`→设置页文案正确→管理员日报管理/用户管理页可用（自身账号删除按钮禁用，其他账号可用）；② 导出——单独验证“导出当天正式日报”“导出本月已归档日报”均生成合法 xlsx 文件并落盘（文件头 `PK\x03\x04`）。
- 安全审查：对本次实际改动的渲染进程文件做了聚焦安全检查（未使用 `security-review` 技能默认抓取的全分支历史 diff，因其包含此前阶段已审查过的无关代码），确认无 `v-html`/`innerHTML`/`eval`、无 `localStorage`/`sessionStorage` 写入、`el-tooltip` 的 `:content` 均未设置 `raw-content`、管理员页面字段与后端最小元数据类型逐一对应；未发现 P0/P1。如实记录：本次审查由主 Agent 直接执行，未像阶段 6/7/8/`BE-10B`/`BE-10C` 那样额外派发独立沙盒 Agent 复核。
- 已知非阻塞缺口：`electron/e2e/*.spec.ts` 五个既有 spec 仍是 V1 UI 断言，`npm run test:e2e` 现在会失败（例如 `bootstrapAdmin` 用的用户名 `'admin'` 现在会被保留用户名规则拒绝、页面标题“日报工作台”已改名），已记入 `issues.md` ISS-024，重写为 V2 形状是 `QA-10` 的既定范围，非本阶段回归。

### 第二版端到端验收（阶段 10E，QA-10）

- 后端/前端回归：backend `ruff`/`mypy`/`pytest`（280 项）与 electron `lint`/`typecheck`/`test`（125 项）/`test:integration`（2 项）均实际重新执行并通过；本阶段未改动后端或 renderer 业务代码，仅改动 `electron/e2e/`。`git diff --check` 通过。
- 迁移验收：核对 `backend/tests/test_v2_migration.py` 现有 4 个测试函数的覆盖范围（空库/真实 V1 结构副本升级、三态日报、多模板版本、跨年周与闰日、未来日期、导出任务、停用账号、周报 JSON V2 化、逐字节内容/模板保留、外键检查、无损 downgrade、同日多条目/审计事件拒绝 downgrade、坏 JSON 提前中止），确认已满足设计文档的迁移验收要求，未重复建设。
- E2E 套件全面重写为第二版形状：`electron/e2e/helpers/app.ts` 新增双账号专用 helper（`bootstrapFirstUser`/`completeForcedPasswordChange`/`bootstrapAndSignInAsAdmin`），移除只适用 V1 单账号模型的旧 helper；`primary-path.spec.ts` 扩写为覆盖设计文档要求的完整链路（双账号初始化→admin 强制改密含路由守卫绕过尝试→同日创建两篇→提交→admin 撤销→所有者重新提交→日期级归档→统计→周报→导出真实 xlsx）；其余 4 个既有 spec（`auth-failures`/`daily-validation`/`admin-guard`/`stale-version-conflict`）改为第二版 UI 文案与流程；新增 `user-deletion.spec.ts`。`npm run test:e2e` 连续 3 次全量重跑（6 个 spec）100% 通过，无 flaky。
- 生产打包与真实安装/升级/卸载验证（本机，无独立干净虚拟机，沿用阶段 9 `REL-01` 已获用户确认的方案，本次经用户在 `QA-10` 开工时再次明确同意）：重新执行 PyInstaller 产出全新 V2 sidecar（隔离 PATH 环境下启动验证，`/health` 正常，11 张表齐全）；重新执行 `electron-builder` 产出全新安装包；真实静默安装、真实使用（Playwright 直接驱动已安装二进制，双账号初始化→强制改密→日报创建/提交/归档→周报→统计全部通过）、模拟升级重装（数据完整保留）、真实卸载（程序文件/快捷方式/注册表项清除，用户数据库保留且可读）均已验证。过程中发现一个有价值的非缺陷现象（`ISS-025`）：生产环境下无法用环境变量隔离已打包二进制的数据目录（`SEC-010` 既定安全设计），这次意外触发的启动实际读写并成功迁移了阶段 9 遗留的真实 V1 数据库到第二版头版本——构成一次真实（非合成 fixture）的"已安装环境下 V1→V2 升级"验证。验证完成后已清理注入到真实 `%APPDATA%` 的测试数据。
- 本阶段未发现任何新的真实缺陷（对比阶段 9 `REL-01` 当时发现并修复的三个真实缺陷，其中一个 P0）；第二版打包配置未做任何修改，验证结果为对既有打包链路的完全兼容确认。
- `ISS-018`/`ISS-019`/`ISS-020`/`ISS-021`/`ISS-022`/`ISS-024` 均随本阶段端到端验收升级为 `RESOLVED`。CR-20260807-01 第二版增量（`REQ-10`→`DESIGN-10`→`BE-10A`→`BE-10B`→`BE-10C`→`FE-10`→`QA-10`）至此全部交付完毕。

## 3. 尚未实现

以下均为设计目标，当前不得标记为完成：

- CR-20260807-01 第二版增量的全部任务（`REQ-10`/`DESIGN-10`/`BE-10A`/`BE-10B`/`BE-10C`/`FE-10`/`QA-10`）均已完成，当前无第二版遗留待办。
- AI 周报生成仍为 P2，仅记录扩展边界；当前不得接入模型或保存模型密钥。

- Windows Job Object 级别的孤儿进程彻底防护（ISS-010，非阻塞）。
- 代码签名（安装包和 sidecar 均未签名，`Get-AuthenticodeSignature` 已确认；RISK-003）；正式多杀软兼容性矩阵测试（本机 Windows Defender 默认设置下未观测到拦截，但未做覆盖主流杀软厂商的系统性验证）。
- 独立干净虚拟机（而非当前开发机）上的安装/升级/卸载复测；本仓库未提供该环境，阶段 9 `REL-01` 已改为在本机做更深入的真实验证（含发现并修复三个真实缺陷）替代，该限制已在阶段开工前与用户确认。
- Element Plus 按需引入（ISS-007，非阻塞，构建体积优化）。

## 4. 当前运行方式

根 `npm run dev` 只启动 `electron-vite dev`；Electron Main 自行拉起并管理 FastAPI sidecar。sidecar 启动时会自动执行 `ensure_runtime_directories()` → `run_startup_migrations()`（首次运行即完成建表）→ 启动 Uvicorn。`dev:backend` 脚本仍保留，供脱离 Electron 单独调试后端时使用（需自行在 `.env` 设置 `WEEKLY_REPORT_RUNTIME_SECRET`，非 `test` 环境启动都会走同样的迁移检查）。

页面启动流程：窗口创建后立即显示，`App.vue` 先根据 sidecar 状态展示 `StartupView`（pending/failed）；ready 后恢复 safeStorage Token 并调用 `/auth/me` 校验，再按 bootstrap、登录和角色状态进入对应路由。

## 5. 下一检查点

CR-20260807-01 第二版增量已全部交付完毕（`REQ-10`→`DESIGN-10`→`BE-10A`→`BE-10B`→`BE-10C`→`FE-10`→`QA-10`）。当前没有已确认的下一个开发阶段；后续工作取决于用户提出的新范围（例如正式发布运营、代码签名、独立干净虚拟机复测，或新一轮需求变更），在收到明确指令前不得假设或提前实现。

阶段 10B（日报聚合、管理员撤销与用户安全删除）已实现、自测、质量门禁与独立安全审查通过，实现提交 `784f96c`（见上方"第二版日报聚合、管理员撤销与用户安全删除（阶段 10B，BE-10B）"一节），并随发现的契约偏差以修正提交 `c7ed342` 补齐（ISS-023）。阶段 10C（周报、导出与统计适配）已实现、自测、质量门禁与独立安全审查通过，实现提交 `6255755`（见上方"第二版周报、导出与统计适配（阶段 10C，BE-10C）"一节）。阶段 10D（Electron/Vue 界面，`FE-10`）已实现、自测、质量门禁与真实 Electron 冒烟验证通过，实现提交 `0ee2e8e`（见上方"第二版 Electron/Vue 界面（阶段 10D，FE-10）"一节）。阶段 10E（端到端验收，`QA-10`）已完成迁移/并发/权限/统计验收、E2E 套件重写与真实生产打包安装/升级/卸载验证，实现提交 `622154e`（见上方"第二版端到端验收（阶段 10E，QA-10）"一节）。

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
7. ✅ 独立审查（含专项安全审查）完成，发现并修复 Excel 公式注入与 CORS 文件名暴露两项真实问题，均已补充回归测试；无未解决 P0/P1。实现提交 `d6ab86e` 已创建，阶段 6 正式关闭。

阶段 7 四项任务已完成实现、自测、质量门禁、独立审查（含专项安全审查），统一为 `DONE`：

1. ✅ 自然周周一校验、仅归档日报参与生成、空周可生成、同周唯一（含并发）、来源快照可追溯已实现。
2. ✅ 人工编辑（本周补充/下周计划/问题风险）不反写日报、未显式确认不覆盖、确认后原子替换基线/内容/来源已实现。
3. ✅ 周报列表、周范围选择与逐日可用性展示、生成、编辑保存、来源跳转到日报详情、重新生成醒目覆盖确认已实现。
4. ✅ 后端 169 项、前端 91 项、真实 sidecar 集成 2 项及生产构建全部通过；真实 `npm run dev` 环境完成含生成/编辑/来源跳转/重新生成的全链路手动验证，过程中发现并修复时间显示未转换 `Asia/Shanghai` 的缺陷。
5. ✅ 独立审查（含专项安全审查）完成，逐项核查所有权隔离、`replace_sources` 可达性、乐观锁、确认绕过、SQL 注入与 XSS，均未发现可利用漏洞；无未解决 P0/P1。实现提交 `346b0ea` 已创建，阶段 7 正式关闭。

阶段 8 三项任务已完成实现、自测、质量门禁、独立审查（含专项安全审查），统一为 `DONE`：

1. ✅ admin 手动整库备份：checkpoint（`PRAGMA wal_checkpoint(TRUNCATE)`）+ `sqlite3.Connection.backup()` 一致性快照、进程内随机 ID 注册表（不落业务表）、15 分钟懒过期加启动残留清理、仅创建者本人可下载（跨管理员 40401）已实现。
2. ✅ `/settings` 页面：自动归档开关（持久化可复验）、企业微信占位（零外部请求，仅本地提示）、管理员整库备份创建与保存（醒目敏感性确认 + Electron 原生保存对话框白名单）已实现。
3. ✅ 后端 184 项、前端 107 项、真实 sidecar 集成 2 项及生产构建全部通过；用 Playwright `_electron` 驱动真实构建产物（隔离临时数据目录）完成含权限隔离、持久化、零外部请求和备份文件有效性校验的全链路验证。
4. ✅ 独立审查（含专项安全审查）完成，发现并修复备份复制中途失败遗留残留文件一项真实问题，已补充回归测试；无未解决 P0/P1。实现提交 `00caa33` 已创建，阶段 8 正式关闭。

阶段 9 四项任务已完成实现、自测、质量门禁、独立审查，统一为 `DONE`：

1. ✅ Playwright E2E：初始化→登录→模板→日报→导出→周报主链路及登录失败/字段校验/权限拒绝/乐观锁冲突四条失败路径已实现为可重复运行的正式测试套件（非一次性脚本），5 项全部通过且连续重跑无 flaky。
2. ✅ PyInstaller `onedir` sidecar：无 Python/uv 环境（剥离 PATH）可独立启动、迁移自动执行建表、许可证清单随包、产物不进 ASAR 均已实现并在真实隔离环境验证。
3. ✅ electron-builder Windows x64 安装包：`extraResources` 正确放置 sidecar、安装目录只读（sidecar 与主程序均不写安装目录）、`userData` 数据保留均已实现并验证。
4. ✅ 本机安装/升级/卸载全链路真实验证完成（含发现并修复三个真实缺陷，其中一个 P0）；独立干净虚拟机验证受限于当前环境，已提前与用户确认并记录该限制。
5. ✅ 后端 186 项、前端 108 项、真实 sidecar 集成 2 项、Playwright E2E 5 项及生产/打包构建全部通过；独立审查完成，无未解决 P0/P1。实现提交 `0148171`，阶段 9 正式关闭——V1 规划的全部 9 个阶段至此交付完毕。

## 6. 发布记录

对外发布的 GitHub Release（公开可下载的 Windows 安装包，区别于内部阶段提交）：<https://github.com/wanliqk/weekly-report/releases>

| 版本 | 标签提交 | 发布时间（UTC） | 说明 |
|---|---|---|---|
| `v0.1.0` | `0306cb3` | 2026-08-06T14:50:25Z | V1 首个正式版本：首次初始化/登录、用户管理、模板不可变版本、日报草稿-提交-归档（含提交后自动归档）、按自然周汇总周报、已归档日报导出 Excel、管理员整库手动备份、企业微信占位。安装包未签名。 |
| `v0.2.0` | `95bdbf0` | 2026-08-07T07:57:47Z | CR-20260807-01 第二版增量：双账号初始化（固定 `admin`）与首登强制改密、日报同日多篇与日期级归档（移除单篇归档与自动归档）、管理员撤销提交与操作审计、用户安全删除、周报/导出/统计改读日期级正式来源、新增"我的日报"月历与"统计"页。安装包未签名（沿用 `RISK-003`）。 |

发布流程：`package.json`/`electron/package.json`/`backend/pyproject.toml`/`backend/app/main.py` 的版本号需同步更新（`FastAPI(version=...)` 是 `/health` 版本号的单一来源），并重新执行 `uv lock` 和根 `npm install` 刷新锁文件；随后重建 PyInstaller sidecar 与 electron-builder 安装包，在本机做真实安装/启动/卸载冒烟后再创建 GitHub Release 并上传安装包资产。每个版本对应一个独立的 `chore(release): 发布 vX.Y.Z` 提交与同名 annotated tag。
