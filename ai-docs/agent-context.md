# Agent 启动上下文

> 适用分支：`v1`
> 快照日期：2026-08-10
> 用途：让新 Agent 在开始任务前快速恢复可靠上下文

## 1. 启动必读顺序

每个新会话按以下顺序执行；本文件由根 `AGENTS.md` 路由进入，不要求无目的重读所有长文档：

1. 当前对话中用户的最新明确指令。
2. 仓库根目录 `AGENTS.md`。
3. `ai-docs/README.md`、`progress.md`、`task.md`、`issues.md`。
4. 与任务直接相关的 `requirements.md`、`architecture.md`、`modules.md`、`database.md`、`api.md`、`coding-rule.md` 和 `decisions.md`。
5. 任务涉及产品范围、架构变更或文档冲突时，完整回溯 `docs/需求理解.md` 与 `docs/方案设计.md`。
6. 当前工作树中的相关清单、源码和测试。

只以当前 `v1` 工作树为依据。未经用户明确授权，不查看、引用、复制或合并其他分支及既往 Git 历史。

## 2. 事实优先级与冲突处理

信息冲突时按以下优先级处理：

```text
用户最新指令 / AGENTS.md
    > docs/需求理解.md / docs/方案设计.md
    > 当前代码与锁文件
    > ai-docs 派生汇总
```

当前代码与锁文件优先于 `ai-docs/` 判断实现现状，但不能反向修改已确认的产品或架构约束。发现实现与设计冲突时：

1. 停止扩大冲突范围。
2. 在 `ai-docs/issues.md` 记录文件证据、影响和建议。
3. 能依据上游明确修正的，先同步相关文档再修复实现。
4. 会改变产品范围、架构或数据契约的，请求用户确认。

## 3. 项目一句话说明

这是面向 Windows 10/11 x64 的本地多用户日报周报桌面应用：Electron 负责桌面生命周期，Vue 3 负责界面，FastAPI 是唯一业务入口，SQLite 只由单个后端进程访问。

## 4. 当前已证实的实现事实

截至本快照，当前工作树可直接证明：

