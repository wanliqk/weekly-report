# 当前开发进度

> 快照日期：2026-08-09
> 当前分支：`v1`
> 原则：本文件只记录当前工作树可验证的实现事实；设计目标不等于完成。

## 1. 总体状态

- 当前已完成阶段：阶段 1 工程基线、阶段 2 Desktop Bootstrap、阶段 3 数据基础与 API Foundation、阶段 4 认证与用户管理、阶段 5 模板、设置与日报闭环、阶段 6 查询导出与桌面保存、阶段 7 周报闭环、阶段 8 设置能力与受控备份、阶段 9 质量与发布。V1 规划的全部 9 个阶段均已交付。
- 已完成提交：`3a9fdbc`（工程基线）、`7386cae`（Desktop Bootstrap）、`8480515`（数据基础与 API Foundation）、`b6b1b47`（补充编码规则）、`1a50e75`（认证与用户管理）、`00e647f`（关闭阶段 4 并启动阶段 5 的状态文档）、`1d965fe`（模板、设置与日报闭环）、`d6ab86e`（查询导出与桌面保存）、`fd4df17`（关闭阶段 6 并回填提交号）、`346b0ea`（周报闭环）、`2584133`（关闭阶段 7 并回填提交号）、`00caa33`（设置能力与受控备份）、`0148171`（质量与发布）、`a866872`（第二版增量需求）、`e767ebd`（第二版技术方案）、`e86b88c`（第二版迁移与认证基线 BE-10A）、`784f96c`（日报聚合、管理员撤销与用户安全删除 BE-10B）、`5e33348`（回填 BE-10B 提交号）、`c7ed342`（BE-10B 契约修正 fix，见 ISS-023）。
- 当前所在阶段：CR-20260807-01 第二版增量已全部交付；CR-20260808-02 企业微信增量已完成 `WECOM-00..07`、诊断增强 `WECOM-07A` 及真实连接修复 `WECOM-07B`，下一任务为 `WECOM-08` 全链路验收与发布。
- 阶段 3 实现状态：`DB-01`、`DB-02`、`DB-03`、`API-01`、`QA-03` 均已实现、通过质量门禁并创建独立提交；独立 Reviewer 审查尚待补齐（非阻塞）。
- 阶段 4 实现状态：六项任务均已完成实现、自测、质量门禁、独立审查与提交 `1a50e75`，统一为 `DONE`。
- 阶段 5 实现状态：七项任务均已完成实现、自测、质量门禁、独立审查与提交 `1d965fe`，统一为 `DONE`。
- 阶段 6 实现状态：五项任务（`EXPORT-01`/`EXPORT-02`/`DESK-04`/`FE-05`/`QA-06`）均已完成实现、自测、质量门禁、独立审查（含专项安全审查）与提交 `d6ab86e`，统一为 `DONE`。
- 阶段 7 实现状态：四项任务（`WEEKLY-01`/`WEEKLY-02`/`FE-06`/`QA-07`）均已完成实现、自测、质量门禁、独立审查（含专项安全审查），统一为 `DONE`。
- 阶段 8 实现状态：三项任务（`BACKUP-01`/`FE-07`/`QA-08`）均已完成实现、自测、质量门禁、独立审查（含专项安全审查），统一为 `DONE`。
- 阶段 9 实现状态：四项任务（`QA-09`/`PKG-01`/`PKG-02`/`REL-01`）均已完成实现、自测、质量门禁、独立审查，统一为 `DONE`。真实安装/升级/卸载验证在本机（无独立干净虚拟机）完成，该限制已在阶段开工前与用户确认。
- 当前阻塞：无。企业微信 `ISS-031..034` 已随 `WECOM-07` 解决；扫码原生闪退/导航中断与当前 live 协议漂移 `ISS-035..036` 已随 `WECOM-07B` 解决并真实连接验证。`ISS-026` 在 `WECOM-08` 发布级验收前保持 `MITIGATED`，非官方协议长期风险 `ISS-027` 继续保持 `OPEN`。
- 第二版与企业微信实现事实：CR-20260807-01 的后端、Electron/Vue 与 QA 已全部完成；CR-20260808-02 已完成数据、凭证桥、协议 Client、Mapper、同步编排/API、Electron/Vue 交互、轮转诊断日志，以及一次开发态真实扫码连接/模板发现成功验证，`wecom_sync=true`。尚未完成的是 `WECOM-08` 的日报提交/重复对账、生产打包/安装升级、完整 E2E 和发布级验收。
- AI 上下文治理批次：12 份 `ai-docs/` 文档、启动路由和维护规则已完成交叉复核，随独立文档阶段提交交付；未混入后续阶段实现。
- 2026-08-08：应用户直接指令完成日报 Excel 导出排版增强（`PROD-021`）：新增 `backend/app/services/export_style.py` 封装标题/表头/边框/列宽/行高/冻结表头样式，`export.py` 的 `build_export_workbook` 改为写入 headers/data 后调用 `style_report_sheet()`；未改动列合并、公式防注入、多来源渲染等业务逻辑。因新增标题行，`test_export_service.py`/`test_exports_api.py` 中依赖固定行号的断言已同步更新（表头从 `rows[0]` 移到 `rows[1]`，数据从 `rows[1..]` 移到 `rows[2..]`）。已执行 `uv run ruff check .`、`uv run mypy`、`uv run pytest`（124 源文件、全量测试两次运行均 100% 通过，含一次单测 `test_expired_and_tampered_tokens_map_to_40102` 的偶发无关 flake，隔离重跑与全量重跑均通过，与本次改动无关）；未创建提交，等待用户确认。
- 2026-08-08：应用户直接指令新增模板字段类型 `PROJECT_LIST`（`PROD-022`），支持一篇日报登记多个项目各自的工作内容和完成状态，不修改数据库结构（`fields_json`/`content_json` 仍是既有 TEXT/JSON 列）。后端：`schemas/template.py` 的 `FieldType` 新增该字面量（模板发布沿用既有“非 select/multiselect 不得配置 options”规则，无需新增校验分支）；`schemas/daily_report.py` 新增 `ProjectListEntry`（`project`/`content`/`status` 三态固定枚举 `TODO`/`DOING`/`DONE`）并入 `DailyFieldValue` 联合（已用 `TypeAdapter` 实测 Pydantic smart-union 能按列表元素类型正确区分 `multiselect` 与本类型，无需判别字段）；`services/daily_report.py` 的 `_project_list_error()` 校验每个条目的 `project`/`content` 非空、`status` 合法、字段无缺失/多余，且同时兼容 `save()` 传入的原始 dict 与 `submit()` 经 `parse_daily_content()` 重新解析后的 `ProjectListEntry` 模型两种形态（实现时曾遗漏后一种形态导致 submit 阶段误报“字段不完整”，已修正并由 `test_project_list_field_submits_and_archives_with_multiple_entries` 覆盖该回归）；`services/export.py` 的 `_single_source_cell()` 按列表首元素类型分流到新增的 `_format_project_list()`，按项目分组渲染为 `项目:X\n- 内容`（用半角冒号而非全角冒号，因全角冒号会触发 Ruff `RUF001` 全角标点检测且仓库此前无任何 `noqa` 先例），不显示完成状态，且因固定前缀不以 `=` 开头而天然免疫公式注入（无需依赖 `_defuse_formula` 的转义，仍保留调用以防未来格式调整）。前端：`types/template.ts`/`types/daily-report.ts` 新增类型；`utils/template-fields.ts` 新增 `projectTaskStatusLabel`/`isProjectListArray`/`formatProjectListEntries` 共享辅助并被 `daily-form.ts`/`weekly-report.ts` 复用；`DynamicFieldInput.vue` 新增可动态增删的项目/内容/状态三列编辑区（沿用 `updateXxx(value: unknown)` 具名函数处理 `@update:model-value` 的既有风格，未使用模板内联类型化箭头函数，因仓库此前无该写法先例）；`TemplatesView.vue` 字段类型下拉新增“项目列表”。测试：后端新增 22 项（模板发布、内容校验的 6 种非法形态、必填空列表拒绝提交、保存/提交/归档往返、导出分组渲染/多来源编号/无需转义即免疫公式注入），前端新增 7 项（`emptyFieldValue`/`usesOptions`/`isProjectListArray`/`formatProjectListEntries`/`projectTaskStatusLabel`/`formatDailyFieldValue`/`formatWeeklyFieldValue`/`initializeDailyContent` 深拷贝）。实际门禁：后端 `uv run ruff check .`（通过）、`uv run ruff format --check .`（除本次改动外，`app/services/export_style.py` 存在一项与本次改动无关的既有格式漂移，未改动该文件）、`uv run mypy`（strict，124 源文件，通过）、`uv run pytest`（JUnit XML 确认 **302 项、0 失败、0 错误、0 跳过**，含阶段 10C/QA-10 遗留 280 项）均实际执行并通过；前端 `npm run lint`（0 error/0 warning，修复中途 `eslint --fix` 顺带格式化了未改动的 `electron/src/main/index.ts` 的一处预先存在的空行警告，已用 `git show HEAD:... | tr -d '\r'` 逐字节核对还原为改动前内容，`cmp` 确认与 HEAD 完全一致，不计入本次改动）、`npm run typecheck`、`npm test`（**22 文件 132 项全部通过**，较改动前 125 项净增 7 项）、`npm run build` 均实际执行并通过。已知非阻塞：`electron/src/main/index.ts` 第 51 行存在一处与本次改动无关的既有 prettier 空行警告（HEAD 提交已如此，`npm run lint` 的 `--max-warnings=0` 因此在改动前就会失败），本次未修复以保持提交范围聚焦。已随提交 `7ce6928` 交付。
- 2026-08-08：用户反馈 `PROD-022` 首版导出格式（单元格内“项目:X\n- 内容”分组文本）不符合预期，要求改为真正的二维表（动态表头、每项目一行、保持现有表头加粗/边框/自动换行/自动列宽样式、不影响其他字段类型）；因“一个字段值渲染成多行多列的表”与既有“一天一行”的主表模型结构性冲突，落地前用 `AskUserQuestion` 确认了两种可行布局（主表下方按日期分块 vs. 独立工作表），用户选择前者。已实现并记为 `PROD-023`：`export.py::plan_export_columns` 新增 `include` 过滤谓词，主表列用 `field_type != "PROJECT_LIST"`、块规划用 `field_type == "PROJECT_LIST"`（两者复用同一套顺序/去重/消歧逻辑）；`build_export_workbook` 对每个「已归档日期 × PROJECT_LIST 字段」组合（若该组合下所有来源条目累计至少一条目）在主表下方追加：空行 + 标题行（`{日期} {责任人} · {字段标签}`）+ 固定表头行（项目/工作内容/完成状态）+ 逐条目数据行，多来源条目按提交顺序直接展平为连续行（不做 `[N]` 来源编号，不按项目名合并，因合并会在新增的“完成状态”列上产生冲突）；`项目`/`工作内容`现在是独立单元格，改为各自调用 `_defuse_formula()`（不再依赖旧版单元格前缀“天然免疫”公式注入的特性）；`export_style.py` 新增 `ProjectListBlockLayout` 与 `_style_block_title()`，`style_report_sheet()` 新增 `project_list_blocks` 参数，复用既有表头/表体样式函数为每个分块单独打表头加粗+边框+自动换行，并把列宽自适应改为跨"主表+全部分块"行范围与列数的统一一次性计算（因为分块的 3 列复用主表最左侧列字母）。用一次性脚本对生成的真实 xlsx 做了程序化验证（超出自动化测试断言范围，人工确认）：分块表头 `bold=True`/`fill=FF1F3864`/`border=thin`，数据行 `wrap_text=True`/`border=thin`，标题行 `bold=True`，列宽按内容自适应（示例中 A=31/B=21/C=12），`freeze_panes` 仍锚定主表首个数据行未被分块影响。测试：删除原先 3 个针对单元格分组渲染/`[N]` 编号的测试，新增 4 个针对分块表结构的测试（主表不含该字段列+分块标题/表头/数据行/总行数、项目与内容各自独立转义、多来源展平不加编号、空列表日期不生成分块且分块顺序跟随主表日期顺序），新增 `_row_values()` 测试辅助函数按行读取并裁剪 `sheet.max_column` 因分块 3 列而对更窄主表行产生的尾部 `None` 填充。实际门禁：`uv run ruff check .`、`uv run ruff format .`（仅重排本次改动引入的 2 处超长行，未改动 `export_style.py` 中与本次无关的既有格式漂移之外的内容）、`uv run mypy`（strict，124 源文件）均通过；`uv run pytest`（JUnit XML 确认 **303 项、0 失败、0 错误、0 跳过**）通过。未改动前端（本次改动完全在导出渲染的后端实现内）。已随提交 `47c1f4b` 交付。
- 2026-08-08：用户第二次反馈导出布局（`PROD-023` 的“主表下方分块”）仍不符合预期，改为给出具体表格示例和 7 条编号要求：日期/责任人/明日工作计划按项目数纵向合并、项目明细每项目一行、日级字段不重复、保持现有样式、"使用 POI 合并单元格功能实现"、处理项目数为 1/为空两种边界。已实现并记为 `PROD-024`，取代 `PROD-023`：因需求原文的“POI”是 Java 生态工具，与本仓库 Python/FastAPI + openpyxl 技术栈不符，已在实现前向用户简要说明并按功能等价改用 openpyxl 的 `sheet.merge_cells()`（继续遵循 `AGENTS.md` 的技术栈约束，未引入 Java/POI 依赖）。`export.py::plan_export_columns` 改回单一顺序列表（移除 `PROD-023` 引入的 `include` 过滤谓词），新增 `field_type` 字段供调用方判断如何渲染；新增 `_plan_column_layout()` 按字段原有顺序原地展开——`PROJECT_LIST` 字段展开为“项目/工作内容/进度”3 列表头，其余字段各占 1 列，返回日级列索引、常规字段列索引、`PROJECT_LIST` 三元组列索引三份映射；`build_export_workbook` 按天计算 `row_count = max(1, 各 PROJECT_LIST 字段当天条目数)`，仅在该天第一行写入日期/责任人/常规字段值，`row_count > 1` 时对每个日级列调用 `sheet.merge_cells()` 纵向合并到最后一行；`PROJECT_LIST` 列逐行填入各自条目（不足的行留空，不合并）。已用一次性脚本验证 openpyxl 行为细节：在合并区域的非锚点 `MergedCell` 上设置 `.font`/`.alignment`/`.border` 是安全的（只有 `.value` 赋值会报错），因此"先写值+合并、`style_report_sheet()` 统一后处理样式"的既有顺序不需要改变；并程序化核对了生成的真实 xlsx——表头 6 列全部 `bold=True`/`fill=FF1F3864`，合并单元格 `A3:A4`/`B3:B4`/`F3:F4` 与预期完全一致，列宽自适应、`freeze_panes` 均未受影响。`export_style.py` 随之移除 `PROD-023` 引入的 `ProjectListBlockLayout`/`_style_block_title`/`project_list_blocks` 参数，`style_report_sheet()` 恢复为单一表头+表体的简单形态。测试：删除原先 4 个针对分块表结构的测试，新增 6 个针对内联合并单元格布局的测试（多项目纵向合并主表其余列且明细列不合并、单项目不合并、空列表不合并且明细列留空、多来源展平后仍正确合并、项目与内容各自独立转义、两天各自独立展开且互不影响彼此的合并范围），并修正测试辅助函数 `_row_values()`——移除了 `PROD-023` 版本"裁剪尾部 None"的逻辑（该逻辑在合并单元格布局下会误裁剪掉合并产生的合法尾部空值，已用真实断言失败复现并定位），改为如实返回整行。实际门禁：`uv run ruff check .`、`uv run ruff format --check .`（仅 `app/services/export_style.py` 存在一项与本次改动无关、且与前两轮记录相同的既有格式漂移，本次改动涉及的代码本身已格式化，未改动该无关部分）、`uv run mypy`（strict，124 源文件）均通过；`uv run pytest`（JUnit XML 确认 **305 项、0 失败、0 错误、0 跳过**）通过。未改动前端。已随提交 `150d20f` 交付。
- 2026-08-08：应用户直接指令将默认模板核心字段 `今日工作内容` 的默认 `required` 从 `true` 改为 `false`（记为 `PROD-025`），理由是配置了 `PROJECT_LIST` 字段后再强制要求填写单独的 `今日工作内容` 属于冗余。只改动 `backend/app/services/user.py::default_template_fields()` 一处默认值；`今日工作内容` 仍是 `core_type="today_work"` 核心字段（不可删除、仍计入“至少启用一个核心字段”规则），`明日工作计划` 的 `required: true` 不变；`services/template.py` 的模板发布校验从未锁定核心字段的 `required`（该字段本就由请求方自由设置），故无需新增校验分支。已确认此改动只影响新引导账号（首次初始化的双账号、管理员之后新建的用户）的默认模板，已发布的历史模板版本不可变、不受影响。测试：`test_daily_reports_api.py::test_submit_validates_required_fields_and_preserves_draft_on_failure` 原断言“空草稿提交产生 2 个必填错误”已改为断言仅 `明日工作计划`（按 `core_type` 动态定位其 `field_key`，不再假设固定顺序）报错；核对了 `_default_content()` 的其余全部调用点均为动态计算、非硬编码字段数量，无需改动；`test_bootstrap_service.py`/`test_templates_api.py` 中涉及默认模板的断言只检查 `core_type`，不检查 `required`，未受影响。实际门禁：`uv run ruff check .`、`uv run ruff format --check .`（涉及文件均已格式化）、`uv run mypy`（strict，124 源文件）均通过；`uv run pytest`（JUnit XML 确认 **305 项、0 失败、0 错误、0 跳过**）通过。未改动前端（模板编辑器的“必填”开关本就对所有字段通用生效，无需特化；`SetupView.vue` 的引导文案只列出两个默认字段名称，未声称其必填性）。已随提交 `70cdd85` 交付。
- 2026-08-08：应用户直接指令把导出 Excel 的基础列 `责任人` 从第 2 列移到最后一列（记为 `PROD-026`），`日期` 保持第 1 列，模板字段列整体前移。`export.py::_ColumnLayout` 新增 `owner_column` 字段（1-based，恒等于表头总数）；`_plan_column_layout()` 改为先放 `日期`（列 1），逐个展开模板字段列（`PROJECT_LIST` 仍展开为“项目/工作内容/进度”3 列），最后追加 `责任人` 并计算其真实列号；`build_export_workbook()` 的写值逻辑从硬编码 `row[1] = owner_username` 改为 `row[layout.owner_column - 1] = owner_username`；`责任人` 仍属于 `PROD-024` 的“日级列”合并集合，多项目时随 `日期`/其余常规字段一起纵向合并，行为逻辑（合并、多来源 `[N]` 编号、公式转义）完全不变，只是列位置改变。用一次性脚本核对了真实生成的 xlsx：表头/数据行/合并范围（`A3:A4`/`E3:E4` 明日工作计划/`F3:F4` 责任人）均与预期一致。测试：更新了 `test_export_service.py` 中 9 个因列顺序断言而失败的既有测试（含 `PROD-024` 阶段新增的合并单元格测试）和 `test_exports_api.py` 中 1 个真实走 API 全链路的测试，将 `_BASE_HEADERS` 替换为独立的 `_DATE_HEADER`/`_OWNER_HEADER` 常量（不再是相邻的固定二元组）；未新增测试用例，因为这是既有维度（列顺序）的位置调整而非新行为。实际门禁：`uv run ruff check .`、`uv run ruff format --check .`（仅 `app/services/export_style.py` 存在与本次无关、此前三轮均已记录过的既有格式漂移）、`uv run mypy`（strict，124 源文件）均通过；`uv run pytest`（JUnit XML 确认 **305 项、0 失败、0 错误、0 跳过**）通过。未改动前端。未创建提交，等待用户确认。

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

