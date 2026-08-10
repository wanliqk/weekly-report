# 技术决策记录

> 更新日期：2026-08-07
> 说明：本文件汇总已经接受的决策，不在此发明新架构。变更核心决策必须先走 `architecture.md` 的架构变更门禁。

## 1. 已接受架构决策

| ID | 决策 | 状态 | 主要来源 | 实施约束 |
|---|---|---|---|---|
| ADR-001 | Electron 与 FastAPI 使用回环 REST 通信 | Accepted | `architecture.md`、`docs/方案设计.md` | 后端只监听 `127.0.0.1`；Vue 仅通过 API 访问业务数据 |
| ADR-002 | FastAPI 是唯一业务入口，Node/Electron 不承载业务规则 | Accepted | `architecture.md`、`AGENTS.md` | 写操作遵循 API→Service→Repository→Model/DB；Electron 不访问 SQLite |
| ADR-003 | SQLite 由单 sidecar、单 worker 独占访问 | Accepted | `architecture.md`、`database.md` | 禁止多 Uvicorn worker 和第二个数据库访问进程 |
| ADR-004 | 使用不可变模板版本与日报完整 JSON 快照 | Accepted | `requirements.md`、`architecture.md` | 模板变更不得改变历史日报；版本行禁止原地更新/删除 |
| ADR-005 | 动态模板、日报和周报内容使用校验后的结构化 JSON | Accepted | `architecture.md`、`database.md` | JSON 写入前由版本化 schema 校验，不接受任意结构 |
| ADR-006 | API 使用 HTTP 状态与 `{code,msg,data}` 双层语义 | Accepted | `api.md`、`architecture.md` | 文件成功流为唯一例外；错误仍返回统一 JSON |
| ADR-007 | 本地认证采用 24h JWT 与 `token_version` | Accepted | `requirements.md`、`architecture.md` | 修改/重置密码或禁用账号后旧 Token 立即失效 |
| ADR-008 | V1 周报重生成须显式确认，确认后覆盖且不保留版本 | Accepted for V1 | `requirements.md`、`architecture.md` | 不得静默覆盖；版本历史留到 P2 |
| ADR-009 | Excel 使用任务记录加二进制下载 | Accepted | `architecture.md`、`api.md` | 后端生成并治理临时文件，普通 API 不返回内部路径 |
| ADR-010 | V1 所有数据库主键统一为 26 字符 ULID 文本 | Accepted | `architecture.md`、`database.md` | 不得混用 UUIDv7 或其他主键格式 |
| ADR-011 | 手动整库备份仅 admin 可用，通过短期下载文件交付 | Accepted | `requirements.md`、`architecture.md`、`api.md` | 备份含所有用户数据；随机 ID、15 分钟过期、界面明确提示敏感性 |
| ADR-012 | electron-vite 5 是唯一 Electron 开发/构建工具 | Accepted | `architecture.md`、`docs/方案设计.md` 工具链变更 | 源码固定在 `electron/src/main|preload|renderer`，产物固定在 `electron/out` |
| ADR-013 | Node.js 22.12+、npm 10+、根 npm workspace 是 JS 工具链基线 | Accepted | `architecture.md`、`AGENTS.md`、根 `package.json` | 使用根 `package-lock.json`；不在未评审时改用 pnpm |
| ADR-014 | 第二版使用日期容器 1:n 日报来源条目 | Accepted for V2 | `BE-10B` 实现（`docs/方案设计.md` 第二版、`architecture.md` §13） | 日期容器唯一表达日期关闭和正式日报；条目表取消同日唯一 |
| ADR-015 | 日期行保存版本化不可变正式快照 | Accepted for V2 | `BE-10B` 实现（`docs/方案设计.md` 第二版、`database.md` §8） | 按来源稳定排序，无损保留边界；周报/导出不临时拼装正式结果（周报/导出改读该快照仍是 BE-10C 范围） |
| ADR-016 | 日期行作为创建、保存、删除、提交、撤销和归档的共同并发互斥点 | Accepted for V2 | `BE-10B` 实现（`docs/方案设计.md` 第二版、`architecture.md` §13） | SQLite 短事务条件更新协调全部同日写操作，防止部分归档；已用并发测试验证创建/归档互斥 |
| ADR-017 | admin 撤销使用专用最小元数据查询与独立审计 | Accepted for V2 | `BE-10B` 实现（`requirements.md`、`api.md` §13） | 不查询/返回他人正文；审计只存原因和白名单元数据；已通过独立安全审查确认 SQL 层不选择正文列 |
| ADR-018 | 有业务记录的账号不得物理删除 | Accepted for V2 | `BE-10B` 实现（`requirements.md`、`database.md` §8） | 无业务账号可安全删除；有业务账号只能停用，避免级联丢失；末位管理员/自我删除保护已用并发测试验证 |
| ADR-019 | 周报、导出和完成统计只读取日期级正式日报 | Accepted for V2（`BE-10C`） | `requirements.md`、`docs/方案设计.md` 第二版 | 一日期只参与一次，来源条目仅作篇数和追溯，不重复汇总；周报/导出已改读 `daily_report_days.archive_snapshot_json`，统计的 `completed_days`/`daily_report_count` 分别按日期/来源条目口径查询 |

