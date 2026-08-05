# 问题、风险与阻塞记录

> 更新日期：2026-08-05
> 严重度：P0 安全/数据损失；P1 核心功能/契约；P2 可维护性/体验；P3 建议
> 状态：`OPEN`、`MITIGATED`、`RESOLVED`、`BLOCKED`

## 1. 当前开放项

| ID | 级别 | 状态 | 问题/风险 | 当前影响 | 处理条件/归属 |
|---|---|---|---|---|---|
| ISS-001 | P1 | OPEN | Electron 尚未托管 FastAPI sidecar | 当前 `npm run dev` 由 `concurrently` 独立启动两端；生产启动链路不存在 | 阶段 2 `DESK-02`：动态端口、进程启停、开发/生产路径和退出清理完成 |
| ISS-002 | P0 | OPEN | runtime secret 尚未生成和校验 | 回环端口不是身份边界；在此之前不得开放业务 API | 阶段 2 `DESK-02`/`BE-02`/`DESK-03`：Main 每次启动随机生成，经最小 preload 交给 renderer API 客户端且仅内存持有，除 `/health` 外强制校验 |
| ISS-003 | P1 | OPEN | `/health` 未达到冻结契约 | 当前只返回 `data.status`；缺少版本字段及明确 `Cache-Control: no-store` | 阶段 2 `BE-02`：按 `api.md` 补齐响应与测试，再由 Electron 依契约轮询 |
| ISS-004 | P1 | OPEN | 业务窗口不等待后端健康成功 | 后端启动失败时仍会展示工程首页，没有可诊断错误流程 | 阶段 2 `DESK-03`：健康成功后展示业务窗口，失败页提供重试和脱敏日志入口 |
| ISS-005 | P1 | OPEN | 数据库与迁移基础尚未实现 | 当前没有 Engine/Session、ORM、Alembic revision、PRAGMA 或迁移前备份，任何数据均不可持久化 | 阶段 3 `DB-01`..`DB-03` 完成并通过新库/失败/备份测试 |
| ISS-006 | P0 | OPEN | 认证、所有权与业务 API 尚未实现 | 当前没有 JWT、runtime 双校验、用户隔离；不得把占位模块暴露为可用功能 | 阶段 4 起按依赖逐步实现；每个 Repository 查询强制 owner 条件 |
| ISS-007 | P2 | OPEN | Element Plus 当前全量引入 | renderer 生产包偏大，阶段基线曾观测主 JS 约 2.6 MB；会影响启动和构建告警 | 前端页面组件稳定后改为按需引入，并以构建体积对比验证；不得为此提前混入阶段 2 提交 |
| ISS-008 | P1 | OPEN | PyInstaller sidecar 和 Windows 安装链路仍为占位 | `build/sidecar` 只有说明文件，安装包不能交付可运行后端 | 阶段 9 `PKG-01`/`PKG-02`：onedir、extraResources、无 Python 干净机验证 |
| ISS-009 | P2 | RESOLVED | AI 上下文文档需要形成独立阶段提交 | 12 份上下文文档、启动路由和维护规则已建立并完成交叉复核 | 随本次独立文档阶段提交交付；后续每个实现阶段持续维护 |

## 2. 非阻塞产品/发布风险

| ID | 级别 | 状态 | 风险 | 当前决策/缓解 | 重新评审条件 |
|---|---|---|---|---|---|
| RISK-001 | P2 | MITIGATED | SQLite 不做整库加密，设备离线泄露仍可能暴露正文 | V1 已接受：密码 Argon2id、Token safeStorage、权限隔离；提示本地数据敏感性 | 用户要求磁盘泄露防护或产品进入受监管场景 |
| RISK-002 | P2 | MITIGATED | 周报确认重生成会覆盖人工编辑且 V1 无恢复 | UI 必须醒目确认；API 必须要求显式 `confirm_overwrite` 和乐观锁 | 用户要求历史比较/恢复时设计版本表并进入 P2 |
| RISK-003 | P2 | OPEN | PyInstaller 体积和杀软误报 | 采用 onedir、许可证清单和干净机验证；发布时评估签名 | 首个 sidecar 包产出后测量体积、启动耗时和杀软结果 |
| RISK-004 | P2 | MITIGATED | admin 手动备份包含所有用户数据 | 仅 admin、创建者下载、随机短期 ID、15 分钟过期、UI 敏感提示 | 若备份需要细分用户范围或外部存储，先更新契约与安全设计 |
| RISK-005 | P2 | OPEN | 当前测试只覆盖工程骨架 | 现有 1 个前端单元测试、3 个后端健康测试不能证明业务正确 | 各阶段由 Agent C 按 `task.md` 添加契约、权限、并发、集成和 E2E 覆盖 |

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