## 7. 企业微信同步文档阶段（CR-20260808-02，WECOM-01）

- 2026-08-08：已读取当前日报日期级正式快照、Model/Service/Controller/Repository/数据库契约，并分析用户提供的 `wx-ribao.py` 及真实 HTTP 样例的登录、Cookie、模板/列表/提交请求和响应结构；分析过程未把真实 Cookie、账号标识或日报正文写入文档。
- 正式文档已新增第三版需求和技术方案：只手动同步本人已归档正式日报；Electron Main 安全登录 + `safeStorage` Cookie jar；FastAPI Mapper/Sync Service/内部协议 Client；三张非敏感元数据表；Main-only secret；动态字段映射；`uncertain` 保守重试语义。
- `ai-docs` 已同步需求、架构、模块、数据库、API、决策、风险和 `WECOM-00..08` 任务。`WECOM-01` 仅交付文档，没有修改后端/前端/数据库、依赖、能力开关或原始资料，也没有发起企业微信网络请求。
- 当前实现事实仍是 `wecom_sync=false` 和设置页占位。下一步必须先做 `WECOM-00` 敏感样例治理，再进入数据或登录实现。

## 8. 企业微信敏感样例治理（WECOM-00，ISS-028）

- 2026-08-08：根 `.gitignore` 新增精确规则 `backend/wx-ribao/`，把用户提供的真实参考脚本 `wx-ribao.py`（含硬编码的真实表单地址/`journaluuid`）和真实抓包 `http_raw_request.txt`/`http_raw_response.txt` 整目录排除；`git status --short`/`git status --ignored --short` 已验证该目录从 `??`（未跟踪）变为 `!!`（已忽略），原始文件本身未被修改或暂存。
- 新增 `backend/tests/fixtures/wecom/`：`get_template_combine_info_response.json`、`get_journal_list_response.json`、`answer_page_request.http`、`answer_page_response.json` 四份全合成 fixture，覆盖 `docs/方案设计.md` §2.4 记录的三个内部接口；Cookie 值、`sid`/`vid`/`uid`、`form_id`/`template_id`/`journaluuid`、人名、公司名、头像域名和日报正文全部替换为 `SYNTHETIC-*`/虚构占位符，仅保留题目标签（"日期"/"今日工作"等通用模板文案）和字段名等非识别性协议形状；随附 `README.md` 按文件逐一标注与真实抓包的置信度关系（`get_journal_list` 无真实抓包可比对，标注为低置信度，留给 `WECOM-04` 在受控测试账号上复核）。
- 新增 `backend/tests/test_wecom_fixture_hygiene.py` 作为可复跑的敏感扫描：仅当本机存在 `backend/wx-ribao/` 时才动态提取其中的 Cookie 值、`create_name`/`reply_name`/`user_name`/`avatar`/`text_reply`/`form_id`/`template_id`/`journaluuid` 等敏感字段取值和脚本硬编码 URL 分量，断言 fixture 目录不包含任何一个；目录不存在时安全跳过（不影响其他机器/CI）。用正向对照验证过扫描逻辑真实生效：临时向 fixture 文本注入真实样例中出现的一个真实姓名后重跑会被正确检出为 1 项泄漏，证明该测试不是空跑通过（验证后未落盘，本文档不记录具体姓名）。
- 实际门禁：`uv run ruff check .`（含新文件，0 error）、`uv run mypy`（strict，**125 个源文件**，较 `QA-10` 收尾的 123 个新增 2 个）均通过；`uv run pytest`（**306 项收集**，含新增 1 项 `test_wecom_fixture_hygiene.py`）在无 pipe 截断的直接重定向运行下**全部通过、exit code 0**。过程中两次全量跑批复现已知的 `ISS-013`（`test_expired_and_tampered_tokens_map_to_40102` 偶发假阳性，因随机 JWT 签名翻转末位字符不总改变解码字节），单独重跑 `test_auth_api.py` 立即 8 项全部通过；本阶段未改动任何 JWT/认证代码，与该已知非阻塞问题无关。`git diff --check` 通过（仅 LF→CRLF 提示）；`git status --short` 只显示 `.gitignore` 改动与两个新增路径，`backend/wx-ribao/` 不再出现。
- 顺带发现一项与本阶段无关的预置格式漂移：`uv run ruff format --check .` 报告 `app/services/export_style.py` 需要重新格式化（该文件本次会话未改动，`git status` 确认工作树干净，漂移应来自更早提交未跑 format 门禁）；判断为超出 `WECOM-00` 范围的独立小问题，未顺手修改以避免把无关改动混入本阶段提交，已记入 `issues.md`（`ISS-029`，P3，非阻塞）。
- `backend/tests/fixtures/wecom/` 目前只是数据文件，尚未接入任何 Client/Mapper 代码（`WECOM-02..04` 仍是 `TODO`）；不得把 fixture 存在等同于协议 Client 或数据基础已实现。