- 根目录是 npm workspace，包管理器基准为 npm 10，`electron/` 是工作区成员。
- Electron 39、electron-vite 5、Vue 3、TypeScript、Vue Router、Pinia、Element Plus、Axios 和 Vitest 已配置。
- Electron 已实现单实例、安全窗口选项、sidecar 生命周期管理（动态端口、随机 `runtime_secret`、健康检查、退出清理）；preload 暴露受限的 `runtimeBridge.{sidecar,api,token}`，Token 仅由 Main 通过 `safeStorage` 加密持久化，无明文回退。
- renderer 在 sidecar 未就绪时展示 `StartupView`；就绪后恢复并校验安全 Token，按初始化/登录/角色状态进入对应路由；已接入初始化、登录、应用布局、admin 用户管理、模板管理、日报工作台/动态表单页面和周报工作台/编辑页面。
- FastAPI/uv/Python 3.12 项目已建立，绑定配置只允许 `127.0.0.1`，Uvicorn 固定单 worker；`RuntimeSecretMiddleware`、统一异常处理、达标 `/health` 均已实现。
- SQLAlchemy 异步 Engine/Session、SQLite PRAGMA、8 张业务表 ORM、Alembic 初始迁移、迁移前备份+轮转均已实现（阶段 3）。
- 阶段 4 后端已实现首次初始化、24h JWT、运行时用户状态与 `token_version` 双校验、登录/当前用户/改密/退出，以及 admin 用户查询/创建/更新/重置；创建用户会原子建立设置与默认模板，末位有效管理员受条件更新保护。
- 阶段 5 模板发布、个人设置/能力 API、日报快照与状态机及对应 Vue 页面已完成实现、自测、质量门禁、独立审查和提交 `1d965fe`，七项任务统一为 `DONE`。
- 阶段 6 导出任务/归档校验/动态列规划、xlsx 生成/下载/过期清理、Electron 保存对话框白名单和日报导出交互已完成实现、自测、质量门禁、独立审查（含专项安全审查）与提交 `d6ab86e`，五项任务统一为 `DONE`。
- 阶段 7 自然周可用性/生成/来源快照、人工编辑与确认重生成及对应 Vue 页面已完成实现、自测、质量门禁、独立审查（含专项安全审查），四项任务统一为 `DONE`。
- 阶段 8 admin 手动整库备份 API（checkpoint+backup API 生成、进程内 `BackupRegistry`、15 分钟懒过期、仅创建者下载）与设置/企业微信占位/管理员备份 Vue 页面已完成实现、自测、质量门禁、独立审查（含专项安全审查），三项任务统一为 `DONE`。
- 阶段 9 已完成：Playwright E2E 套件（`QA-09`）、真实 PyInstaller `onedir` sidecar（`PKG-01`，`build/sidecar/weekly-report-backend.exe`）、真实 electron-builder Windows 安装包（`PKG-02`）、本机安装/升级/卸载真实验证（`REL-01`，无独立干净虚拟机，已与用户确认该限制）均已交付；过程中发现并修复三个真实缺陷（sidecar 生产环境变量注入缺失 ISS-014、主进程模块打包遗漏 ISS-015、npm workspace 作用域包名导致安装产物异常 ISS-016）。
- `build/sidecar/` 已是真实产物目录，不再是占位。
- 2026-08-07 已完成 CR-20260807-01 的需求确认和技术方案编写：提出日期容器 1:n 条目、日期级正式快照/归档事务、admin 最小元数据撤销与脱敏审计、固定 admin/强制改密、安全删除、自然日统计、V1 迁移/受限 downgrade、周报/导出适配和 Electron 路由；`BE-10A`（迁移与认证基线）、`BE-10B`（日报聚合、管理员撤销与用户安全删除）、`BE-10C`（周报、导出与统计适配）均已实现、自测、质量门禁与独立安全审查通过。BE-10B 落地后启动 BE-10C 前发现并修正五处响应契约与 `docs/方案设计.md` 的偏差（ISS-023，已 RESOLVED），教训是字段级契约必须核对方案原文而非仅依赖 `ai-docs/` 摘要。`FE-10`（第二版 Electron/Vue 界面：强制改密路由、我的日报月历+日期级归档、我的周报多来源展示、统计页、管理员日报管理/用户删除、设置收口、日历页导出入口）已实现、自测、质量门禁通过并经真实 Electron 冒烟验证；实现过程中发现并当场修正一处自查缺口——重写"我的日报"为日历视图时最初遗漏了导出入口，已补回“导出本月已归档日报”/“导出当天正式日报”并用真实生成的 xlsx 文件验证。`QA-10`（端到端验收）已完成：迁移覆盖复核（确认既有 fixture 测试已满足要求）、Playwright E2E 套件全面重写为第二版形状（含扩写的主链路 `primary-path.spec.ts` 和新增的 `user-deletion.spec.ts`，连续 3 次全量重跑 100% 通过）、真实生产打包（PyInstaller+electron-builder）与真实安装/升级/卸载验证（含一次意外但真实的"已安装环境下 V1→V2 升级"验证，源自阶段 9 遗留的真实数据，记为 `ISS-025`）。CR-20260807-01 第二版增量至此全部交付完毕，后端与 Electron/Vue 界面均已全部是第二版并经端到端验证。