## 2. 已接受产品与安全默认值

| ID | 决策 | 状态 | 来源 | 实施约束 |
|---|---|---|---|---|
| PROD-001 | V1 首发仅支持 Windows 10/11 x64 | Accepted for V1 | `requirements.md`、`docs/方案设计.md` | macOS/Linux 属于后续范围 |
| PROD-002 | admin 管理账号但默认不能查看其他用户业务正文 | Accepted | `requirements.md`、`api.md` | 管理接口只返回账号元数据；业务 Repository 仍按 owner 过滤 |
| PROD-003 | V1 日报状态固定为 `draft→submitted→archived`，归档后只读且不撤回 | Superseded for second version | `requirements.md`、`database.md`、CR-20260807-01 | 仅用于描述当前 V1 实现；第二版改为同日多条目与日期级汇总归档 |
| PROD-004 | 自然周固定为 Asia/Shanghai 周一至周日，周报仅汇总 archived 日报 | Accepted | `requirements.md`、`api.md` | 未归档日报只作提示，空周允许创建周报 |
| PROD-005 | V1 模板支持 text、textarea、number、date、select、multiselect，无附件 | Extended by `PROD-022` | `requirements.md`、`database.md` | 核心字段不可删除且至少启用一个；`PROD-022` 新增第 7 种字段类型 `PROJECT_LIST`，本行描述的六种类型仍全部有效 |
| PROD-006 | 企业微信仅提供本地“未开放”占位，不定义同步 API | Accepted for V1 | `requirements.md`、`api.md` | 不引入 SDK，不产生企业微信网络请求 |
| PROD-007 | 导出动态列按 `field_key` 首次出现顺序排列，表头取该字段最近一次出现的标签文本 | Accepted for V1 | `EXPORT-01` 实现（`requirements.md` 4.4 只给出“按稳定 `field_key` 合并、同名标签追加短标识”的原则，未定义具体排序/取值算法） | 历史新增字段追加在已见字段之后；`field_key` 不变时标签变化不拆列；两个不同 `field_key` 恰好得到相同表头文本才追加 `field_key` 后缀消歧 |
| PROD-008 | 导出文件内的 `Asia/Shanghai` 时间展示使用固定 UTC+8 偏移而非 `zoneinfo` | Accepted for V1 | `EXPORT-02` 实现 | 中国大陆自 1991 年后不施行夏令时，固定偏移在数值上等价且避免生产环境依赖可选的 `tzdata` 包（Windows 默认不含 IANA 时区数据库）；若产品未来需要真实多时区支持需新 ADR |
| PROD-009 | 周报 `PUT` 只接受并覆盖 `supplement`/`next_week_plan`/`risks` 三个自由文本字段，`content.days` 由服务端固定为生成/重生成时的快照，不做逐字段编辑 | Accepted for V1 | `WEEKLY-02` 实现（`requirements.md` 4.3.4/4.3.5 只描述"自动内容"与"编辑区"两部分，未定义 `PUT` 的字段粒度） | 从机制上保证"人工编辑不反写日报"且不会让用户绕过重新生成来局部篡改来源摘要；若未来需要允许编辑单日摘要文本需新 ADR |
| PROD-010 | 手动整库备份不落业务表，改用进程内 `BackupRegistry`（随机 ULID -> 记录），15 分钟懒过期 + `create()` 时序清理 + 启动时目录级清理三重机制共同保证残留可控 | Accepted for V1 | `BACKUP-01` 实现（`database.md` §6 已给出"不登记业务表、进程内随机 ID 映射、15 分钟过期、启动清理"的原则，未定义具体触发时机的组合） | 进程重启即清空注册表，因此启动清理可以对目录下的 `*.db` 文件做无条件删除而无需比对任何持久状态；若未来需要备份跨进程重启仍可查询，需改为持久化记录并新增 ADR |
| PROD-011 | 第二版日期未归档时允许同日多篇条目，日期级归档汇总当天全部已提交条目并关闭日期 | Accepted for V2 | `docs/需求理解.md` CR-20260807-01、第二版方案 | 有草稿时阻止归档；正式日报唯一、来源可追溯、自动归档移除 |
| PROD-012 | 第二版 admin 可撤销任意用户尚未归档的已提交条目，普通用户不能撤销 | Accepted for V2 | `docs/需求理解.md` CR-20260807-01、第二版方案 | 仅开放必要元数据，不开放正文；必须填写原因并记录脱敏审计 |
| PROD-013 | 第二版首次初始化创建普通用户，并自动创建同初始密码的默认管理员 | Accepted for V2 | `docs/需求理解.md` CR-20260807-01、第二版方案 | admin 用户名固定、密码分别哈希、首次登录强制改密、双账号和默认数据原子创建 |
| PROD-014 | 第二版统计按自然日，日报篇数按来源条目，管理员只看本人统计 | Accepted for V2 | `docs/需求理解.md` CR-20260807-01 | 周末计入；日期正式日报不重复加一；不做团队排名 |
| PROD-015 | BE-10A 在 V2 表结构上保留 V1 日报 API 的“同日一篇/单篇归档”兼容桥；周报持久化先升级 V2、API 暂扁平化为 V1 展示结构 | Superseded by BE-10B（日报）/BE-10C（周报） | `BE-10A` 实现、`docs/方案设计.md` 分阶段计划 | 日报同日一篇兼容桥已随 `BE-10B` 移除；周报 API 已随 `BE-10C` 正式切换为 `entries[]` 多来源展示结构，不再扁平化为 V1 单来源形状 |
| PROD-018 | 导出单元格内多来源值按提交顺序渲染为 `[1] 值\n[2] 值`（以该日期正式快照中来源条目的固定序号编号），同一行内不同列共用同一套序号；只有单一来源时保持字段原始类型（数字不因合并逻辑转为文本） | Accepted for V2 | `BE-10C` 实现（`docs/方案设计.md` §9.2 已给出 `[1] 值`、`[2] 值` 的渲染格式，未定义序号在同一行跨列时是否保持一致、以及字段在某来源缺失时如何编号） | 序号按来源在该日期正式快照 `entries[]` 中的位置（1-based，已按 `submitted_at ASC` 排好序）固定分配，同一行所有列共用；某来源缺少该字段时该列直接跳过对应序号（不显示空的 `[N]` 占位行），保持"同一序号在整行中恒指同一来源"这一可读性约定 |
| PROD-016 | `client_request_id` 的幂等判定按 `(所有者, work_date)` 而非仅按 key 本身：同 key 且所有者/日期均一致才视为重放并返回既有条目，否则一律拒绝为 `40908` 冲突 | Accepted for V2 | `BE-10B` 实现（`api.md` §13.5 只定义“同键返回既有条目，不同键可创建同日新条目”，未定义跨用户/跨日期复用同一 key 时的判定粒度） | 避免任何一方在不知情时把复用的 key 静默接到别人的条目上；独立安全审查确认跨用户复用不返回对方日报内容，只返回 409 冲突 |
| PROD-017 | 日期级归档使用“先对日期行做条件 `UPDATE` 占用 SQLite 写锁、再读子条目决策”的两段式而非应用层锁表 | Accepted for V2 | `BE-10B` 实现（`database.md` §8.2 只要求“锁定/条件触碰日期行”，未定义具体机制） | 复用 `AUTH-01` 已确立的“单条件写语句关闭检查-写入竞态”模式；创建条目改用 `INSERT ... SELECT ... WHERE EXISTS` 单语句版本；均已用真实 `asyncio.gather` 并发测试验证 |
| PROD-019 | `electron/src/renderer/src/main.ts` 的 `app.use(ElementPlus, ...)` 新增 `locale: zhCn`（`element-plus/es/locale/lang/zh-cn`） | Accepted for V2 | `FE-10` 实现（真实冒烟发现：新增的 `el-calendar` 组件在未配置 locale 时渲染英文星期表头，与全局中文界面不一致） | V1 阶段未使用任何依赖 Element Plus 内建文案的组件（日期选择器等仅使用自定义占位符，未触发该问题），因此此前未配置；这是全局配置，理论上也会让既有组件（分页、空状态等）的内建文案从英文默认值改为中文，属于修复而非风险 |
| PROD-020 | 日报 Excel 导出的界面入口从 V1 的“日报列表复选框 + 筛选按钮”改为“我的日报”日历页的两个按钮——归档日期详情面板内“导出当天正式日报”（单日期）与页头“导出本月已归档日报”（按当前显示月的日期范围筛选） | Accepted for V2 | `FE-10` 实现（`docs/方案设计.md` §11.2 未规定导出入口的具体控件形态，只描述了日历+详情面板的整体布局；日历型 UI 不适合沿用表格勾选） | 复用既有 `POST /daily-report-exports` 的 `daily_report_day_ids`/`filter` 二选一契约，未新增接口；实现过程中曾在把“我的日报”整体重写为日历时遗漏导出入口，真实 Electron 冒烟验证阶段发现并当场补回（两个按钮均已用真实生成的 xlsx 文件验证），记录该疏漏是为了提醒后续大范围替换现有页面时，逐项核对被替换页面原有的全部能力清单，而不仅是核对新设计文档列出的能力 |
| PROD-022 | 新增模板字段类型 `PROJECT_LIST`（项目列表），支持一篇日报中登记多个项目各自的工作内容和完成状态；`content_json` 中该字段的值为 `[{"project": str, "content": str, "status": "TODO"\|"DOING"\|"DONE"}]`；完成状态固定三态，不走 `select`/`multiselect` 的模板可配置 `options` 机制 | Accepted | 用户直接指令（2026-08-08），不修改数据库结构，只扩展字段类型处理逻辑（`fields_json`/`content_json` 均为既有 TEXT/JSON 列） | 复用现有 `field_type` 校验通路（`_normalized_options` 已按“非 select/multiselect 类型不得配置 options”的既有规则自动拒绝该类型的 `options`，无需新增分支）；`DailyFieldValue` 新增 `list[ProjectListEntry]` 联合分支，`parse_daily_content`/`parse_day_archive_snapshot` 的 Pydantic smart-union 已实测能正确按列表元素类型（字符串 vs 对象）区分 `multiselect` 与 `PROJECT_LIST`，无需额外判别字段 |
| PROD-023 | `PROJECT_LIST` 导出为真正的二维表而非单元格文本：主表下方按“日期 × 字段”追加独立分块（标题行 + 固定表头 + 逐条目数据行） | Superseded by `PROD-024` | 用户直接指令（2026-08-08），取代 `PROD-022` 首版单元格分组渲染的导出格式 | 该“主表下方分块”布局本身已被 `PROD-024` 的“主表内联 + 纵向合并单元格”布局取代（用户对同一功能的第二次反馈）；`ProjectListBlockLayout`/`_style_block_title`/`style_report_sheet(..., project_list_blocks=...)` 已随 `PROD-024` 从 `export_style.py` 移除，`plan_export_columns` 的 `include` 过滤谓词已随 `PROD-024` 移除（不再需要两份不相交的列表） |
| PROD-024 | `PROJECT_LIST` 改为主表内联并纵向合并单元格（不再是独立分块）：`plan_export_columns` 恢复单一顺序列表但新增 `field_type` 字段（不再需要 `include` 过滤谓词），`PROJECT_LIST` 字段在该顺序中的位置直接展开为“项目/工作内容/进度”3 列表头，其余字段仍各占 1 列；`build_export_workbook` 按天计算 `row_count = max(1, 各 PROJECT_LIST 字段当天条目数)`，日级列（日期/责任人/其余非 `PROJECT_LIST` 字段）只在该天第一行写值，`row_count>1` 时用 `sheet.merge_cells()` 纵向合并到最后一行；`PROJECT_LIST` 列逐行填入各自条目，不足的行留空；多来源条目仍按提交顺序展平、不做 `[N]` 编号、不按项目名合并（同一原因：会与“进度”列冲突） | Accepted | 用户直接指令（2026-08-08），给出了具体表格示例和 7 条编号要求，取代 `PROD-023` 的分块布局 | 需求原文写“使用 POI 合并单元格功能实现”，但本仓库后端是 Python/FastAPI + openpyxl，并非 Java/Apache POI；已按功能等价实现为 openpyxl 的 `sheet.merge_cells()`（用一次性脚本验证过在合并单元格的非锚点 `MergedCell` 上设置 `.font`/`.alignment`/`.border` 是安全的，只有 `.value` 赋值会报错，因此“先写值+合并、样式统一后处理”的既有 `style_report_sheet()` 调用顺序不需要改变）；“项目”/“工作内容”仍需各自 `_defuse_formula()`（同 `PROD-023` 的结论，标准单元格无固定前缀防护）；需求量词“为空”“为 1”分别对应 `row_count=1` 时“不合并、明细列留空”与“不合并、明细列正常显示”两种自然结果，未新增专门分支；多个 `PROJECT_LIST` 字段（罕见）会各自贡献 3 列且 `row_count` 取所有字段条目数的最大值，未做表头消歧，超出本次需求范围 |
| PROD-021 | 日报 Excel 导出增加企业报表排版（居中大字号标题行、表头底色/加粗/边框、按内容宽度自适应列宽、长文本自动换行、按行内换行数估算行高、冻结标题+表头），样式代码集中封装在新增 `app/services/export_style.py`，`export.py` 只调用 `style_report_sheet()` 不直接操作 openpyxl 样式对象 | Accepted for V1/V2 | 用户直接指令（2026-08-08），纯表现层增强，不改变列合并/公式防注入/多来源渲染等既有业务逻辑 | 新增标题行使表头从第 1 行移到第 2 行、数据从第 3 行起（原第 1/2 行语义整体下移一行）；所有读取该 xlsx 固定行号的测试/下游代码需同步更新；样式颜色统一使用完整 8 位 ARGB（显式 `FF` 不透明前缀），因为 6 位 RGB 会被 openpyxl 回写为 `00` 透明前缀，Excel 会忽略该字节但 WPS/LibreOffice 等其他阅读器可能按透明处理导致表头白字不可见 |
| PROD-025 | 默认模板核心字段 `今日工作内容`（`core_type="today_work"`）的默认 `required` 从 `true` 改为 `false`；`明日工作计划`（`core_type="tomorrow_plan"`）保持 `required: true` 不变；`今日工作内容` 仍是核心字段（不可删除，仍计入“至少启用一个核心字段”规则），只是不再默认必填 | Accepted | 用户直接指令（2026-08-08），理由：用户若配置了 `PROJECT_LIST` 字段（`PROD-022`）承载今日工作内容，再强制要求填写单独的 `今日工作内容` 字段即属冗余 | 只改 `backend/app/services/user.py::default_template_fields()` 的默认值，不新增校验分支——`services/template.py` 的 `required` 字段本就由请求方自由设置，从未对核心字段做过锁定；只影响新引导的账号（首次初始化的双账号、管理员之后创建的新用户），已发布的历史模板版本不可变、不受影响；`test_submit_validates_required_fields_and_preserves_draft_on_failure` 原断言“空草稿提交产生 2 个必填错误”已同步改为断言仅 `明日工作计划` 报错 |
| PROD-026 | 导出 Excel 基础列 `责任人` 从第 2 列移到最后一列，模板字段列整体前移；`日期` 保持第 1 列不变 | Accepted | 用户直接指令（2026-08-08） | `export.py::_ColumnLayout` 新增 `owner_column` 字段记录 `责任人` 的 1-based 列号（始终等于表头总数，即最后一列）；`_plan_column_layout()` 改为先放 `日期`（列 1），逐个展开模板字段（`PROJECT_LIST` 仍展开为“项目/工作内容/进度”3 列），最后追加 `责任人`；`build_export_workbook()` 写值处从硬编码 `row[1] = owner_username` 改为 `row[layout.owner_column - 1] = owner_username`；`责任人` 仍是"日级列"（`PROD-024` 的合并集合成员之一），项目数大于 1 时随 `日期`/其余常规字段一起纵向合并；受影响的既有测试（列顺序断言）已同步更新，行为本身（合并/多来源编号/公式转义等）不变 |
| SEC-001 | JWT 持久化使用 Electron safeStorage | Accepted | `architecture.md`、`AGENTS.md` | renderer 不写 `localStorage`/`sessionStorage`；不可用时必须显式失败或提示 |
| SEC-002 | 所有业务 API 同时校验 JWT 与 `X-Runtime-Secret` | Accepted | `architecture.md`、`api.md` | `/health` 是唯一例外；Main 随机生成，renderer API 客户端仅在内存持有，不得进入 Vite 变量、持久化存储或日志 |
| SEC-003 | V1 不做 SQLite 整库加密 | Accepted for V1 | `requirements.md`、`architecture.md` | 密码使用 Argon2id、Token safeStorage；若要求磁盘泄露防护需新 ADR |
| SEC-004 | 密码最小长度 8 位、最大 128 位（服务端统一校验） | Accepted | `AUTH-01`、`BE-10A` 实现 | 仅为输入校验基线，非完整密码复杂度策略；`bootstrap`、登录改密和管理员重置密码均须复用同一下限，不得各自定义 |
| SEC-005 | JWT HS256 签名密钥由后端首次启动随机生成并持久化于数据目录 | Accepted for V1 | `AUTH-02` 实现 | 使用 256-bit 随机密钥和独占创建；重启后复用，格式损坏时拒绝启动；不得硬编码、记录日志或经 renderer 暴露 |
| SEC-006 | 导出 xlsx 对以 `=` 开头的字符串单元格加前缀单引号转义，防止 Excel 公式注入 | Accepted for V1 | `EXPORT-02` 实现，专项安全审查发现 | 仅处理 `=` 前缀（openpyxl 只会把该前缀提升为公式）；不处理 `+`/`-`/`@`，避免破坏中文报告中常见的列表符号 |
| SEC-007 | CORS 响应头显式 `expose_headers=["Content-Disposition"]` | Accepted for V1 | `EXPORT-02` 实现，真实 Electron 联调发现 | 仅新增这一个响应头的跨域可见性；`allow_origins` 固定白名单、`allow_credentials=False` 不变，不构成新的跨域数据泄露面 |
| SEC-008 | Electron 侧新增独立的 `BackupFileSaver`（`.db` 文件名白名单、100MB 字节上限），不与阶段 6 已审查的 `ExportFileSaver`（`.xlsx`、25MB）共享同一校验器实例 | Accepted for V1 | `BACKUP-01`/`FE-07` 实现 | 两个白名单结构相同但刻意不合并，避免任一方将来放宽后缀/大小限制时意外影响另一方；`backup:save-file` 与 `export:save-file` 是两个独立 IPC channel，均校验 `event.senderFrame` |
| SEC-009 | 手动备份跨管理员下载统一返回 `40401`（不区分"不存在"与"非本人创建"），与其余资源的所有权隔离约定一致 | Accepted for V1 | `BACKUP-01` 实现，`api.md` §1 既定原则的延伸 | 避免让任意 admin 通过响应差异枚举出其他 admin 是否创建过备份；创建者本人与非创建者的 404 响应体完全相同 |
| SEC-010 | 生产模式下 Electron 向 sidecar 子进程注入 `WEEKLY_REPORT_{DATA,LOG,BACKUP,EXPORT_TEMP,MANUAL_BACKUP_TEMP}_DIR`（均指向 `app.getPath('userData')` 下的子目录）与 `WEEKLY_REPORT_ENVIRONMENT=production`；开发模式不注入，沿用仓库相对 `.local-data/` 默认值 | Accepted for V1 | `PKG-01`/`PKG-02` 实现（`architecture.md` §4.3 已给出目标目录表，未定义生产环境变量如何把该目标真正传给 sidecar 进程，ISS-014 记录了这一实现缺口） | 安装目录必须保持只读（`architecture.md` §5）；未注入前生产 sidecar 会用相对仓库路径的默认值，PyInstaller 冻结后实际落在安装目录内部，会导致真实安装后首次启动即失败。`environment=production` 一并关闭 `/docs`（`main.py` 已有的开发态判断） |
| SEC-011 | admin 撤销/审计查询一律用 SQLAlchemy 原始列选择（`select(DailyReport.id, ..., User.username, ...)`）而非选择完整 ORM 实体 | Accepted for V2 | `BE-10B` 实现，`architecture.md` §13.2 既定原则的延伸 | `AdminSubmittedEntry` dataclass 结构性排除 `content_json`/`template_snapshot_json`，正文和模板快照在 SQL 层就不会被加载，不依赖响应 schema 兜底过滤；独立安全审查确认无绕过路径 |
| SEC-012 | 用户安全删除的确认口令使用目标账号原始 `username` 精确匹配（非规范化/不区分大小写），与登录/唯一性判重使用的 `casefold()` 规范化刻意不同 | Accepted for V2 | `BE-10B` 实现（`api.md` §13.1 只给出 `{confirm_username,reason}`，未定义比较口径） | 删除是不可逆物理操作，精确匹配比大小写无关匹配更能确认操作者确实看清了目标账号，而非被相近用户名误删；不影响登录仍使用规范化判重 |
| PKG-DEC-01 | `backend/app/db/migrate.py` 的 `alembic.ini`/`alembic/` 路径解析改为区分冻结态：`getattr(sys, "frozen", False)` 为真时相对 `sys.executable` 所在目录解析，否则保持原有 `__file__` 相对路径 | Accepted for V1 | `PKG-01` 实现 | PyInstaller onedir 冻结后纯 Python 模块不再是磁盘上的真实文件，`__file__` 相对路径不可用；`alembic.ini`/`alembic/versions/*.py` 改为 PyInstaller spec 显式 `datas` 打包在 exe 同级目录（`weekly-report-backend.spec` 的 `contents_directory="."` 保证两者同级），只影响该模块内部路径解析，不改变对外契约 |
| PKG-DEC-02 | `electron/package.json` 的 `name` 从作用域包名 `@weekly-report/electron` 改为 `weekly-report-electron` | Accepted for V1 | `PKG-02`/`REL-01` 实现（真实构建发现，见 `issues.md` ISS-016） | electron-builder 在 `oneClick && !perMachine`（本项目 NSIS 配置）下用 `sanitizeFileName(package.json name)` 作为默认安装目录名且不处理 `@scope/` 前缀，导致真实安装目录被命名为畸形的 `@weekly-reportelectron` 且安装内容为空；根 `package.json` 的 `workspaces: ["electron"]` 按目录路径匹配，不依赖该字段，重命名不影响任何现有脚本 |
| PKG-DEC-03 | `electron-builder.yml` 的 `nsis.artifactName` 改用 `${productFilename}-${version}-setup.${ext}`（原为 `${name}-...`） | Accepted for V1 | `PKG-02`/`REL-01` 实现（真实构建发现，见 `issues.md` ISS-016） | `${name}` 直接取 package.json 原始 `name`，作用域包名中的 `/` 被 NSIS 当路径分隔符，导致安装包完全生成失败（"Can't open output file"）；`${productFilename}` 是 electron-builder 已做过安全字符校验的产物名（本项目固定解析为 `weekly-report`） |
| PKG-DEC-04 | `electron.vite.config.ts` 的 main 进程构建对 `@electron-toolkit/utils` 显式排除出外部化（`externalizeDepsPlugin({ exclude: [...] })`），强制打包进 `out/main/index.js` | Accepted for V1 | `PKG-02`/`REL-01` 实现（真实安装间歇性复现，见 `issues.md` ISS-015，P0） | electron-vite 默认把 main 进程的真实 npm 依赖外部化为运行期 `require(...)`，依赖 electron-builder 打包时从 `node_modules` 收集；npm workspace 提升导致该依赖实际位于仓库根 `node_modules/` 而非 `electron/node_modules/`，electron-builder 的依赖遍历间歇性遗漏，造成打包后主进程约有一定概率启动即抛 `Cannot find module` 且窗口完全打不开。若未来新增 main/preload 依赖出现类似问题，同一模式（显式排除外部化、强制打包）优先于继续依赖 electron-builder 的自动依赖收集 |