## 9. 企业微信数据基础与登录凭证桥（WECOM-02/WECOM-03）

- 2026-08-08：`WECOM-02`（backend 数据基础）与 `WECOM-03`（Electron 登录与凭证桥）依赖均只是 `WECOM-00`/`WECOM-01`、文件范围完全不重叠（`backend/**` vs `electron/**`），按两个 Agent 并行实现，主 Agent 复核两份 diff 并统一运行合并后的全量门禁、同步文档、创建独立提交。
- `WECOM-02`：新增 `wecom_user_bindings`/`wecom_sync_profiles`/`wecom_daily_sync_records` 三张 ORM 表（迁移 `f19f6d677a36`，`down_revision=8b1d4e6f2a90`）、对应 Repository、`app/schemas/wecom.py` 的三个 Pydantic 配置契约（`WeComQuestionMappingConfig`/`WeComRecipientConfig`/`WeComFieldMappingConfig`，`schema_version` 均为无默认值 `Literal[1]`）。字段设计已与 `docs/方案设计.md` §6 逐项核对；`last_error_kind` 刻意不加 CHECK 白名单，留给尚未实现的 `WECOM-04/06` 决定该枚举的最终取值集合。这一步只是数据层（Model/Repository/Schema/Migration），不含 Service、API Router、企业微信协议 Client。
- `WECOM-03`：新增 `WeComCredentialStore`（`safeStorage` 加密、随机 `credential_slot` 定位、无明文回退）、`WeComAuthWindowController`（隔离 session partition、精确主机名导航白名单、轮询 `wedoc_sid` Cookie 判定登录完成而非固定等待）、`WeComBridgeClient`（按 §9.2 请求形状实现的骨架，调用尚不存在的 `/api/v1/internal/wecom/**` 会得到 404，这是记录在案的范围边界）、`register-wecom-bridge.ts`（`connect`/`disconnect`/`executeSync` 三个窄 IPC）；独立生成的 `main_bridge_secret` 随 sidecar 子进程环境变量下发并接入既有日志脱敏机制，刻意不接入任何 IPC handler。
- 详细设计决策、字段级核对结果和验证记录见 `ai-docs/task.md` 的"WECOM-02/WECOM-03 验证记录"小节，不在此重复。
- 合并后实际门禁（主 Agent 重新执行，未只信任两个 Agent 各自的门禁结果）：后端 `uv run ruff check .`、`uv run mypy`（strict，**132 个源文件**）通过，`uv run pytest -q`（**342 项收集，0 failure/0 error**，`--junit-xml` 确认）；前端 `npm run lint`、`npm run typecheck`、`npm test`（**26 文件 192 项**）、`npm run build` 均通过；主 Agent 独立复核构建产物未发现 Main-only 密钥/Cookie 相关字符串泄露到 `preload`/`renderer`。`git diff --check` 通过（仅 LF→CRLF 提示）。
- 当前实现事实：企业微信数据层和 Electron 凭证桥骨架已存在，但公开/Main-only API、企业微信协议 Client、字段映射 Mapper、同步编排 Service 均未实现，产品仍是 `wecom_sync=false` 占位。下一步是 `WECOM-04`（内部协议 Client）和 `WECOM-05`（字段映射与预览），依赖已满足，可并行。

## 10. 企业微信协议 Client 与字段映射（WECOM-04/WECOM-05）