- 2026-08-08 已完成 CR-20260808-02 的 `WECOM-01` 文档阶段：企业微信反向同步将以本人已归档日期正式快照为唯一来源，采用 Electron Main 安全登录/`safeStorage` 凭证、FastAPI Mapper/Sync Service/内部协议 Client、三张非敏感元数据表、Main-only secret 和保守 `uncertain` 状态。代码尚未实现。
- 2026-08-08 已完成 `WECOM-00` 敏感样例治理（ISS-028 已 RESOLVED）：根 `.gitignore` 新增精确规则把用户提供的真实资料目录 `backend/wx-ribao/`（真实抓包 + 含真实 `journaluuid` 的参考脚本）整体排除，`git status --ignored` 确认已生效且原始文件未被改动；新增 `backend/tests/fixtures/wecom/` 四份全合成协议 fixture 供后续 Client 契约测试使用；新增 `backend/tests/test_wecom_fixture_hygiene.py` 作为可复跑敏感扫描，已用正向注入真实姓名验证过其真实生效而非空跑通过。后端 `ruff check`/`mypy`（strict，125 个源文件）/`pytest`（306 项收集，直接重定向运行 exit code 0 全部通过；两次复现已知非阻塞的 `ISS-013`）均已实际执行并通过。
- 2026-08-08 已完成 `WECOM-02`（企业微信数据基础）与 `WECOM-03`（Electron 登录与凭证桥），两个 Agent 按 backend/electron 无重叠文件并行实现，主 Agent 逐文件复核并统一提交。`WECOM-02`：三张 ORM 表（`wecom_user_bindings`/`wecom_sync_profiles`/`wecom_daily_sync_records`，迁移 `f19f6d677a36`）、Repository、`app/schemas/wecom.py` 的三个 Pydantic 配置契约，只是数据层，不含 Service/API/协议 Client。`WECOM-03`：`WeComCredentialStore`（`safeStorage` 加密、随机 `credential_slot`、无明文回退）、`WeComAuthWindowController`（隔离 session partition、精确主机名导航白名单、轮询 Cookie 判定登录完成）、`WeComBridgeClient`（调用尚不存在的 Main-only 端点会 404，是已知范围边界）、独立 `main_bridge_secret` 随子进程环境变量下发且不接入任何 IPC。合并后实际门禁：后端 `ruff check`/`mypy`（strict，132 个源文件）通过，`pytest`（342 项收集，0 failure/0 error）通过；前端 `lint`/`typecheck`/`test`（26 文件 192 项）/`build` 均通过；构建产物已复核无密钥/Cookie 泄露。
- 2026-08-08 已完成 `WECOM-04`（企业微信内部协议 Client）与 `WECOM-05`（字段映射与预览），两个 Agent 均在 backend 内并行实现，文件范围不重叠（`app/integrations/wecom/**` vs `app/services/wecom_mapper.py`），唯一共享的 `pyproject.toml`/`uv.lock`（`httpx` 迁移为生产依赖）只由 `WECOM-04` 改动且已尽早一次完成，主 Agent 逐文件复核并统一提交。`WECOM-04`：`WeComInternalClient` 三方法（`get_template_info`/`list_journals`/`submit_daily`）、host 硬编码 + 每请求二次校验防 SSRF、六种分类异常、RFC 6265 风格 Cookie URL 筛选、httpx 随机边界 multipart。`WECOM-05`：`wecom_mapper.py` 严格实现 §7.1 四条路由优先级、`PROJECT_LIST` 格式化、多来源"日报 N"分段、`schema_fingerprint`/`payload_fingerprint` 两个确定性纯函数；过程中解决了设计文档"责任人"表述的歧义并反向修正了 `docs/方案设计.md` §7.2 的示例文本（含冒号全角/半角的仓库惯例统一）。合并后实际门禁：后端 `ruff check`/`ruff format --check`（仅剩既有 `ISS-029`）/`mypy`（strict，139 个源文件）均通过，`pytest`（407 项收集，0 failure/0 error，等于 342+31+34）通过；用 `WECOM-00` 敏感样例扫描逻辑对完整 diff 做了额外正向核验。企业微信公开/Main-only API、连接与同步编排 Service（幂等/状态机/重复检查）、renderer UI 仍未开始，`wecom_sync` 仍为 `false`。
- 2026-08-09 已完成 `WECOM-06`（同步编排与 API）。开工时发现工作树已存在未提交的半成品（两个 Service 主体、Repository/Schema 扩展、`main_bridge_secret` 相关基础设施改动），核对与 `docs/方案设计.md` 一致后续建，补齐了 API 路由层（`app/api/v1/wecom.py` 公开 REST、`app/api/v1/internal_wecom.py` Main-only REST，路由级 `require_main_bridge_secret` + `include_in_schema=False`）、`main.py` 接入，以及设计文档要求但半成品缺失的启动崩溃恢复（`syncing` 超 5 分钟租约转 `uncertain`）。过程中发现并修复一个真实并发缺陷（`ISS-030`）：`WeComConnectionService` 的插入冲突回退逻辑在 `IntegrityError` 后未 `rollback()` 就复用同一 Session，真实并发连接会直接抛 `PendingRollbackError` 而非按设计回退为更新；已改用 `begin_nested()`（SAVEPOINT）修复并用真实 `asyncio.gather` 并发测试验证。新增 45 项测试（Service 级 29 项 + API 级 16 项）。全量门禁：`ruff check`/`ruff format --check`（仅剩既有 `ISS-029`）/`mypy`（strict，148 个源文件）均通过，`pytest`（458 项，0 failure/0 error）通过；独立审查已派发 `code-review`（high）与 `security-review` 两个沙盒 Agent，`security-review` 已完成且未发现高置信度安全漏洞，`code-review` 提交时仍在后台运行、结果待补记。已知边界（`ISS-031`，非缺陷）：Electron 现有 `register-wecom-bridge.ts::connect()` 的 `form_id`/`credential_slot` 尚未真正接通，真实"连接"UI 是 `WECOM-07` 的既定范围，本任务未越权修改 `electron/**`。企业微信后端至此全部就位，`wecom_sync` 能力开关仍为 `false`，renderer 无任何调用入口。
- 2026-08-09 已完成 `WECOM-07`（Electron/Vue 交互）：设置页提供表单连接/重连/断开、账号与模板信息、字段映射/收件人/未映射策略配置和同步历史；已归档日报详情提供预览、未映射字段就地修正、同步状态与保守重试。Electron `connect(form_id)` 已透传 Main 创建的 `credential_slot`；双鉴权且不进入 OpenAPI 的 Main-only 查询按当前 JWT 返回本人槽位与 binding status，解决重启/切换账号恢复（`ISS-032`）并支持断开响应对账。凭证删除失败通过只含 opaque slot 的空 marker 持久重试；历史 `pending` 可继续执行且未连接时禁用。Cookie/槽位不进入 preload/renderer；`ISS-031..034` 已解决，`wecom_sync=true`。全量门禁通过：后端 Ruff/mypy/pytest（460 项），前端 lint/typecheck/Vitest（27 文件 254 项）/build；真实 Electron 冒烟验证设置页入口可用；独立三轮窄复审最终无剩余 P0/P1/P2。受控真实企业微信账号、生产打包和发布级验收仍属于 `WECOM-08`。
- 2026-08-09 已完成 `WECOM-07A`（企业微信轮转诊断日志）：新增 `log_dir/wecom.log`（2 MiB × 5），默认脱敏；`WEEKLY_REPORT_WECOM_LOG_REDACT=false` 只增加 HTTP 状态、固定异常类型/文案、业务码和模板识别纯计数，Cookie/JWT/运行时密钥/header/body、远端标识及日报正文的强制保护不可关闭。Client 与连接模板识别已接入，完整后端 pytest 465 项通过；`WECOM-08` 边界不变。
- 2026-08-09 用户真实使用中同步持续失败，触发一轮非正式但产出真实修复的排障（`ISS-037`..`ISS-042`，均已 RESOLVED，先于正式 `WECOM-08` 立项）：`ISS-037` 修复了执行同步链路里业务/协议拒绝完全不写日志的缺口；`ISS-038` 补上未解析业务码的诊断（`schema_paths`/原始类型字面量）；`ISS-039` 是用户明确授权、范围收窄的原始正文调试开关（`WEEKLY_REPORT_WECOM_DEBUG_RAW_BODY`，默认关闭，Cookie/header 结构上不可能进入该路径）；`ISS-040` 是协议主体修复：用户提供真实成功抓包后，执行同步阶段彻底改用 `GET formcol/detail` 取代已对该账号失效的 `list_journals`，连接阶段仍用旧接口（唯一能给出 `template_id` 的来源），并顺带修复一个从未被真实提交路径验证过的独立 bug（`reply_type=24` 富文本题目需要 `rich_text_reply` 而非裸 `text_reply`）；`ISS-040` 当时新增的 `fork_items` 查重逻辑随即被 `ISS-041` 证实是自身引入的 bug——`fork_items` 是"表单实例是否存在"而非"是否已提交内容"，且 `get_form_detail()` 本身似乎就会让当天的 fork 成立，导致查重在每次尝试上都 100% 误判为重复；已彻底移除查重逻辑，直接提交并信任 `submit_again=true`，与用户抓包一致。移除查重后请求首次真正打到提交接口，被业务拒绝（`business_code=-120000035`，无文案）；`ISS-042` 用原始日志比对真实成功抓包定位到唯一结构性差异——`wwjournal_data.entry.reporter` 为空数组，而连接时早已算出并保存的本人 `wecom_vid` 从未被用上；已改为连接时默认 `reporter_vids=[wecom_vid]`，设置页仍可手动覆盖。`schema_fingerprint` 组成变化，已连接用户首次同步会触发一次（设计内、已测试的）`schema_changed`，需重新连接。`docs/方案设计.md` §2.4/§5.3/§6.3/§10.2/§10.3/§11 已同步修订并保留可追溯的修订说明（含 `ISS-040`/`ISS-041`/`ISS-042` 三次独立修订记录）。已知未处理的邻近问题：`_upsert_profile()` 重连会无条件覆盖用户手动配置的收件人/字段映射，是本次改动之前就存在的既有行为，未在本轮触碰，留作后续观察项。`WECOM-08` 的受控账号冒烟、生产打包、全链路 E2E、凭证扫描和独立安全审查仍未开始，此轮修复不能替代它们。
- 2026-08-10：`v0.3.0` 打包的安装包被发现企业微信同步入口仍显示"暂未开放"——根因是 `build/sidecar/`（打包进安装包的 PyInstaller 后端产物）自 08-07 起就没跟着 `WECOM-07`（08-09 把 `capabilities.wecom_sync` 默认值改成 `true`）重新编译，`npm run build:win` 只重建 Electron/Vue 前端和调用 electron-builder，不会触发 PyInstaller，导致安装包里嵌的后端还是旧代码。已重新执行 `uv sync --group build` + `pyinstaller` + 覆盖 `build/sidecar/` + `npm run build:win`，冒烟验证新 exe 跑到最新迁移（含 `f19f6d677a36 add wecom sync tables`）且 `main_bridge_secret` 校验生效；产出新 `electron/dist/weekly-report-0.3.0-setup.exe`（未提交到仓库，`dist/`/`build/sidecar/` 均 gitignore）。同时把这个易漏步骤补进根 `README.md`"生产打包（Windows 安装包）"一节，随文档改动一起创建独立提交。
- 2026-08-10 完成 `ISS-048`（`PROD-030`）：用户报告换一个企业微信表单 ID 重连后同步失败（新旧表单字段名相同），根因是 `ISS-042` 尾注记录的既有观察项——`WeComConnectionService._upsert_profile()` 对已存在 profile 的重连无条件用刚计算出的默认值覆盖 `field_mapping_json`/`recipient_config_json`，与 `field_mapping` 本身只按本地模板 `field_key` 路由（与远端表单结构无关）矛盾。用户明确要求处理后，改为仅在该用户从未有过 profile 行时才写入首次计算的默认值，已存在 profile 的重连（含并发插入回退分支）只刷新 `form_id`/`template_id`/`destination_fingerprint`/`question_mapping_json`/`schema_fingerprint`/`is_active`/`version`，不再触碰用户已配置的映射与收件人；`docs/方案设计.md` §5.1 步骤 5 同步补充修订说明。新增 1 项回归测试，后端 `ruff check`/`mypy` strict（150 个源文件）/`pytest` 均通过（唯一失败是与 `ISS-046` 同源的本机 `.env` 环境问题，`git stash` 对比确认无关）。
- 2026-08-10 完成 `ISS-049`：用户报告日报同步失败只提示"企业微信内部服务请求失败（HTTP 502）"，看不出具体原因。根因是 `electron/src/main/wecom/bridge-client.ts::request()` 对非 2xx 响应只拼状态码，从未读取 sidecar 统一 `{code,msg,data}` 错误信封（`backend/app/core/errors.py`，对全部路由生效，含 Main-only `internal/wecom/**`）里本来携带的具体 `msg`，而这个 message 会经 `register-wecom-bridge.ts::toReason()` 原样透传给 renderer 的 `ElMessage.error`。新增 `extractErrorMessage()`：非 2xx 响应优先取响应体里的非空 `msg`，只有响应体不是该形状时才回退到原来的"HTTP {status}"通用文案。新增 2 项 Vitest 用例，前端 `lint`/`typecheck`/`test`（27 文件 264 项）/`build` 均通过。