## 3. 工程协作决策

| ID | 决策 | 状态 | 来源 | 实施约束 |
|---|---|---|---|---|
| GOV-001 | `v1` 是全新主线，只以当前工作树和基线文档为依据 | Accepted | `AGENTS.md` | 未经用户授权不得查看或引用其他分支及 Git 历史实现 |
| GOV-002 | 每个技术阶段通过质量门禁后创建独立 Conventional Commit | Accepted | 用户指令、`AGENTS.md` | 当前阶段不得混入下一阶段；本地提交不代表允许推送 |
| GOV-003 | 任务可按 Agent A/B/C 划分，每项只有一个主责 Agent | Accepted planning convention | 用户指令、`modules.md` | 依赖未满足不得抢跑，共享文件改动先协调 |

## 3.1 企业微信同步决策（CR-20260808-02）

| ID | 决策 | 状态 | 来源 | 约束 |
|---|---|---|---|---|
| PROD-027 | 首版只允许当前用户手动同步本人已归档的日期级正式日报 | Accepted for V1 | `WECOM-06` 实现（`docs/需求理解.md` CR-20260808-02） | 不同步草稿/开放日期，不在归档事务中发外部请求，不允许 admin 同步他人日报；`WeComSyncService.preview()`/`get_or_create_record()` 均强制 owner+`status=archived` |
| PROD-028 | 每用户首版只维护一个启用目标，字段按稳定 `field_key` 映射 | Accepted for V1 | `WECOM-06` 实现（`docs/方案设计.md` CR-20260808-02） | 标签只做首次建议；未映射非空字段阻止提交；`wecom_sync_profiles.user_id` 唯一约束、`PUT /wecom/profile` 只更新映射不重跑标签启发式 |
| PROD-029 | 同步幂等以"日期正式日报 + 目标表单/模板指纹"为准 | Accepted for V1 | `WECOM-06` 实现（`docs/方案设计.md` §6/§10） | 同一目标成功后不重复，不同目标可以显式创建新记录；`(daily_report_day_id, destination_fingerprint)` 唯一约束 + `get_or_create_record()` 幂等已用并发测试验证 |
| PROD-030 | 重连（含换 `form_id`）保留用户已配置的 `field_mapping`/`recipient_config`，只在从未连接过时套用首次计算的默认值 | Accepted for V1 | 用户报告 `ISS-042` 尾注的既有观察项在真实使用中确认为缺陷并要求修复（`ai-docs/issues.md` `ISS-048`） | `field_mapping` 只按本地模板 `field_key` 路由，与远端表单结构无关，重连没有理由重置；`WeComConnectionService._upsert_profile()` 已存在 profile 的分支（含并发插入回退）不再写入新计算的 `field_mapping`/`recipient_config`，只更新 `form_id`/`template_id`/`destination_fingerprint`/`question_mapping_json`/`schema_fingerprint`/`is_active`/`version` |
| SEC-013 | Cookie jar 只由 Electron Main 用 `safeStorage` 保存，SQLite 仅存随机凭证槽位 | Accepted for V1 | `WECOM-03`/`WECOM-07` 实现（`docs/方案设计.md` §3/§6/§12） | Cookie 不进入 renderer、数据库备份、日志、错误响应或 Git；Main-only 端点只在单次请求内内存持有 Cookie jar，从不落库；槽位也不进入 preload/renderer |
| SEC-014 | 企业微信内部端点使用独立 `main_bridge_secret` + 用户 JWT | Accepted for V1 | `WECOM-06`/`WECOM-07` 实现（`docs/方案设计.md` §3.1/§9） | 现有 runtime secret 对 renderer 可见，不能作为唯一保护；`require_main_bridge_secret`（`secrets.compare_digest`）作为路由级依赖统一生效于全部四个 Main-only 端点，包含不进入 OpenAPI 的槽位查询 |
| SEC-015 | `uncertain` 不自动重试，只能先远端对账 | Accepted for V1 | `WECOM-06` 实现（`docs/方案设计.md` §10.3/§11） | 网络超时或崩溃可能已受理，自动重试会制造重复日报；`WeComSyncService.retry()` 对 `uncertain` 状态显式拒绝（`WeComUncertainRetryBlockedError`），启动崩溃恢复只把超租约 `syncing` 转为 `uncertain`、绝不转 `failed` |
| SEC-016 | Electron Main 不以内存变量作为当前企业微信凭证槽位的事实来源，而是按当前用户 JWT 从双鉴权 Main-only API 查询 | Accepted for V1 | `WECOM-07` 实现（`ISS-032`） | 支持应用重启和本地账号切换；后端只返回当前 JWT 用户的 opaque slot + binding status（无绑定为 `null/null`），Main 只在 `connected` 时执行同步，并用状态对账断开响应；任何槽位值都不暴露给 preload/renderer |
| SEC-017 | 企业微信凭证删除采用 Main-only 持久待清理 marker，跨 Main/后端断开失败采用读回状态对账 | Accepted for V1 | `WECOM-07` 独立审查修复（`ISS-033`） | marker 是空文件且文件名只含随机 opaque slot，不含 Cookie/用户/表单信息；后续连接/断开前重试。断开响应异常时，只有读回仍指向原 slot 且状态非 `disconnected` 才恢复本地加密 Cookie；若已 `disconnected` 则保持删除 |
| SEC-018 | 企业微信诊断使用独立轮转 `wecom.log`，脱敏开关只控制白名单诊断元数据 | Accepted for V1 | 用户直接指令（2026-08-09）、`WECOM-07A`/`WECOM-07B` | 默认 `WEEKLY_REPORT_WECOM_LOG_REDACT=true`；`false` 时可增加 HTTP 状态、固定异常类型/文案、业务码、纯结构计数、有界协议 key 路径和纯数字题型枚举；key 路径必须经过标识符正则、深度/数量/长度上限且不得读取 value。Cookie/JWT/运行时密钥/header/body、远端标识和日报正文始终禁止落盘，并由参数面、键白名单和 Formatter 二次清洗共同保护；2 MiB × 5 轮转 |

## 4. 决策变更流程

以下变化必须先记录动机、备选方案、兼容性和迁移影响，并由技术负责人批准：

- 技术栈、数据库、桌面或后端框架替换。
- API 权限/错误码/状态语义、数据所有权或日报状态机变化。
- 表拆并、主键策略、模板快照、周报来源/覆盖语义变化。
- 数据目录、sidecar 生命周期、安全边界或打包结构变化。

批准后依次更新 `requirements.md`/`architecture.md`/`database.md`/`api.md`、`task.md`，最后修改代码。
