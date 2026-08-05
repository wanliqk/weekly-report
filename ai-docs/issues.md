# 问题、风险与阻塞记录

> 更新日期：2026-08-05
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
| ISS-006 | P0 | MITIGATED | 所有权与业务 API 尚未完整实现 | 阶段 4 认证已提交并通过独立审查；阶段 5 模板、设置、日报状态机及 owner 强制过滤已实现、通过门禁和主 Agent 自审，等待独立审查；周报、导出等后续业务 API 仍待各阶段实现 | 阶段 5 独立审查后确认日报边界；后续业务模块继续复用 owner 条件，全部核心业务完成后关闭 |
| ISS-007 | P2 | OPEN | Element Plus 当前全量引入 | renderer 生产包偏大，阶段基线曾观测主 JS 约 2.6 MB；会影响启动和构建告警 | 前端页面组件稳定后改为按需引入，并以构建体积对比验证；不得为此提前混入阶段 2 提交 |
| ISS-008 | P1 | OPEN | PyInstaller sidecar 和 Windows 安装链路仍为占位 | `build/sidecar` 只有说明文件，安装包不能交付可运行后端 | 阶段 9 `PKG-01`/`PKG-02`：onedir、extraResources、无 Python 干净机验证 |
| ISS-009 | P2 | RESOLVED | AI 上下文文档需要形成独立阶段提交 | 12 份上下文文档、启动路由和维护规则已建立并完成交叉复核 | 随本次独立文档阶段提交交付；后续每个实现阶段持续维护 |
| ISS-010 | P2 | OPEN | sidecar 孤儿进程防护未覆盖"Electron 被外部强杀"场景 | `terminateProcessTree` 已用 `taskkill /pid <pid> /t /f` 覆盖正常退出、崩溃（`uncaughtException`）、`SIGINT`/`SIGTERM`、`before-quit` 场景（手动冒烟已验证无孤儿）；但若 Electron 主进程本身被任务管理器"结束进程"或外部 `TerminateProcess` 强杀，注册的退出钩子不会执行，`process.on('exit')` 的同步兜底也依赖该事件本身被触发，理论上仍可能残留 sidecar 进程 | 需要 Windows Job Object（`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`）才能彻底杜绝，Node 原生 `child_process` 不提供该能力；作为后续可选加固项，不阻塞阶段 2 验收 |
| ISS-011 | P2 | RESOLVED | 阶段 5 初版日报详情曾混入阶段 8 `FE-07` 的企业微信占位入口 | 会破坏阶段提交边界，并让阶段 5 错误承载设置/能力占位 UI | 主 Agent 自审时已移除占位入口和 capability 页面调用；阶段 5 仅保留 `SETTING-01` 后端能力 API，UI 仍由阶段 8 实现 |

## 2. 非阻塞产品/发布风险

| ID | 级别 | 状态 | 风险 | 当前决策/缓解 | 重新评审条件 |
|---|---|---|---|---|---|
| RISK-001 | P2 | MITIGATED | SQLite 不做整库加密，设备离线泄露仍可能暴露正文 | V1 已接受：密码 Argon2id、Token safeStorage、权限隔离；提示本地数据敏感性 | 用户要求磁盘泄露防护或产品进入受监管场景 |
| RISK-002 | P2 | MITIGATED | 周报确认重生成会覆盖人工编辑且 V1 无恢复 | UI 必须醒目确认；API 必须要求显式 `confirm_overwrite` 和乐观锁 | 用户要求历史比较/恢复时设计版本表并进入 P2 |
| RISK-003 | P2 | OPEN | PyInstaller 体积和杀软误报 | 采用 onedir、许可证清单和干净机验证；发布时评估签名 | 首个 sidecar 包产出后测量体积、启动耗时和杀软结果 |
| RISK-004 | P2 | MITIGATED | admin 手动备份包含所有用户数据 | 仅 admin、创建者下载、随机短期 ID、15 分钟过期、UI 敏感提示 | 若备份需要细分用户范围或外部存储，先更新契约与安全设计 |
| RISK-005 | P2 | MITIGATED | 业务自动化覆盖仍需随模块扩展 | 当前后端 117 项、前端 54 项、真实 sidecar 集成 2 项均通过；阶段 5 已新增模板、设置、日报快照/状态机、所有权、并发和动态表单纯函数覆盖。周报、导出及全链路 Playwright 仍待后续阶段 | 各阶段按 `task.md` 添加契约、权限、并发、集成和 E2E 覆盖 |

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