“依赖已列入清单”不等于对应业务已完成；“技术方案已描述”也不等于已经落地。

## 5. 当前阶段与下一步

- 已完成阶段：工程基线（`3a9fdbc`）、Desktop Bootstrap（`7386cae`）、数据基础与 API Foundation（`8480515`）、认证与用户管理（`1a50e75`）、模板、设置与日报闭环（`1d965fe`）、查询导出与桌面保存（`d6ab86e`）、周报闭环（`346b0ea`）、设置能力与受控备份（`00caa33`）、质量与发布（`0148171`）。
- 当前阶段：CR-20260808-02 已完成 `WECOM-00..07`，数据、凭证桥、协议 Client、字段 Mapper、同步编排/API 和 Electron/Vue 用户交互均已落地，`wecom_sync=true`。
- 下一步：`WECOM-08` 是唯一可领取任务，需完成受控企业微信测试账号冒烟、生产打包/安装升级、全链路 E2E、凭证扫描和独立安全审查。自动化测试仍须优先使用 `backend/tests/fixtures/wecom/` 的合成 fixture，不得让测试代码本身读取或依赖已被 `.gitignore` 排除的 `backend/wx-ribao/`；但当用户在对话中明确提供/引用该目录下的真实抓包用于协议排障时（`ISS-040` 先例：`ribao.txt`），可以读取以理解真实协议行为，只是绝不能把其中的真实 Cookie、姓名、`journaluuid` 等标识抄进代码、注释、commit message、文档或测试 fixture——落地时一律替换成合成占位值。使用真实测试账号必须保持受控且不得把凭证/正文写入日志或仓库。
- 未获用户明确授权，不得推送远端。

