# 问题、风险与阻塞记录

> 更新日期：2026-08-07
> 严重度：P0 安全/数据损失；P1 核心功能/契约；P2 可维护性/体验；P3 建议
> 状态：`OPEN`、`MITIGATED`、`RESOLVED`、`BLOCKED`

## 1. 当前开放项

| ID | 级别 | 状态 | 问题/风险 | 当前影响 | 处理条件/归属 |
|---|---|---|---|---|---|
| ISS-001 | P1 | RESOLVED | Electron 尚未托管 FastAPI sidecar | 阶段 2 已实现 `SidecarManager`：动态端口、单例拉起、开发/生产路径解析、退出清理，代码与测试均完成，已随阶段 2 提交 `7386cae` 交付 | 阶段 2 `DESK-02`（已交付） |
| ISS-002 | P0 | RESOLVED | runtime secret 尚未生成和校验 | 阶段 2 已实现并随 `7386cae` 交付：Main 每次启动经 `crypto.randomBytes(32)` 随机生成，仅经环境变量传给子进程、仅内存持有；后端 `RuntimeSecretMiddleware` 对除 `/health`/`/docs`/`/openapi.json` 外的请求强制校验；已扫描构建产物确认密钥不进入 Vite 变量。业务 API 本身仍要等阶段 4 JWT 落地才算真正开放（见 ISS-006） | 阶段 2 `DESK-02`/`BE-02`/`DESK-03`（已交付） |
| ISS-003 | P1 | RESOLVED | `/health` 未达到冻结契约 | 阶段 2 已补齐 `version` 字段与 `Cache-Control: no-store`，并有对应测试，已随 `7386cae` 交付 | 阶段 2 `BE-02`（已交付） |
| ISS-004 | P1 | RESOLVED | 业务窗口不等待后端健康成功 | 阶段 2 已实现并随 `7386cae` 交付：`App.vue` 在 sidecar 未 `ready` 时渲染 `StartupView`（pending/failed 态，failed 态可重试并展示脱敏日志），不再直接展示业务首页 | 阶段 2 `DESK-03`（已交付） |
| ISS-005 | P1 | MITIGATED | 数据库与迁移基础尚未实现 | 阶段 3 已实现 Engine/Session、8 张表 ORM、Alembic 初始迁移、PRAGMA、迁移前备份+轮转，代码与测试均完成（45 项后端测试通过），并已创建独立提交 `8480515`；独立 Reviewer 审查完成前保持 `MITIGATED`，不升级为 `RESOLVED` | 阶段 3 `DB-01`..`DB-03`（已提交，待独立 Reviewer 审查） |
| ISS-006 | P0 | RESOLVED | 所有权与业务 API 尚未完整实现 | 阶段 4 认证、阶段 5 模板/设置/日报状态机、阶段 6 导出和阶段 7 周报的 owner 强制过滤均已提交并通过独立审查（阶段 6、7 另有专项安全审查逐条核实所有权隔离）；全部面向普通用户的业务 API（认证、用户、模板、日报、设置、导出、周报）owner 边界均已确认。admin 手动整库备份（`BACKUP-01`，阶段 8）是不同性质的管理员运维能力，其"仅创建者本人可下载"边界已随阶段 8 实现并通过独立安全审查，由 RISK-004 继续跟踪该功能固有的敏感性风险 | 阶段 4/5/6/7/8（均已交付） |
| ISS-007 | P2 | OPEN | Element Plus 当前全量引入 | renderer 生产包偏大，阶段基线曾观测主 JS 约 2.6 MB；会影响启动和构建告警 | 前端页面组件稳定后改为按需引入，并以构建体积对比验证；不得为此提前混入阶段 2 提交 |
| ISS-008 | P1 | RESOLVED | PyInstaller sidecar 和 Windows 安装链路仍为占位 | 阶段 9 `PKG-01` 已产出真实 onedir sidecar（`build/sidecar/weekly-report-backend.exe`，42.69 MB/148 文件），在剥离 PATH（仅 `System32`/`Windows`）的隔离环境下真实启动、`/health` 通过、迁移正确建表；`PKG-02` 已产出可安装的 NSIS 安装包并通过 `electron-builder.yml` 的 `extraResources` 把 sidecar 放在 `resources/sidecar/`（不进 ASAR）；`REL-01` 已在本机完成真实安装/升级/卸载验证（见 `progress.md` 阶段 9 记录） | 阶段 9 `PKG-01`/`PKG-02`/`REL-01`（均已交付） |
| ISS-015 | P0 | RESOLVED | 打包后的主进程间歇性抛出 `Cannot find module '@electron-toolkit/utils'` 而无法启动 | `REL-01` 真实安装验证时发现：electron-vite 默认对 main 进程的真实 npm 依赖做外部化（保留为运行期 `require(...)`），赌 electron-builder 打包时能从 `node_modules` 正确收集到它们；在本仓库的 npm workspace 布局下，`@electron-toolkit/utils` 实际提升到仓库根 `node_modules/`，而不是 `electron/node_modules/`，electron-builder 的依赖遍历在跨 workspace 场景下间歇性找不到并遗漏它——同一个安装好的 exe，连续启动 5 次中会有几次直接弹出主进程未捕获异常对话框、渲染窗口完全打不开（真实截图/UI Automation 提取的错误文本已核实，不是巧合或环境噪音）。已在 `electron.vite.config.ts` 通过 `externalizeDepsPlugin({ exclude: ['@electron-toolkit/utils'] })` 强制把该依赖打包进 `out/main/index.js`，不再依赖打包期对 `node_modules` 的收集；修复后连续 5 次全新安装+启动与 1 次 Playwright 全链路驱动均稳定通过，未再复现 | 阶段 9 `PKG-02`/`REL-01`（已修复，真实环境反复验证） |
| ISS-016 | P1 | RESOLVED | `electron/package.json` 的 npm workspace 作用域名称（`@weekly-report/electron`）在 Windows 打包路径中被错误处理 | `REL-01` 真实构建/安装时发现两处独立问题：(1) `electron-builder.yml` 的 `nsis.artifactName: ${name}-...` 用原始 package.json `name`（含 `/`）拼文件名，NSIS 把 `/` 当路径分隔符，写入不存在的 `dist/@weekly-report/` 子目录直接报错 "Can't open output file"，安装包完全生成不了；(2) electron-builder 在 `oneClick && !perMachine`（即本项目配置）下，默认安装目录名固定走 `sanitizeFileName(package.json 的 name)`（不是 `productFilename`），且未对 `@scope/` 前缀做特殊处理，导致真实安装目录被命名为畸形的 `@weekly-reportelectron`，该次安装是空目录、桌面快捷方式指向空目标、注册表卸载项完全没写入——即一次看起来"成功"（退出码 0）但实际完全没有安装任何东西的失败。已把 `electron-builder.yml` 的 `artifactName` 改为使用 `${productFilename}`（已经过安全字符校验的产物名），并把 `electron/package.json` 的 `name` 从 `@weekly-report/electron` 改为不带作用域的 `weekly-report-electron`，同步刷新根 `package-lock.json`；根 `package.json` 的 `workspaces: ["electron"]` 按目录路径匹配，不依赖该字段，改名不影响任何现有脚本 | 阶段 9 `PKG-02`/`REL-01`（已修复，重新构建安装验证正常） |
| ISS-017 | P3 | OPEN | NSIS 卸载偶发行为差异与空目录残留（均不影响数据安全） | `REL-01` 真实卸载验证时观察到两个非阻塞现象：① 直接调用注册表 `UninstallString`（不带 `/S`）在本环境中多次观察为立即退出且未执行任何卸载动作，而 `QuietUninstallString`（带 `/S`）稳定正确完成卸载——Windows 10/11 现代"设置 > 应用"卸载入口本身优先使用 `QuietUninstallString`（有该字段时不使用 `UninstallString`），本仓库注册表项确认两者均已正确写入，故真实用户经"设置"卸载预期不受影响，仅老式控制面板路径的行为未100%复核；② 卸载后 `%LOCALAPPDATA%\Programs\weekly-report-electron\` 有时会残留一个空目录（不含任何文件，被 Search Indexer/资源管理器短暂持有句柄），几秒到几分钟后通常会自然消失，不含任何数据且无安全影响 | 非阻塞；若未来需要更严格的卸载行为核验，建议在真正的干净虚拟机（而非当前开发机）上复测，排除本机残留索引句柄的干扰 |
| ISS-009 | P2 | RESOLVED | AI 上下文文档需要形成独立阶段提交 | 12 份上下文文档、启动路由和维护规则已建立并完成交叉复核 | 随本次独立文档阶段提交交付；后续每个实现阶段持续维护 |
| ISS-010 | P2 | OPEN | sidecar 孤儿进程防护未覆盖"Electron 被外部强杀"场景 | `terminateProcessTree` 已用 `taskkill /pid <pid> /t /f` 覆盖正常退出、崩溃（`uncaughtException`）、`SIGINT`/`SIGTERM`、`before-quit` 场景（手动冒烟已验证无孤儿）；但若 Electron 主进程本身被任务管理器"结束进程"或外部 `TerminateProcess` 强杀，注册的退出钩子不会执行，`process.on('exit')` 的同步兜底也依赖该事件本身被触发，理论上仍可能残留 sidecar 进程 | 需要 Windows Job Object（`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`）才能彻底杜绝，Node 原生 `child_process` 不提供该能力；作为后续可选加固项，不阻塞阶段 2 验收 |
| ISS-011 | P2 | RESOLVED | 阶段 5 初版日报详情曾混入阶段 8 `FE-07` 的企业微信占位入口 | 会破坏阶段提交边界，并让阶段 5 错误承载设置/能力占位 UI | 主 Agent 自审时已移除占位入口和 capability 页面调用；阶段 5 仅保留 `SETTING-01` 后端能力 API，UI 仍由阶段 8 实现 |
| ISS-012 | P1 | RESOLVED | 导出 xlsx 存在 Excel 公式注入风险 | 独立安全专项审查发现：日报自由文本字段允许任意字符串，`build_export_workbook` 未做转义直接写入单元格；openpyxl 会把以 `=` 开头的字符串提升为可执行公式（CWE-1236），若含此类内容的导出文件被他人在 Excel 中打开可能触发。已在 `EXPORT-02` 内修复：只对 `=` 前缀加单引号转义（不处理 `+`/`-`/`@`，避免破坏中文报告常见的列表符号），并补充专项测试覆盖公式防护与列表符号不受影响两种场景 | 阶段 6 `EXPORT-02`（随本阶段实现提交交付） |
| ISS-014 | P1 | RESOLVED | 生产模式下 sidecar 从未收到指向 `userData` 的数据目录环境变量 | 阶段 9 `PKG-01`/`PKG-02` 准备真实打包验证时发现：`SidecarManager.doStart()` 只注入 `WEEKLY_REPORT_PORT` 与运行期密钥，从未设置 `WEEKLY_REPORT_{DATA,LOG,BACKUP,EXPORT_TEMP,MANUAL_BACKUP_TEMP}_DIR`；生产 sidecar 因此会退回 `Settings` 的仓库相对默认值，在 PyInstaller 冻结后实际解析到安装目录内部，直接违反 `architecture.md` §4.3 目标目录表和 §5"安装目录视为只读"的安全边界，真实安装后首次启动会尝试写入只读目录而失败。已在 `paths.ts` 的 `SidecarLaunchPlan` 增加 `env` 字段（生产分支基于 `userDataPath` 计算五个目录 + `WEEKLY_REPORT_ENVIRONMENT=production`，开发分支保持空对象不影响既有 `.local-data/` 行为），`manager.ts` 合并进子进程环境，`index.ts` 传入 `app.getPath('userData')`；已补充/更新单元测试 | 阶段 9 `PKG-01`/`PKG-02`（已修复） |
| ISS-013 | P2 | OPEN | `test_access_token.py`/`test_auth_api.py` 的“篡改 Token”测试偶发误报通过 | 该测试翻转 JWT 签名末位字符来模拟篡改；本次 QA 全量跑批中曾出现该用例断言失败（篡改后的 Token 仍被判定为有效），单独重跑及后续多次全量重跑均未复现。怀疑是 base64url 编码在签名末尾分组存在冗余位，特定随机签名下翻转末位字符不改变解码后的字节值，属于测试本身构造方式的偶发边界，而非本次改动引入的回归（本次未改动 `access_token.py`/`jwt_secret.py`/`auth.py`） | 非阻塞；后续如需彻底消除可改为翻转签名中段字节或改用专门破坏签名的构造方式，不应仅翻转最后一个 base64 字符 |

| ISS-018 | P1 | MITIGATED | CR-20260807-01 将日报从“同日唯一、单篇三态归档”改为“同日多条目、日期级汇总归档”，与 V1 schema/API/周报/导出直接冲突 | BE-10A 已交付日期容器、正式单来源快照、V1 数据/周报 JSON 迁移和受限 downgrade；旧日报 API 暂由兼容桥维持同日一篇，尚未开放多条目 | BE-10B～10E 完成同日多篇事务、下游适配、Electron 与 E2E 后才能 RESOLVED |
| ISS-019 | P1 | MITIGATED | admin 撤销其他用户提交改变了现有“admin 不查看/操作他人业务数据”的权限边界 | 方案采用专用最小元数据查询、正文/模板不选择不返回、原因必填和独立脱敏审计；待确认且尚未实现 | 阶段 10B 实现权限/审计并以 SQL 选择列、API 响应和越权测试证明后关闭 |
| ISS-020 | P1 | RESOLVED | 首次初始化改为普通用户 + 默认管理员双账号 | BE-10A 已实现固定 `admin`、密码分别 Argon2id 哈希、双账号及双方默认资源原子创建、admin 首次登录强制改密、管理员重置后强制改密；顺序/并发重复初始化、事务回滚、哈希不同和业务 API 拦截均有自动化测试 | 阶段 10A 已完成并通过后端 199 项全量测试；Electron 强制改密页面属于 FE-10，不影响后端风险关闭 |
| ISS-021 | P1 | MITIGATED | “用户管理支持删除”与 V1 永久保留业务记录、外键 RESTRICT 和无业务删除 API 冲突 | 已冻结为无业务记录可物理删除、有业务记录只能停用，并增加当前账号/末位管理员/确认用户名/原因保护；尚未实现 | 阶段 10B 实现安全删除和外键竞态测试后关闭；级联永久删除仍不在范围 |
| ISS-022 | P2 | MITIGATED | 统计指标需要统一日历口径 | 已冻结自然日完成率、来源条目篇数、`week_start` 周报归属、今天/昨天连续记录和未来月 null 规则；尚未实现 | 阶段 10C/10D 完成查询、界面和跨月/闰日测试后关闭 |

## 2. 非阻塞产品/发布风险

| ID | 级别 | 状态 | 风险 | 当前决策/缓解 | 重新评审条件 |
|---|---|---|---|---|---|
| RISK-001 | P2 | MITIGATED | SQLite 不做整库加密，设备离线泄露仍可能暴露正文 | V1 已接受：密码 Argon2id、Token safeStorage、权限隔离；提示本地数据敏感性 | 用户要求磁盘泄露防护或产品进入受监管场景 |
| RISK-002 | P2 | MITIGATED | 周报确认重生成会覆盖人工编辑且 V1 无恢复 | UI 必须醒目确认；API 必须要求显式 `confirm_overwrite` 和乐观锁 | 用户要求历史比较/恢复时设计版本表并进入 P2 |
| RISK-003 | P2 | MITIGATED | PyInstaller 体积和杀软误报 | 采用 onedir、许可证清单和真实安装验证均已完成（阶段 9）：`build/sidecar/` 实测 42.69 MB/148 文件，`weekly-report.exe` 主进程与 `weekly-report-backend.exe` 均未签名（`Get-AuthenticodeSignature` 确认 `NotSigned`），本机 Windows Defender 默认设置下完成多次真实安装/启动未观测到拦截或误报；未做正式跨厂商杀软兼容性矩阵测试，也未做代码签名 | 若正式发布前需要覆盖更多杀软厂商结果或购买签名证书，需单独立项验证 |
| RISK-004 | P2 | MITIGATED | admin 手动备份包含所有用户数据 | 已随阶段 8 `BACKUP-01`/`FE-07` 实现并通过独立安全审查：仅 admin、创建者本人下载（40401 隔离）、进程内随机 ULID 短期映射、15 分钟懒过期加启动残留清理、`/settings` 界面创建前醒目敏感性确认；风险本身随功能存在长期保留，故维持 `MITIGATED` 而非 `RESOLVED` | 若备份需要细分用户范围或外部存储，先更新契约与安全设计 |
| RISK-005 | P2 | MITIGATED | 业务自动化覆盖仍需随模块扩展 | 当前后端 186 项、前端 108 项、真实 sidecar 集成 2 项、Playwright E2E 5 项（初始化→登录→模板→日报→导出→周报主链路及登录失败/字段校验/权限拒绝/乐观锁冲突失败路径）均通过，阶段 9 `QA-09` 已交付全链路 E2E 覆盖 | 各阶段按 `task.md` 添加契约、权限、并发、集成和 E2E 覆盖 |

## 3. 当前阻塞项

当前无需要用户立即决策的 `BLOCKED` 项。`architecture.md` 已为首发平台、管理员数据权限、周报覆盖策略和数据库加密给出 V1 默认决策，可继续实现。

出现以下情况时必须把对应任务标为 `BLOCKED`：

- 需求与架构/API/数据库文档互相冲突，且不同选择会改变行为或数据模型。
- 需要改变已接受 ADR、安全边界、所有权或状态机。
- 需要新增未登记接口/错误码，或需要跨阶段混入不可拆分变更。
- 工作树存在其他 Agent 对同一文件的未协调修改。

## 4. 问题关闭要求

问题只有在满足以下条件后才能标为 `RESOLVED`：

1. 对应实现、自动化测试和文档已完成。
2. 适用质量门禁通过，结果写入 `task.md`。
3. 独立审查无未解决 P0/P1。
4. 所属阶段已创建独立 Conventional Commit；若仅临时缓解，状态应为 `MITIGATED` 而非 `RESOLVED`。