- 2026-08-08：`WECOM-04`（内部协议 Client）与 `WECOM-05`（字段映射与预览）依赖分别是 `WECOM-00`/`WECOM-02`/`WECOM-03` 和 `WECOM-02`、互不依赖，文件范围完全不重叠，唯一共享风险点是 `backend/pyproject.toml`/`uv.lock`（只有 `WECOM-04` 需要改，把 `httpx` 迁移为生产依赖），已要求尽早一次性完成以降低两个 Agent 共享同一 `backend/.venv` 的环境竞态窗口；按此拆分并行实现，主 Agent 复核两份 diff 并统一运行合并后的全量门禁、同步文档、创建独立提交。
- `WECOM-04`：新增 `app/integrations/wecom/`（`client.py`/`schemas.py`）。`WeComInternalClient` 的 base URL 硬编码 `doc.weixin.qq.com`（非构造参数，每次请求前二次校验，防 SSRF）、`follow_redirects=False`、六个分类异常（`WeComAuthExpired`/`WeComSchemaChanged`/`WeComBusinessRejected`/`WeComProtocolChanged`/`WeComTransportFailed`/`WeComOutcomeUncertain`）、`select_cookie_header()` 按 RFC 6265 规则筛选、multipart 提交用 httpx 惯用法强制随机边界。过程中发现并修复一个真实的测试环境陷阱：Alembic `env.py` 的 `logging.config.fileConfig(disable_existing_loggers=True)` 会在测试跨文件运行时把 Client 自己的 logger 标记为 disabled，导致 `caplog` 收不到日志脱敏断言需要的记录，已在测试内保存/强制启用/还原该标志规避。
- `WECOM-05`：新增 `app/services/wecom_mapper.py`。严格按 §7.1 四条优先级路由（`PROJECT_LIST` 优先于 `core_type`），解决了"责任人"的表述歧义（`ProjectListEntry` 没有责任人子字段，按普通自定义字段处理）并**反向修正了 `docs/方案设计.md` §7.2` 的示例文本**（移除易被误读的"每项目一个责任人"示例行，冒号统一改为半角以匹配仓库全部 Python 源码零例外遵守的 Ruff `RUF001`/`RUF002`/`RUF003` 规则）；`compute_schema_fingerprint()`/载荷指纹均为 `sha256(json.dumps(sort_keys=True))` 的确定性纯函数。
- 详细设计决策、字段级核对结果和验证记录见 `ai-docs/task.md` 的"WECOM-04/WECOM-05 验证记录"小节，不在此重复。
- 合并后实际门禁（主 Agent 重新执行，未只信任两个 Agent 各自的门禁结果）：`uv run ruff check .`、`uv run ruff format --check .`（仅剩既有 `ISS-029`）、`uv run mypy`（strict，**139 个源文件**）均通过；`uv run pytest -q`（**407 项收集，0 failure/0 error**，恰好等于 342 + 31 + 34）。`git diff --check` 通过（仅 LF→CRLF 提示）；用 `WECOM-00` 的敏感样例扫描逻辑对完整 diff 做了额外正向核验，真实样例 token 均未出现。
- 当前实现事实：企业微信数据层、Electron 凭证桥、协议 Client、字段 Mapper 均已就位，但公开/Main-only API、连接与同步编排 Service（幂等/状态机/重复检查）、renderer UI 均未实现，产品仍是 `wecom_sync=false` 占位。下一步是 `WECOM-06`（同步编排与 API），依赖已满足。

## 11. 企业微信同步编排与 API（WECOM-06）

- 2026-08-09：开工时发现工作树已存在未提交的 `WECOM-06` 半成品（`wecom_connection.py`/`wecom_sync.py` 两个 Service、`repositories/wecom.py`/`schemas/wecom.py` 的扩展、`main_bridge_secret` 相关的 `config.py`/`middleware.py`/`dependencies.py` 改动），逐文件核对其状态机/字段设计与 `docs/方案设计.md` §3～§11 一致后在此基础上继续，未推倒重写；这批未提交改动本身未包含任何 API 路由、`main.py` 接入或测试。
- `WeComConnectionService`（`app/services/wecom_connection.py`）：`validate_connection()` 在同一事务内完成模板发现、三题结构指纹计算、`wecom_user_bindings`/`wecom_sync_profiles` 原子写入，任一步失败前不写任何行；`update_profile()` 只允许更新 `recipient_config`/`field_mapping`，`question_mapping` 永远来自连接时发现。`WeComSyncService`（`app/services/wecom_sync.py`）：`execute()` 严格三段式（短事务 A 条件置 `syncing` 并生成 `attempt_token` → 事务外调 Client → 短事务 B 按 `attempt_token` 条件写终态），重复检测按 `template_id+reply_id+work_date` 匹配候选、无法证明归属则 `duplicate_detected` 且不提交；`get_or_create_record()` 按 `(daily_report_day_id, destination_fingerprint)` 幂等。
- 补齐的新交付：`app/api/v1/wecom.py`（公开 REST：`connection`/`profile`/`previews`/`sync-records` 及 `daily-report-days/{work_date}/wecom-syncs`）、`app/api/v1/internal_wecom.py`（Main-only REST，路由级 `require_main_bridge_secret` + `include_in_schema=False`）、`app/main.py` 接入。`docs/方案设计.md` §10.3 要求但半成品中缺失的启动崩溃恢复（`syncing` 超 5 分钟租约转 `uncertain`，绝不转 `failed`）已补齐：`WeComDailySyncRecordRepository.recover_stale_syncing()`/`WeComSyncService.recover_stale_syncing_records()`/`app/__main__.py` 启动接入。
- **发现并修复一个真实并发缺陷（`ISS-030`，P1）**：`_upsert_binding`/`_upsert_profile` 的 `except IntegrityError:` 回退分支未先 `rollback()` 就复用同一 `AsyncSession` 继续查询，SQLAlchemy 事务在 `flush()` 失败后已进入 `DEACTIVE` 态，任何后续查询立即抛 `PendingRollbackError`——真实并发/重复连接会直接 500 而非设计承诺的"回退为更新"。用真实 `asyncio.gather` 双会话并发复现后，改为把两处 `add()` 包进 `await self._session.begin_nested()`（SAVEPOINT）修复，只回滚这一次插入尝试而不牵连同一事务内更早已成功的写入（保住 binding+profile 同时成功/失败的原子性）。详见 `ai-docs/task.md`"WECOM-06 验证记录"。
- 测试：`tests/wecom_service_support.py`（共享 `StubWeComClient`/fixture 构造，非 `test_*` 命名不会被收集）+ 四个新测试文件共 45 项（Service 级连接 9 项、Service 级同步 20 项——含并发创建/并发执行拒绝/`attempt_token` 迟到丢弃的 Repository 级直接验证/崩溃恢复、公开 API 6 项、Main-only API 10 项——含双重鉴权/`X-Runtime-Secret` 豁免/OpenAPI 排除/`monkeypatch` 打桩后的连接-执行-重复检测全链路）。
- 门禁：`uv run ruff check .`、`uv run ruff format --check .`（仅剩既有 `ISS-029`）、`uv run mypy`（strict，**148 个源文件**）均通过；`uv run pytest -q --junitxml`（**458 项、0 failure/0 error/0 skipped**，等于阶段前 407 + 半成品自带 6 + 本任务新增 45）通过。
- 独立审查：派发了 `code-review`（high）与 `security-review`（专项安全）两个独立沙盒 Agent。`security-review` 已完成，复核所有权隔离、双密钥模型（`X-Main-Bridge-Secret` 恒定时间比较且路由级统一生效）、中间件路径豁免不误伤其他路由、响应不泄露凭证字段、无原始 SQL 注入面，未发现达到高置信度阈值的漏洞。`code-review`（high）提交时仍在后台运行，结果待补记（见 `task.md`"WECOM-06 验证记录"）。
- 已知范围边界（非缺陷，记入 `issues.md` `ISS-031`）：Electron `register-wecom-bridge.ts::connect()` 当前调用 `bridgeClient.validateConnection(cookieJar, '')`（`form_id` 空字符串，`WECOM-03` 自述已知的 `WECOM-06/07` 范围边界）且从未把 `credentialStore.save()` 的 `slot` 传给后端，而 `WECOM-06` 按方案设计把 `credential_slot` 实现为必填字段——真实点击"连接"目前仍无法完整走通，属已知边界的自然延伸，未越权提前修改 `electron/**`；`WECOM-07` 实现真实连接 UI 时需一并补上表单发现和 `credential_slot` 透传。
- 当前实现事实：企业微信后端（数据层、Electron 凭证桥、协议 Client、字段 Mapper、连接/同步编排 Service、公开与 Main-only API）已全部实现并通过独立审查，`wecom_sync` 能力开关仍为 `false`，renderer 无任何调用入口。下一步是 `WECOM-07`（Electron/Vue 交互），依赖 `WECOM-03`+`WECOM-06` 均已满足。

## 12. 企业微信 Electron/Vue 交互（WECOM-07）

- 2026-08-09：在工作树已有未提交半成品的基础上完成设置连接/重连/断开、账号与模板展示、动态字段映射、收件人/未映射策略、同步历史筛选分页，以及已归档日报的转换预览、未映射字段就地修正、同步状态和保守重试交互；当前模板保存映射时保留历史模板规则，避免破坏历史日报预览。
- Electron Main/preload 已接通真实 `form_id` 与 `credential_slot`。发现半成品把当前槽位只存在 Main 内存，应用重启或本地账号切换后无法读取 `safeStorage` Cookie jar（`ISS-032`）；新增双鉴权且不进入 OpenAPI 的 `GET /api/v1/internal/wecom/connections/credential-slot`，连接、断开、执行均按当前 JWT 获取本人 opaque slot 与 binding status。跨用户查询为 `null/null`，槽位、Cookie 与 Main-only secret 均不进入 preload/renderer；`ISS-031`/`ISS-032` 已随本阶段解决。
- `capabilities.wecom_sync` 已切换为 `true`，设置页和已归档日报详情均有真实入口。renderer 新增企业微信类型、公开 REST API、纯函数工具、两个 Vue 组件与 45 项工具单测；Electron 与后端补充真实请求形状、重启恢复、跨用户隔离、空表单 ID 和能力开关回归测试。
- 独立审查发现并推动关闭两个部分失败 P2（`ISS-033`）：槽位删除失败改为先写 Main-only 空 marker、后续连接/断开前持久重试；断开响应异常改为读取 `connection_status` 对账，确认 `disconnected` 时保持本地删除，确认后端仍指向原槽时才恢复加密 Cookie。另关闭历史重试可恢复性 P2（`ISS-034`）：未连接禁用操作，`pending` 可继续执行，异常后重载真实状态。经过三轮窄复审，最终无剩余 P0/P1/P2。
- 全量门禁：后端 `ruff check`、mypy strict（148 个源文件）、pytest（**460 项通过**）；`ruff format --check` 仅剩既有 `ISS-029`。前端 `npm run lint`、`npm run typecheck`、Vitest（**27 文件 254 项通过**）、`npm run build` 均通过；构建产物敏感字符串扫描通过。真实 Electron/sidecar 冒烟（临时扩展现有 spec，运行后还原）确认设置页企业微信表单入口可见、连接按钮可用、占位提示消失（**1 项通过**）；未使用真实企业微信账号、未发起外部登录。
- 下一步是 `WECOM-08`：受控真实账号连接/提交/对账、生产 sidecar/electron-builder 打包、安装升级、完整 Playwright E2E、发布级凭证扫描与独立安全审查。WECOM-07 只代表开发态交互闭环，不代表已经发布验收。

## 13. 企业微信轮转诊断日志（WECOM-07A）

- 新增独立 `wecom.log`：开发态位于 `.local-data/logs/`，生产态位于 Electron `userData/logs/`；单文件 2 MiB、保留 5 个轮转备份，后端迁移完成后配置，避免被 Alembic 的 logging 初始化禁用。
- 新增 `WEEKLY_REPORT_WECOM_LOG_REDACT` 开关，默认 `true`；设为 `false` 并重启后增加 HTTP 状态、异常分类/固定文案、业务码和模板识别纯计数。开关不影响 Cookie、JWT、运行时密钥、header/body、远端标识和日报正文的永久禁止规则。
- 企业微信 Client 与连接模板识别均已接入；下一次连接 502 可从 `business_rejected`、`protocol_changed` 或 `template_unresolved` 分类和安全诊断字段定位，不再依赖易失的 sidecar 内存日志。
- 后端完整门禁：Ruff lint 通过，mypy strict 150 个源文件通过，pytest 465 项通过；完整 format check 仅剩既有 `ISS-029`。`WECOM-08` 仍为下一任务，本增强不代表真实账号或发布级验收完成。

## 14. 企业微信真实连接兼容修复（WECOM-07B）

- 修复扫码完成后的 Electron 原生闪退：登录窗口改为强制销毁并等待 `closed` 后再清理隔离 Session；真实扫码后主应用保持运行。修复 SSO 页面替换初始导航产生的 `ERR_ABORTED (-3)` 误判：仅对仍存活窗口继续 Cookie 轮询，其它加载错误保持失败。
- 通过不含任何 value 的有界 key 路径和纯数字题型诊断，确认并兼容当前 live 响应：`form_info/form_info.form_id`、`createvid/doc_info.form_id`、文本题型 `reply_type=24`；保留旧 fixture 的 `form/form_id`、`reply_id`、文本题型 `1`，未知结构继续阻断。
- 真实连接最终记录为 `connection_validation outcome=ok`，Electron 保持 4 个常驻进程。后端定向 50 项、排除既有 `ISS-013` 后全量 470 项通过；Ruff lint、mypy、涉及文件 format check 通过。Electron lint、typecheck、Vitest 255 项和生产构建通过。
- `WECOM-08` 仍为下一任务：尚未验证真实日报提交、重复对账、生产 sidecar/electron-builder 打包安装升级、完整 E2E、发布级凭证扫描和独立安全审查。

## 15. 同步执行链路业务拒绝日志缺口修复（`ISS-037`，补充 WECOM-07A）

- 真实同步排障发现：`WeComSyncService.execute()`（而非 `validate_connection()`）触发的 HTTP-200-后业务/协议/结构拒绝完全没有写入 `wecom.log`，因为 `_send_json`/`_send_multipart` 的 `_log()` 只包住传输层解析，公开方法自己再调用的 `_parse_template_info`/`_parse_journal_page`/`_parse_submission_result` 逃逸在日志作用域外。已把 `parse` 折入同一 `_log()` 作用域，任何调用方（含 `validate_connection()`）现在都保证"一次调用一条准确结果的日志行"。
- `WeComBusinessRejected` 新增 `biz_message`（`head.msg`/`errmsg`，截断 200 字符），随 `business_code` 一起加入 `wecom_logging.py` 诊断白名单，仅在 `WEEKLY_REPORT_WECOM_LOG_REDACT=false` 时输出；`last_error_message`/API 契约不变。
- 用真实 `wecom_daily_sync_records` 数据定位到 2026-08-09 14:26:30 与 14:36:59 两次真实失败均止步于 `list_journals` 的业务拒绝，但当时的具体 `errcode`/`errmsg` 已随日志缺口丢失，无法回溯；修复后需用户重新触发一次同步才能拿到真实业务码。
- 新增/扩展测试覆盖 `biz_message` 提取、长度截断，以及两个专门针对本缺口的回归测试（`caplog` 直接断言业务拒绝产出且仅产出一条 `outcome=business_rejected` 记录）。后端 `ruff check`/`mypy` strict/`pytest` 全量执行通过（唯一失败项经 `git stash` 验证是本机 `.env` 遗留的既有失败，与本次改动无关）。已创建独立提交 `11ff7ab`（未推送远端）。

## 16. 未解析业务码诊断补强（`ISS-038`）

- 用户按 §15 的修复重启并重试后，`wecom.log` 显示 `list_journals` 的 `business_code=-1` 且没有 `schema_paths`——`error.detail`（即 `_schema_paths` 的输出）此前从未接入 `client.py::_log()` 的 diagnostics，只有 `WeComConnectionService` 自己重复实现的日志分支带这个字段。已把 `error.detail` 接入 `_log()`，并给三处 `WeComBusinessRejected` 补上 `detail=_schema_paths(payload)`。
- 用户重试后新日志显示 `schema_paths="entrys,errcode"`：响应顶层确实只有这两个键（排除了模板接口那种 `head` 信封漂移的可能），`entrys` 为空，`errcode` 本身值类型异常导致 `_coerce_biz_code` 回退为 `-1`。新增 `_describe_unparseable_code`/`_business_message_for_unparseable_code`：当 `errmsg`/`head.msg` 缺失且业务码无法解析为整数时，把原始值的类型/字面量（如 `""`/`None`，均属状态码字段本身而非日报正文或凭证）写入 `business_message`。
- 新增 5 项测试（含真实观测到的"非数字 `errcode`"、新增的"空字符串 `errcode`"两个场景）。全量 `ruff check`/`mypy` strict/`pytest` 通过。

## 17. 用户授权的原始正文调试开关（`ISS-039`）

- 用户在对话中明确要求"要企业微信接口返回的原始请求体和响应体"，并在被告知 Cookie/报告正文风险后明确授权、要求"加一个开关，只有我开启的时候才能打印"。判断依据：Cookie/header 的保护不因授权让步（等价账号会话凭证，`WeComInternalClient` 结构上也从未把 header 传给任何日志函数，与这个开关开/关无关）；但请求/响应**正文**本身（`list_journals` 尤其不含 Cookie）在用户对自己数据的明确、具体授权下可以做成默认关闭的显式开关，而不是一概拒绝。
- 新增 `Settings.wecom_debug_raw_body`（`WEEKLY_REPORT_WECOM_DEBUG_RAW_BODY`，默认 `false`）；新增与常规 `wecom.log` 物理隔离的独立文件 `wecom-raw-debug.log`（`.local-data/` 下已 gitignore，2 MiB×2 备份）；`log_wecom_raw_body()` 的函数签名没有 header/Cookie 形参；`configure_wecom_raw_debug_logging()` 在关闭时把目标 logger 设为 `disabled=True` 且不挂任何 handler（双重保险：调用点判断 + logger 本身失效）；即使正文里意外出现凭证形状的子串，仍会走统一的凭证正则 scrub 兜底；开关开启时会在正常 `wecom.log` 写一条醒目 WARNING 横幅，且提醒排障后需关闭并删除该文件。
- 已同步在 `AGENTS.md` 安全条款中记录这条被审视过、范围明确的例外及其边界，避免今后的 Agent 误判这是未授权的规则违反。
- 实现过程中发现并当场修正一个真实回归：最初把 `debug_raw_body` 实现为 `_new_client()` 内部直接调用全局 `get_settings()`（`@lru_cache` 单例），导致全量 `pytest` 从 1 项既有失败暴涨到 10 项——`test_wecom_internal_api.py`/`test_wecom_api.py` 靠 `create_app(settings=...)` 注入独立 `Settings` 实例，从不真正调用 `get_settings()`；只要请求路径真正走到 `_new_client()`（`validate_connection`/`execute_sync`），就会绕开测试注入的 Settings，直接命中本机 `.env` 的空 `runtime_secret` 报 `ValidationError`。已改用 `ExportService` 已经验证过的既定模式：`Settings` 经 `Depends(get_app_settings)` 在 `internal_wecom.py` 两个真正触达 Client 的路由（`validate_connection`/`execute_sync`）显式注入并传给 Service 构造函数；`WeComConnectionService`/`WeComSyncService` 新增可选 `settings` 参数，不引入任何模块级全局单例读取。
- 新增 9 项测试：默认关闭不落盘、开启后请求/响应正文均落盘且不含 Cookie、`submit_daily` 真实正文场景（验证开关确实生效而非静默空转）、凭证正则兜底、非法 `direction`/`path` 静默丢弃、`configure_wecom_logging`/`configure_wecom_raw_debug_logging` 双开关组合。DI 修复后重跑曾失败的全部 10 项均转为通过；全量 `ruff check`/`ruff format`/`mypy` strict/`pytest` 通过。
- 用户需要在自己的 `.env` 里设置该开关并重启应用才能生效；这是继续排查这次真实 `list_journals` 失败的下一步。

## 18. 执行同步协议改为 formcol/detail，移除 list_journals 查重（`ISS-040`）

- 用户提供真实成功抓包（`backend/wx-ribao/ribao.txt`）：`GET formcol/detail` 取结构 → `POST formcol/answer_page` 直接提交，全程不调用查重接口，且真实成功。用户据此明确决策：执行同步阶段完全放弃 `list_journals`，改走这条已验证的路径；`get_template_info`/`journal/get_template_combine_info` 仅保留给连接阶段（唯一能提供 `template_id` 的接口，`formcol/detail` 不返回该字段，提交时改用已保存的 `wecom_sync_profiles.template_id`）。
- 新增 `WeComInternalClient.get_form_detail()`（`GET /formcol/detail`，唯一不需要 `sid`/`wedoc_xsrf` 的接口）与 `WeComFormDetail`/`WeComFormDetailForkItem` 契约；`question_infos` 复用既有 `WeComQuestionItem`（`pos`/`note`/`ext` 均已是可选字段）。查重逻辑改用响应自带的 `fork_items`（按 `ctime` 换算 Asia/Shanghai 日期比对目标 `work_date`，只认存活 `status`），不再需要单独一次查重请求。
- 抓包同时暴露一个独立、此前从未被真实提交路径验证过的 bug：`reply_type=24`（"富文本"，这个账号今日工作/明日计划题目的实际类型）必须用 `rich_text_reply:{text_reply:"<div>...</div>",plain_text_reply:"..."}`，而不是代码里一直在用的裸 `text_reply`——此前从未暴露是因为同步从未真正跑到提交这一步。`WeComAnswerItem` 新增 `rich_text: bool`，`submit_daily()` 按此分流序列化并做 HTML 转义；判断依据是 `formcol/detail` 当次返回的题目原始数字 `type`（现查，不依赖本地保存的归一化 `text/date/select` 大类，因为那层归一化从设计上就不携带线格式细节）。多行文本的 HTML 换行渲染方式（`<br>` vs 分段 `<div>`）未经真实多行提交验证，是最佳猜测。
- `compute_schema_fingerprint()` 停止纳入 `sub_type`：`formcol/detail` 没有 `ext`，如果继续纳入会让每次执行同步都与连接时保存的指纹永久不匹配。副作用：已连接用户的指纹构成发生变化，下次同步会被判定一次 `schema_changed`（已有、经测试的正常处理路径，非新错误），需要重新连接一次。
- 查重来源换成 `fork_items` 后不再有可交叉验证的远端 ID（如 `journalid`），因此明确放弃了原设计里"`uncertain` 记录可自动对账为 `succeeded`"的分支；已确认这条分支在当前代码库里从未被任何调用点实际触发过（`retry()` 显式拒绝对 `uncertain` 记录生效），所以是记录一个此前只存在于纸面的能力缺口，不是真实行为倒退。
- 已删除不再被任何调用方使用的 `list_journals()`/`WeComJournalPage`/`WeComJournalEntry`/`_parse_journal_page`/`_MAX_JOURNAL_ENTRIES`/`_DEFAULT_JOURNAL_LIMIT`；`wecom_logging.py::_ALLOWED_PATH_TEMPLATES` 同步更新（移除 `get_journal_list`，新增 `formcol/detail`）。
- `docs/方案设计.md` §2.4/§5.3/§6.3/§10.2/§10.3 已修订，逐条记录新协议形状、`rich_text_reply` 格式要求、查重取舍及其理由，保留可追溯的修订说明而非静默改写。

## 19. fork_items 查重误判，彻底移除查重（`ISS-041`）

- 用户重新连接后重试同步，真实报告"检测到企业微信可能已存在同日日报"，但企业微信当天实际没有任何日报——`ISS-040` 刚上线的 `fork_items` 查重逻辑本身有 bug，不是历史遗留问题。
- 根因：`fork_items` 列出的是"这个周期性表单存在哪些日期的实例（fork）"，不是"哪些日期已经真正提交过内容"；抓包证据显示某个 fork 的 `ctime` 早于同一会话里对它的实际提交，说明"fork 存在"和"已提交"是两件事，而 `fork_items` 仅有的字段（`form_id`/`ctime`/`mtime`/`status`）没有一个能区分"空壳实例"与"已填写提交"。更严重的是，`get_form_detail()` 这次调用本身看起来就会让"今天"的 fork 成立——查重检查因此在每一次同步尝试上都 100% 误判，而不是"保守但偶尔误判"。
- 已彻底移除 `_has_duplicate_fork`/`_fork_item_matches_work_date`/`_FORK_ITEM_LIVE_STATUS` 三个函数/常量，`_perform_remote_sync()` 不再基于 `fork_items` 做任何阻断：结构指纹校验通过后直接提交，信任 `submit_again=true`，与用户提供的真实成功抓包（本身也不含查重调用）完全一致。`fork_items` 仍会被 `get_form_detail()` 抓取并建模（`WeComFormDetailForkItem`）供未来参考，只是不再影响状态机；`duplicate_detected` 状态、错误码 `40915` 和状态机允许的转换均保留在系统中，属于诚实记录、当前无路径可达的能力缺口。
- `docs/方案设计.md` §2.4/§5.3/§10.2/§10.3/§11 追加"第二次修订"说明，未删除 `ISS-040` 第一次修订的记录，保留完整决策轨迹。
- 移除 3 个已过时的查重专项测试，新增 2 个"存在 fork 也必须成功提交"的回归测试（`test_wecom_sync_service.py`/`test_wecom_internal_api.py` 各一个），防止这个 100% 误判行为再次出现。`ruff check`/`mypy` strict/定向 `pytest`/全量 `pytest` 均通过。
- 教训：`fork_items` 这类"实例列表"字段，在没有真实多日、多状态样本佐证前不能想当然地当作"提交历史"使用——这正是 `ISS-040` 实现时踩的坑，`ISS-041` 是紧接着的一次真实纠正，两者相隔不到一次重连+重试的时间。

## 20. reporter_vids 默认留空导致提交被拒，改为默认本人 vid（`ISS-042`）

- `ISS-041` 修复后用户重试，请求第一次真正打到 `formcol/answer_page`，但被业务拒绝（`business_code=-120000035`，无文案）。用户追问"为什么要我手填 vid，这不该自动获取吗"——是个合理的产品问题，不只是排障问题。
- 用 `WEEKLY_REPORT_WECOM_DEBUG_RAW_BODY` 的原始请求日志逐字段比对用户真实成功抓包，定位到唯一结构性差异：真实成功提交的 `wwjournal_data.entry.reporter` 是 `[{"vid": "本人 vid"}]`，失败请求的 `reporter`/`mngreporter` 全是空数组。原设计（`WeComConnectionService.validate_connection()`）在连接时把 `recipient_config.reporter_vids` 无条件初始化为空列表，理由是"没有可靠来源发现收件人"，把配置完全推给用户在设置页手填一个他们通常不知道的数字 vid。
- 直接查库确认：该用户 `wecom_user_bindings.wecom_vid`（连接时已经算出并保存的"猜测归属"值）与其真实成功抓包里的 `reporter` vid 完全一致。这说明"留空"从来不是保守选项，而是必然失败的选项——本人 vid 本来就已经在数据库里，只是没有被用上。
- 已改为连接时默认 `reporter_vids=[wecom_vid]`（`wecom_vid` 为空时仍保持空列表，避免 `WeComRecipientConfig` 的非空校验因 `[""]` 报错）；设置页仍保留手动覆盖/新增收件人的能力。更新 1 个既有测试的默认值断言，新增 1 个"无最佳猜测 entry 时不产出空字符串 vid"的边界测试。`docs/方案设计.md` §6.3 已同步修订。`ruff check`/`mypy` strict/定向 `pytest`/全量 `pytest` 均通过。
- 已知未处理的邻近问题（未在本次范围内）：`_upsert_profile()` 对已存在 profile 的重连会无条件用刚计算出的新 `recipient_config`/`field_mapping` 覆盖，这是本次改动之前就存在的既有行为——重新连接会连带覆盖用户此前在设置页手动配置的收件人/字段映射。是否应改为"仅在从未手动配置过时才套用默认值"是一个产品决策，留作后续观察项。**2026-08-10 更新：该观察项已由用户明确要求处理并解决，见第 25 节 `ISS-048`。**

## 21. 表单链接解析支持第二种真实链接格式（`ISS-043`）

- 用户要求 `parseWeComFormId` 支持企业微信"获取表单 id"分享链接 `https://doc.weixin.qq.com/journal/create?docid=c2_<form_id>`，此前只识别 `/forms/j/<id>` 一种。
- 新增 `docid=` 标记提取，按真实抓包确认的 `c2_` 前缀规律剥离前缀；原有 `/forms/j/` 优先提取、纯 id 直通、长度/空值校验行为不变。
- 新增 4 项 Vitest 用例；前端 `lint`（`eslint --fix` 修复一处 prettier 格式问题）/`typecheck`/`test`（27 文件 258 项）均通过。

## 22. "查看日报"按钮改为打开对应日报详情页（`ISS-044`）

- 用户指出 `WeComSettingsCard.vue` 同步历史表格的"查看日报"按钮实际打开的是 `/daily?date=...`（"我的日报"日历页按日期筛选），不是 `DailyDetailView.vue`（`/daily/:id`）本身。
- `WeComSyncRecordData` 只带 `daily_report_day_id`（日期容器 id），不是具体 `DailyReport` 条目 id，无法直接拼路由。改为复用 `DailyListView.vue::selectDate()` 已有的"按日期解析目标条目"逻辑：调 `getDayDetail(record.work_date)`，优先取 `status==='draft'` 的条目，否则取最后一条，再 `router.push('/daily/${target.id}')`，两个入口行为保持一致。
- 改为异步调用后补充 `openingRecordId` 逐行 loading 态防止重复点击；`entries` 为空的防御分支（理论上同步记录只会出现在已归档日期，不应发生）改为提示而非崩溃。
- 前端 `lint`/`typecheck`/`test`（27 文件 258 项）/`build` 均通过。该组件此前无 Vitest 单测（覆盖属于 Playwright E2E 范畴），本次未新增组件级单测，与既有测试边界保持一致。

## 23. page-heading/page-actions 非全屏下布局错乱（`ISS-045`）

- 用户报告 `DailyDetailView.vue` 的状态标签 + 三个按钮只有软件全屏时正常显示，非全屏（正常窗口宽度）下位置错乱。
- 根因在共享全局样式：`main.css` 的 `.page-heading` 是 `display: flex` 但缺 `flex-wrap`，标题区宽度不够时整体不换行，`.page-actions` 被挤压进标题右侧的剩余空间，标签和三个按钮各自的文字被迫在极窄列宽内内部折行，而不是整组换到新行。`.page-heading`/`.page-actions` 同时被 `DailyDetailView.vue` 和 `WeeklyDetailView.vue` 复用，判定为共享类问题，在 `main.css` 里统一修，不做单视图样式覆盖。
- 修复：`.page-heading` 增加 `flex-wrap: wrap`；`.page-actions` 增加 `flex-wrap: wrap` 与 `margin-left: auto`——后者让操作组在换到标题下方新行时仍贴右对齐，与两者共享一行时 `.page-heading` 的 `justify-content: space-between` 效果保持一致，避免换行前后左右对齐方式不统一。
- 纯 CSS 改动，无对应 Vitest；前端 `lint`/`typecheck`/`build` 均通过。验证时发现浏览器自动化工具的 `resize_window` 在本机环境下不改变实际渲染视口（`window.innerWidth` 固定），改为本地同源 HTTP 服务器 + 仓库真实 `main.css`/`base.css`/对应 DOM 结构的静态复现页，用固定宽度容器模拟 760px/480px 视口：先临时还原修复前的 CSS，截图复现出用户描述的错乱现象（操作组被挤压、按钮文字内部折行），再恢复修复后的 CSS，确认同一窄宽度下标签+三个按钮整组换行、贴右对齐，480px 更窄时按钮组自身也能整齐二次换行，均无重叠。
- 未在真实鉴权 Electron 应用内做最终截图确认，验证基于抽取自仓库的真实样式表与 DOM 结构的静态复现页；`WeComSettingsCard.vue` 存在用户自己进行中的无关手动改动（保存按钮 `margin-top` 内联样式、表格列宽 170→120），本次未触碰。

## 24. v0.3.0 打包发布：默认管理员固定初始密码 + E2E 断裂发现（`ISS-046`/`ISS-047`）

- 打包 v0.3.0 前照例先跑全量质量门禁，后端 `pytest` 意外出现 24 failed / 80 errors，排查定位到 `backend/app/services/bootstrap.py` 的默认管理员密码在上一个提交（`2fe9f1a` "fix: 修复bug"，非本会话所作）被硬编码成了 `'admin123'`，而不是像文档描述的那样与首位普通用户密码相同——这直接导致大量共享测试夹具（`tests/conftest.py::stage5_context`）登录失败而级联报错。
- 就地询问用户如何处理：用户明确表示这是有意变更，要保留固定的 `admin123` 初始密码。据此把裸字符串提炼为具名常量 `BootstrapService.DEFAULT_ADMIN_PASSWORD`，更新 `docs/需求理解.md`/`docs/方案设计.md`/`ai-docs/requirements.md` 中"管理员初始密码与用户密码相同"的措辞（`方案设计.md` 保留修订说明而非静默改写），并修复全部因此假设失效的后端测试——`conftest.py`、`test_system_bootstrap_api.py`、`test_wecom_api.py`、`test_auth_api.py`、`test_bootstrap_service.py`、`test_users_api.py`、`test_user_deletion.py`、`test_wecom_internal_api.py`，统一改为导入 `DEFAULT_ADMIN_PASSWORD` 登录/改密，而不是沿用普通用户密码变量。修复后全量 `pytest` 484 passed（唯一失败是已知与本次无关的本机 `.env` 空 `WEEKLY_REPORT_RUNTIME_SECRET` 残留，`git stash` 前后对比确认）；`ruff check`/`mypy` strict 均通过。
- 同一假设也写死在 Playwright E2E 助手里：`electron/e2e/helpers/app.ts` 的 `bootstrapAndSignInAsAdmin` 用首位用户密码登录 admin，且 `waitForSetupOrLogin`/`bootstrapFirstUser` 还在等待"创建管理员"标题文案——后者是本次会话更早前 `SetupView.vue` 改动（把标题改成"创建用户"）造成的连带失效。新增 `FIXED_ADMIN_INITIAL_PASSWORD` 常量，修复该助手及直接绕过助手登录 admin 的 `primary-path.spec.ts`/`user-deletion.spec.ts`。
- 修完上述问题后跑 `npm run test:e2e`（6 个 spec）验证，发现 4 个 spec（`daily-validation`/`primary-path`/`stale-version-conflict`/`user-deletion`）在登录成功后立刻卡在 `button:has-text("新建日报")` 超时——与本次改动无关：日历式日报创建重构（`DailyListView.vue`，最后改动于 `499cac6`）比 E2E 套件上一次真正重写（`QA-10`/`622154e`）更新，"新建日报"独立按钮已被移除，改为点击日历某天弹出确认对话框；这几个 spec 从未跟着更新。核对本会话及更早的一连串 `daily`/`wecom` 修复提交，发现它们的质量门禁记录里从未包含 `test:e2e`（只有 `lint`/`typecheck`/`test`/`build`），这个断裂因此一直没被发现。
- 判定为 `ISS-047`（P2，OPEN，不在本次范围内处理）：重写 4 个 spec 需要先吃透新的日历交互流程，工作量和风险都不适合在打包发布任务中顺手做掉，尤其 `primary-path.spec.ts` 是唯一的全链路验收覆盖，贸然按猜测改写风险较高。已如实告知用户当前只有 `admin-guard`/`auth-failures` 两个不涉及日报创建的 spec 能通过，请用户决定是否在本次发布前投入专项修复。

## 25. 重连覆盖用户已配置的字段映射/收件人（`ISS-048`）

- 用户报告：换一个企业微信表单 ID 重新连接后同步失败，且新旧表单字段名相同。排查确认根因正是 `ISS-042` 尾注记录的那个"留作后续观察项"：`WeComConnectionService._upsert_profile()` 对已存在 `wecom_sync_profiles` 行的重连，会无条件用 `validate_connection()` 里刚计算出的首次连接默认值覆盖 `field_mapping_json`（清空为空规则 + `unmapped_policy="block"`）与 `recipient_config_json`（重置收件人 vid 猜测）——而 `field_mapping` 本身只按本地模板 `field_key` 路由，跟连接的是哪个企业微信表单完全无关，重连没有理由重置它。
- 用户明确要求处理，判定为产品决策（`PROD-030`）：`_upsert_profile()` 改为只有该用户从未有过 profile 行（含并发插入竞态回退到 `IntegrityError` 分支）时，才写入首次计算的默认 `field_mapping`/`recipient_config`；已存在 profile 的重连（无论是否换了 `form_id`）只更新 `form_id`/`template_id`/`destination_fingerprint`/`question_mapping_json`/`schema_fingerprint`/`is_active`/`version`，不再触碰用户已配置的映射与收件人。`docs/方案设计.md` §5.1 步骤 5 同步补充一句澄清。
- 新增回归测试 `test_reconnect_preserves_manually_configured_field_mapping_and_recipient_config`：先首次连接，再通过 `update_profile()` 写入自定义映射规则与收件人，然后切到 `another-form` 重连，断言两者原样保留、`form_id`/`version` 仍按预期更新。
- 后端 `ruff check`/`mypy` strict（150 个源文件）/`pytest` 均实际执行：定向 `test_wecom_connection_service.py` 12 项全部通过；全量 pytest 唯一失败是 `test_config.py::test_test_environment_does_not_require_a_runtime_secret`，`git stash` 对比确认改动前后同样失败，是本机 `backend/.env` 残留空 `WEEKLY_REPORT_RUNTIME_SECRET` 导致，与 `ISS-046` 记录的是同一个已知环境问题，与本次改动无关。

## 26. 同步失败提示只显示 HTTP 状态码，丢弃了 sidecar 的具体错误信息（`ISS-049`）

- 用户报告日报同步失败时提示"企业微信内部服务请求失败（HTTP 502）"，看不出具体是什么问题。定位到 `electron/src/main/wecom/bridge-client.ts::request()`：非 2xx 响应时只拼接状态码抛出，从未读取响应体——而 sidecar 的统一异常处理（`backend/app/core/errors.py::register_exception_handlers`）对包括 Main-only `internal/wecom/**` 在内的所有路由都返回 `{code,msg,data}` 信封，`msg` 本来就是具体原因（该场景是 `_app_error_for()` 兜底分支的"企业微信返回内容不符合已知协议"）。这个 `WeComBridgeClientError.message` 会经 `register-wecom-bridge.ts::toReason()` 原样透传成 renderer `ElMessage.error` 展示的文案，所以之前用户看到的只有状态码。
- 新增 `WeComBridgeClient.extractErrorMessage()`：非 2xx 响应先尝试解析 JSON 取非空 `msg` 字段作为错误信息；只有响应体不是这个形状（非 FastAPI 响应、代理错误页、非 JSON 内容等）时才回退到原来的"企业微信内部服务请求失败（HTTP {status}）"通用文案，作为安全网而非被删除。
- 新增 2 项 Vitest 用例：sidecar 错误信封 `msg` 优先展示（502 + 具体 `msg`）、无 `msg`/响应体非 JSON 两种场景都正确回退到通用文案；既有"404 变成 clean typed error"用例未改动、仍通过。前端 `lint`/`typecheck`/`test`（27 文件 264 项）/`build` 均实际执行并通过。

## 27. 同步失败提示仍是固定通用句，丢弃了业务码（`ISS-050`）

- `ISS-049` 修复的是 Electron 桥接层丢弃 HTTP 层 `msg` 的问题；用户紧接着报告同步失败提示变成了固定文案"企业微信拒绝了本次提交"，还是看不出具体原因——这是同一类问题在更深一层的复现：后端 `backend/app/services/wecom_sync.py` 的 `_classify_write_client_error()`/`_classify_read_client_error()` 对 `WeComBusinessRejected` 各自返回一句写死的通用 `last_error_message`（"企业微信拒绝了本次提交"/"...请求"），完全丢弃了异常自带的 `biz_code`（真实场景常见 `business_code=-120000035` 且 `head.msg` 为空，`ISS-042` 已记录过这个具体号）。还额外发现一个既有不一致：`_app_error_for()` 对 `business_rejected` 这个 kind 没有专属分支，会掉进跟它无关的"企业微信返回内容不符合已知协议"兜底文案，导致同步当下弹出的即时报错跟写入数据库的 `last_error_message` 文案对不上。
- 新增 `_business_rejection_message(exc, action=...)`：把 `exc.biz_code` 直接拼进消息，例如"企业微信拒绝了本次提交(业务码 -120000035)"；读/写两个分类函数统一改用它。`_app_error_for()` 新增 `message` 形参和 `business_rejected` 专属分支，两处调用点（`get_form_detail`/`submit_daily` 的异常处理）把分类阶段算出的 `message` 传进去，修掉了上述"即时报错 vs 持久化记录"文案不一致的问题。
- 刻意不转发 `exc.biz_message`（WeCom 响应体里的原始 `head.msg` 文本，真实抓包里常见为空，偶尔有值）：`docs/方案设计.md` §9.4 明确写着"响应只给出用户可行动建议和本地 record_id，不透传企业微信原始响应"，而 `biz_code` 本身在 `WeComClientError` 的文档注释和现有调试日志开关设计里都已被当作"安全分类信息"处理（不是原始正文/Cookie/header 那一类），所以只暴露 code、不暴露远端原始文案，是在这次修复范围内能做到的最直接又仍然合规的做法。
- 新增 3 项 pytest：写路径业务码直出到 `last_error_message`/`AppError.message`、读路径同样直出、以及一个专门验证"就算异常真的带了 `biz_message`，这段真实企业微信文案也不会出现在任何用户可见文案或持久化记录里"的负向用例（防止未来有人为了"更详细"而不小心把 `biz_message` 也拼进去，违反 §9.4）。
- 后端 `ruff check`/`mypy` strict（150 个源文件）/定向 `pytest`（22 项）/全量 `pytest` 均实际执行：全量唯一失败仍是与 `ISS-046`/`ISS-048` 同源的本机 `.env` 残留空 `WEEKLY_REPORT_RUNTIME_SECRET` 环境问题，与本次改动无关。这次改动只在后端，前端 `weComSyncSummary()` 逻辑和其既有 Vitest 用例不受影响（该函数本就是把 `last_error_message` 原样透传，不关心具体文案内容），未触碰 `electron/**`。

## 28. 提交固定使用连接时的过期 fork form_id，改为解析当次最新 fork（`ISS-051`）

- `ISS-050` 修复上线后，用户下一条报告就是新提示"企业微信拒绝了本次提交（业务码 -1000888）"——直出错误信息这一层已经生效，问题回到了协议本身。用户此前排障留下的 `WEEKLY_REPORT_WECOM_DEBUG_RAW_BODY` 开关仍是开着的（`backend/.env` 里 `=true`），本机 `.local-data/logs/wecom-raw-debug.log`/`wecom.log` 已经记录了当次真实请求/响应，读取后定位到根因：企业微信这个"周期性日报表单"不是只在语义上循环，`form_id` 本身会随时间持续生成新的 fork 实例（`fork_items` 每项一个独立 `form_id`），旧 fork 在某个时间点后不再接受新提交。`wecom_sync_profiles.form_id` 只在 `WECOM-06` 设计的连接流程里写入一次、此后从不更新（`ISS-048`/`PROD-030` 处理的是"重连会不会覆盖用户配置"，跟这个"form_id 会不会过期"是完全不同的问题）；这次真实抓包里，连接时保存的 fork 比当前最新 fork 落后约一天，`submit_daily` 一直固定提交给这个过期 fork 因而被拒——而更新的那个 fork 其实就在同一次 `get_form_detail()` 响应的 `fork_items` 里，此前只是从未被用来选择提交目标（`ISS-040`/`ISS-041` 两次修订时 `fork_items` 只被当成"查重信号"评估过，从未考虑过"提交目标本身也可能需要跟着换"）。
- 新增 `_resolve_current_fork_form_id(form_detail, fallback=profile.form_id)`：从当次 `fork_items` 里选 `ctime` 最大（最新创建）的一项作为提交时实际使用的 `form_id`；`fork_items` 为空（刚连接、还没有 fork 历史）时退回 `profile.form_id`，即修复前的行为原样保留。解析出的 form_id **只用于 `WeComSubmitDailyPayload` 这一次提交调用**（`WeComInternalClient.submit_daily()` 内部单一来源同时驱动 URL 顶层 `form_id` 和 `wwjournal_data.entry.doc_info.form_id`，改一处即可两处生效），刻意不回写 `profile.form_id`，也不重算 `destination_fingerprint`——`wecom_daily_sync_records` 的 `(daily_report_day_id, destination_fingerprint)` 唯一约束和整套幂等模型（`PROD-029`）建立在连接时确定的稳定身份上，轮换的 fork id 混进去会让同一个"目标"每天都被判定成不同目标，破坏幂等；`get_form_detail()` 读取结构时仍传 `profile.form_id`，真实抓包证实该端点接受任意历史 fork 查询、不受影响。新增决策 `PROD-031`，`docs/方案设计.md` §10.2 追加第三次修订说明。
- 新增 2 项 pytest（用 `wecom_service_support.py` 已有的 `build_fork_item()` 构造合成 `fork_items`）：有更新 fork 时提交目标改用最新 fork（并断言 `profile.form_id`/`destination_fingerprint`/`version` 提交成功后原样不变）、无 `fork_items` 时保持退回旧行为不变。`StubWeComClient` 新增 `last_submit_payload` 记录最近一次提交内容供断言，这是共享测试基础设施的纯增量修改，不影响其他既有测试。
- 后端 `ruff check`/`mypy` strict（150 个源文件）/定向 `pytest`（`test_wecom_sync_service.py` 24 项）/全量 `pytest` 均实际执行：全量唯一失败仍是与 `ISS-046`/`ISS-048`/`ISS-050` 同源的本机 `.env` 环境问题，与本次改动无关。诊断过程中读取的真实 form_id/vid/日报正文均未抄入代码、注释、commit message、文档或测试，落地时全部替换为合成占位值（`ISS-000`/`WECOM-00` 既定纪律的延续）。
- **未决**：这个修复是基于单次真实抓包（"取 `fork_items` 中 `ctime` 最大者作为当前有效目标"）的最佳推断，还没有经过用户真实重试确认成功；如果推断有误（例如实际判据不是 `ctime` 而是某个未观察到的状态字段），需要用户再授权一次原始正文抓包定位。已提醒用户排障结束后关闭 `WEEKLY_REPORT_WECOM_DEBUG_RAW_BODY` 并删除 `wecom-raw-debug.log`，但鉴于修复尚待验证，暂时保留以备需要再次抓包。
- **2026-08-11 更新——该推断已被证伪**：用户重试后，读取新的原始调试日志确认提交请求确实已经改用最新 fork（`payload.form_id` 与 `fork_items` 里 `ctime` 最大者一致），但响应仍是同一个 `business_code=-1000888`。同时发现一个更严重的独立问题：这一个多小时里的 7 次重试，每一次企业微信真实响应的历史列表都精确多出一条新记录（创建时间与每次尝试时间对应），说明**即便 API 报错，提交内容其实还是被写进了用户真实的企业微信账号**，已提醒用户去检查并清理这些重复的占位测试内容，并暂停继续重试（记为 `ISS-053`，OPEN，是否要把这类"报错但实际已写入"的场景改判为不可直接重试的 `uncertain`，留给用户决定，本次未擅自改状态机）。真正根因见第 29 节 `ISS-052`。

## 29. reporter_vids 的"提交者自己的 vid"默认值本身就是错的（`ISS-052`）

- `ISS-051` 被证伪后，用户主动提供了新的真实抓包（`backend/wx-ribao/获取reportvids.txt`，用户自行获取并按既定治理只留在本地、未提交仓库）：`POST journal/get_template_combine_info?_prefetch=1`——正是连接时 `get_template_info()` 已经在调用的同一个端点——响应的 `body.entrys[]` 每一条真实历史记录都带一个 `reportvids` 字段，6 条记录全部是同一对 vid，且这对 vid 都不是提交者本人（对照同一响应的 `template_info.appro[]` 审批人名单，是其中两位）。这直接证明了 `ISS-042` 当初"connect 时找不到可靠的收件人来源，退而求其次默认成提交者自己的 vid"这个假设从一开始就是错的——`reportvids` 才是企业微信自己已经解析好的正确收件人（模板配置的审批人），从来不是提交者本人；而这个字段其实一直都在响应里，只是 `WeComTemplateEntry`（`model_config = ConfigDict(extra="ignore")`）把它当未知字段静默丢弃了，从未被读取过。
- `WeComTemplateEntry` 新增 `reportvids: list[RemoteId]` 字段（默认空列表，兼容没有这个字段的旧/合成响应）。`WeComConnectionService.validate_connection()` 里连接时算 `recipient_config` 的逻辑改为：`entries[0].reportvids` 非空时优先使用它；只有完全没有历史记录（真正的首次连接、还没有任何提交过）时才退回 `ISS-042` 的"提交者自己的 vid"兜底——这仍然好过空列表（`ISS-042` 已证明必被拒绝），只是不再是首选。这个字段本身是协议设计好交给调用方使用的标识列表（不是自由文本），跟 §9.4"不透传企业微信原始响应"约束的对象（`biz_message` 这类原始文案）性质不同，不受那条规则限制。`docs/方案设计.md` §6.3 追加修订说明。
- **对这个真实用户当下没有自动生效**：她/他已经有一份 `wecom_sync_profiles` 记录，而 `ISS-048` 已经让重连不再覆盖已有的 `recipient_config`，所以这个新的连接时默认值不会自动应用到已存在的连接上。已经告诉用户可以直接去设置页把"填报接收人 vid（reporter）"手动改成抓包里那两个真实审批人 vid（不需要重新连接、不需要重新打包），这是眼下能最快验证这个假设的办法。
- 新增 2 项 pytest：`entries[0].reportvids` 非空时优先使用、`reportvids` 为空/字段不存在时退回旧的自身 vid 兜底（确认两个既有 `ISS-042` 回归测试不受影响）。后端 `ruff check`/`mypy` strict（150 个源文件）/定向 `pytest`（`test_wecom_connection_service.py` 14 项、`test_wecom_client.py` 45 项）/全量 `pytest` 均通过，唯一失败仍是同源 `.env` 环境问题。
- **未决**：还没有经过用户真实重试确认 -1000888 真的消失；如果手动改了 vid 之后依然被拒，说明真正原因不止"收件人不对"这一项，需要再要一次真实抓包。