具体任务编号、依赖和状态以 `ai-docs/task.md` 为准；完成事实以 `ai-docs/progress.md` 为准。

## 6. 不可突破的实现边界

- Electron main/preload 只负责桌面能力和受限 IPC；不得承载业务 Service 或直接访问 SQLite。
- Vue renderer 只通过 REST API 访问业务数据，不得获得任意 Node、文件系统或命令执行能力。
- 所有业务写操作遵循 `API -> Service -> Repository -> Model/DB`。
- FastAPI 只监听 `127.0.0.1` 动态端口、保持单 worker，并校验 `X-Runtime-Secret`。
- `runtime_secret` 由 Main 每次启动随机生成，经最小 preload 契约只交付给 renderer 的 API 客户端并仅在内存使用；不得进入 Vite 变量、持久化存储或日志。
- JWT 由 Electron `safeStorage` 保存，不得写入 `localStorage` 或 `sessionStorage`。
- 不记录密码、JWT、runtime secret、完整日报或周报正文。
- 开发环境使用仓库 `.local-data/`；生产数据使用 Electron `userData`，安装目录保持只读。
- 企业微信开发态能力已随 `WECOM-07` 启用（`wecom_sync=true`），但尚未完成 `WECOM-08` 的受控真实账号、生产打包和发布级验收；AI 模型仍不在范围。
- 企业微信 Cookie 只能由 Electron Main 通过 `safeStorage` 保存；不得进入 renderer、SQLite、备份、日志或错误响应。携带 Cookie 的内部端点必须使用独立 Main-only secret，不能只依赖 renderer 可见的 runtime secret。

## 7. 工作与交付规则

1. 开工前检查 `git status --short --branch`，保留用户及其他 Agent 的已有修改。
2. 使用 PowerShell 7；文本检索优先 `rg`；不要使用 Bash heredoc 或 Bash 转义习惯。
3. 先确认任务依赖与验收标准，再修改最小必要范围。
4. 测试结果必须来自实际执行，不得根据清单或历史描述推断通过。
5. 每个阶段完成全部对应质量门禁后，复核工作树并创建一个独立 Conventional Commit。
6. 本地提交不代表可以推送远端；推送必须由用户明确授权。
7. 若任务需要三路并行，可按“后端/数据”“Electron/前端”“测试/文档”拆分给最多三个 Agent；先划定不重叠文件，再由主 Agent 集成验证与提交。

## 8. 常用质量门禁

仓库根目录：

```powershell
npm ci
npm run lint
npm run typecheck
npm test
npm run build
```

后端：

```powershell
uv sync --directory backend --frozen
uv run --directory backend ruff check .
uv run --directory backend mypy
uv run --directory backend pytest
```

只报告本次实际运行过的命令及结果；未运行的门禁明确标注未验证。
