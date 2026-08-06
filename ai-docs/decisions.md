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

## 2. 已接受产品与安全默认值

| ID | 决策 | 状态 | 来源 | 实施约束 |
|---|---|---|---|---|
| PROD-001 | V1 首发仅支持 Windows 10/11 x64 | Accepted for V1 | `requirements.md`、`docs/方案设计.md` | macOS/Linux 属于后续范围 |
| PROD-002 | admin 管理账号但默认不能查看其他用户业务正文 | Accepted | `requirements.md`、`api.md` | 管理接口只返回账号元数据；业务 Repository 仍按 owner 过滤 |
| PROD-003 | V1 日报状态固定为 `draft→submitted→archived`，归档后只读且不撤回 | Superseded for second version | `requirements.md`、`database.md`、CR-20260807-01 | 仅用于描述当前 V1 实现；第二版改为同日多条目与日期级汇总归档 |
| PROD-004 | 自然周固定为 Asia/Shanghai 周一至周日，周报仅汇总 archived 日报 | Accepted | `requirements.md`、`api.md` | 未归档日报只作提示，空周允许创建周报 |
| PROD-005 | V1 模板支持 text、textarea、number、date、select、multiselect，无附件 | Accepted for V1 | `requirements.md`、`database.md` | 核心字段不可删除且至少启用一个 |
| PROD-006 | 企业微信仅提供本地“未开放”占位，不定义同步 API | Accepted for V1 | `requirements.md`、`api.md` | 不引入 SDK，不产生企业微信网络请求 |
| PROD-007 | 导出动态列按 `field_key` 首次出现顺序排列，表头取该字段最近一次出现的标签文本 | Accepted for V1 | `EXPORT-01` 实现（`requirements.md` 4.4 只给出“按稳定 `field_key` 合并、同名标签追加短标识”的原则，未定义具体排序/取值算法） | 历史新增字段追加在已见字段之后；`field_key` 不变时标签变化不拆列；两个不同 `field_key` 恰好得到相同表头文本才追加 `field_key` 后缀消歧 |
| PROD-008 | 导出文件内的 `Asia/Shanghai` 时间展示使用固定 UTC+8 偏移而非 `zoneinfo` | Accepted for V1 | `EXPORT-02` 实现 | 中国大陆自 1991 年后不施行夏令时，固定偏移在数值上等价且避免生产环境依赖可选的 `tzdata` 包（Windows 默认不含 IANA 时区数据库）；若产品未来需要真实多时区支持需新 ADR |
| PROD-009 | 周报 `PUT` 只接受并覆盖 `supplement`/`next_week_plan`/`risks` 三个自由文本字段，`content.days` 由服务端固定为生成/重生成时的快照，不做逐字段编辑 | Accepted for V1 | `WEEKLY-02` 实现（`requirements.md` 4.3.4/4.3.5 只描述"自动内容"与"编辑区"两部分，未定义 `PUT` 的字段粒度） | 从机制上保证"人工编辑不反写日报"且不会让用户绕过重新生成来局部篡改来源摘要；若未来需要允许编辑单日摘要文本需新 ADR |
| PROD-010 | 手动整库备份不落业务表，改用进程内 `BackupRegistry`（随机 ULID -> 记录），15 分钟懒过期 + `create()` 时序清理 + 启动时目录级清理三重机制共同保证残留可控 | Accepted for V1 | `BACKUP-01` 实现（`database.md` §6 已给出"不登记业务表、进程内随机 ID 映射、15 分钟过期、启动清理"的原则，未定义具体触发时机的组合） | 进程重启即清空注册表，因此启动清理可以对目录下的 `*.db` 文件做无条件删除而无需比对任何持久状态；若未来需要备份跨进程重启仍可查询，需改为持久化记录并新增 ADR |
| PROD-011 | 第二版日期未归档时允许同日多篇条目，日期级归档汇总当天全部已提交条目并关闭日期 | Product direction accepted; design pending | `docs/需求理解.md` CR-20260807-01 | 有草稿时当前基线为阻止归档；正式日报唯一、来源可追溯、自动归档停用；需新数据/API/迁移设计 |
| PROD-012 | 第二版 admin 可撤销任意用户尚未归档的已提交条目，普通用户不能撤销 | Product direction accepted; permission detail pending | `docs/需求理解.md` CR-20260807-01 | 默认只开放必要元数据；是否查看他人正文待用户确认，操作需记录原因且不记录正文 |
| PROD-013 | 第二版首次初始化创建普通用户，并自动创建同初始密码的默认管理员 | Product direction accepted; account detail pending | `docs/需求理解.md` CR-20260807-01 | 两账号及默认数据必须原子创建、密码分别哈希；管理员用户名和强制改密策略待确认 |
| SEC-001 | JWT 持久化使用 Electron safeStorage | Accepted | `architecture.md`、`AGENTS.md` | renderer 不写 `localStorage`/`sessionStorage`；不可用时必须显式失败或提示 |
| SEC-002 | 所有业务 API 同时校验 JWT 与 `X-Runtime-Secret` | Accepted | `architecture.md`、`api.md` | `/health` 是唯一例外；Main 随机生成，renderer API 客户端仅在内存持有，不得进入 Vite 变量、持久化存储或日志 |
| SEC-003 | V1 不做 SQLite 整库加密 | Accepted for V1 | `requirements.md`、`architecture.md` | 密码使用 Argon2id、Token safeStorage；若要求磁盘泄露防护需新 ADR |
| SEC-004 | 密码最小长度 8 位、最大 128 位（服务端统一校验） | Accepted for V1 | `AUTH-01` 实现（`docs/需求理解.md`/`docs/方案设计.md` 未给出具体数值） | 仅为输入校验基线，非完整密码复杂度策略；`bootstrap-admin`/`AUTH-02` 登录改密/`USER-01` 重置密码均须复用同一下限，不得各自定义 |
| SEC-005 | JWT HS256 签名密钥由后端首次启动随机生成并持久化于数据目录 | Accepted for V1 | `AUTH-02` 实现 | 使用 256-bit 随机密钥和独占创建；重启后复用，格式损坏时拒绝启动；不得硬编码、记录日志或经 renderer 暴露 |
| SEC-006 | 导出 xlsx 对以 `=` 开头的字符串单元格加前缀单引号转义，防止 Excel 公式注入 | Accepted for V1 | `EXPORT-02` 实现，专项安全审查发现 | 仅处理 `=` 前缀（openpyxl 只会把该前缀提升为公式）；不处理 `+`/`-`/`@`，避免破坏中文报告中常见的列表符号 |
| SEC-007 | CORS 响应头显式 `expose_headers=["Content-Disposition"]` | Accepted for V1 | `EXPORT-02` 实现，真实 Electron 联调发现 | 仅新增这一个响应头的跨域可见性；`allow_origins` 固定白名单、`allow_credentials=False` 不变，不构成新的跨域数据泄露面 |
| SEC-008 | Electron 侧新增独立的 `BackupFileSaver`（`.db` 文件名白名单、100MB 字节上限），不与阶段 6 已审查的 `ExportFileSaver`（`.xlsx`、25MB）共享同一校验器实例 | Accepted for V1 | `BACKUP-01`/`FE-07` 实现 | 两个白名单结构相同但刻意不合并，避免任一方将来放宽后缀/大小限制时意外影响另一方；`backup:save-file` 与 `export:save-file` 是两个独立 IPC channel，均校验 `event.senderFrame` |
| SEC-009 | 手动备份跨管理员下载统一返回 `40401`（不区分"不存在"与"非本人创建"），与其余资源的所有权隔离约定一致 | Accepted for V1 | `BACKUP-01` 实现，`api.md` §1 既定原则的延伸 | 避免让任意 admin 通过响应差异枚举出其他 admin 是否创建过备份；创建者本人与非创建者的 404 响应体完全相同 |
| SEC-010 | 生产模式下 Electron 向 sidecar 子进程注入 `WEEKLY_REPORT_{DATA,LOG,BACKUP,EXPORT_TEMP,MANUAL_BACKUP_TEMP}_DIR`（均指向 `app.getPath('userData')` 下的子目录）与 `WEEKLY_REPORT_ENVIRONMENT=production`；开发模式不注入，沿用仓库相对 `.local-data/` 默认值 | Accepted for V1 | `PKG-01`/`PKG-02` 实现（`architecture.md` §4.3 已给出目标目录表，未定义生产环境变量如何把该目标真正传给 sidecar 进程，ISS-014 记录了这一实现缺口） | 安装目录必须保持只读（`architecture.md` §5）；未注入前生产 sidecar 会用相对仓库路径的默认值，PyInstaller 冻结后实际落在安装目录内部，会导致真实安装后首次启动即失败。`environment=production` 一并关闭 `/docs`（`main.py` 已有的开发态判断） |
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

## 4. 决策变更流程

以下变化必须先记录动机、备选方案、兼容性和迁移影响，并由技术负责人批准：

- 技术栈、数据库、桌面或后端框架替换。
- API 权限/错误码/状态语义、数据所有权或日报状态机变化。
- 表拆并、主键策略、模板快照、周报来源/覆盖语义变化。
- 数据目录、sidecar 生命周期、安全边界或打包结构变化。

批准后依次更新 `requirements.md`/`architecture.md`/`database.md`/`api.md`、`task.md`，最后修改代码。
