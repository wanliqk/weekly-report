# 编码与协作规范

> 状态：强制执行（V1）
> 更新日期：2026-08-05
> 适用范围：所有开发 Agent、审查 Agent 和人工贡献者

## 0. 规范优先级与状态表达

- 当前工作树中的 `AGENTS.md` 是仓库执行约束；`docs/需求理解.md` 和 `docs/方案设计.md` 分别是产品与技术事实源；`ai-docs/` 用于快速恢复上下文和追踪进度。
- `architecture.md`、`modules.md`、`database.md`、`api.md` 中的“目标”“已批准”不等于“已实现”。完成状态只由代码、测试结果、`task.md` 和 `progress.md` 共同证明。
- 文档发生冲突时不得自行选择更方便的规则：先停止冲突范围的实现，在 `issues.md` 记录差异并请求确认。
- 只检查当前 `v1` 工作树；未经用户明确授权，不得读取或借用其他分支及历史提交。

## 1. 开发前置流程

每次开始任务前必须：

1. 先读取 `agent-context.md`，再按其路由读取任务相关文档；不得为形式完整而无目的加载全部长文档。
2. 在 `task.md` 确认任务 ID、依赖、范围、验收标准和允许修改的模块。
3. 检查工作区现有改动，避免覆盖其他 Agent 的提交。
4. 判断任务是否符合 `architecture.md` 的依赖方向和安全边界。
5. 若存在冲突或契约缺口，将任务标为 `BLOCKED` 并记录问题；不得直接修改核心架构。

## 2. 通用原则

- 保持变更最小且围绕单一任务；禁止无关重构、批量改名和顺手升级依赖。
- 业务规则必须只有一个权威实现位置，前端校验只改善体验，后端仍需完整校验。
- 禁止硬编码端口、安装路径、用户目录、JWT 密钥、runtime secret 和环境相关绝对路径。
- 所有外部输入均不可信：HTTP 参数、JSON、IPC、文件名、环境变量和数据库旧数据必须校验。
- 代码、测试、迁移和文档要在同一任务中保持一致。
- 不得在日志、异常、测试快照或提交记录中泄露密码、Token、密钥或真实工作正文。

## 3. 命名与文件

- Python：模块/函数/变量 `snake_case`，类 `PascalCase`，常量 `UPPER_SNAKE_CASE`。
- TypeScript/Vue：变量/函数 `camelCase`，组件/类型 `PascalCase`，常量按项目约定使用 `UPPER_SNAKE_CASE`。
- API 和数据库字段统一 `snake_case`；前端在 API 适配层转换时集中处理，不散落页面。
- 布尔名称使用 `is_`、`has_`、`can_`、`should_` 等明确前缀。
- 时间字段使用 `_at`，业务日期使用 `_date` 或固定 `week_start/week_end`。
- 文件按业务能力命名，避免 `utils.py`、`common.ts` 之类无限扩张的容器。
- 文本文件统一 UTF-8，行尾遵循作用域最近的 `.editorconfig`；不得在功能任务中批量转换无关文件。文案可使用中文，标识符和协议字段使用英文。

## 4. Python/FastAPI 规范

### 4.1 分层

- Router 只做 schema 解析、依赖注入、调用 Service 和返回协议响应。
- Service 表达业务用例、状态机和事务，不依赖 FastAPI Request/Response。
- Repository 只负责数据访问；业务资源查询必须包含 `owner_id`。
- ORM Model 不直接作为 API schema；Pydantic 输入/输出模型分离。
- 禁止 Router 直接访问 Session、Repository 跨过 Service 执行业务写操作。

### 4.2 类型与异步

- 所有公开函数、Service、Repository 和 schema 字段必须有类型注解。
- 不使用可变默认参数；Optional/nullability 必须显式。
- 异步调用链不混入阻塞 I/O；openpyxl 等阻塞工作通过明确的线程执行策略处理。
- 不使用宽泛 `except Exception` 吞错；转换异常后保留安全的 cause 和请求 ID。

### 4.3 事务与时间

- Service 明确事务范围；禁止在 Repository 内隐式提交。
- 写操作使用短事务；网络、文件生成和长计算不得置于数据库事务内。
- 时间由统一 Clock/UTC helper 获取，测试可替换；禁止到处直接调用本地时间。
- 乐观锁使用 `WHERE id=? AND user_id=? AND version=?` 条件更新，并验证受影响行数。

### 4.4 质量门禁

- Ruff format/check 通过。
- mypy 对项目配置的范围零错误；不得用无说明的 `type: ignore`。
- pytest 覆盖正常、权限、校验、冲突、重复请求和异常路径。

## 5. TypeScript/Vue 规范

- 启用严格 TypeScript；禁止无理由 `any`、非空断言和类型强转绕过错误。
- Vue 组件使用 Composition API 和 `<script setup lang="ts">`。
- 页面不直接调用 Axios，统一通过 `src/api`；错误映射和 Token 处理放拦截层。
- Pinia 只保存真正跨页面状态；服务端列表和详情不做无边界全局缓存。
- 动态日报字段由一套字段渲染器按 `field_type` 映射，禁止每个页面重复实现。
- 表单同时展示客户端提示与服务端字段错误；提交失败不得清空输入。
- 所有异步操作显示 loading 并防重复点击；最终正确性仍由服务端约束保证。
- 路由 meta 明确匿名/登录/admin 权限，导航守卫只用于界面控制，不替代后端鉴权。
- 用户可见文案不展示堆栈、内部路径、SQL 或原始未知错误。
- ESLint、Prettier、TypeScript 检查和 Vitest 必须通过。

## 6. Electron 规范

- 桌面代码固定在 `electron/src/main`、`electron/src/preload`、`electron/src/renderer`；禁止另建根 `frontend/` 或 electron-egg 风格业务 controller/service。
- electron-vite 配置只维护在 `electron/electron.vite.config.ts`；构建产物固定为 `electron/out`，源文件不得直接进入生产包。
- `contextIsolation=true`、`nodeIntegration=false`、`sandbox=true` 不得弱化。
- preload 只暴露按用途命名的白名单方法；参数和返回值必须可序列化且有类型。
- IPC channel 使用集中常量和 allowlist；Main 端再次校验调用参数。
- 禁止通过 contextBridge 暴露通用 `ipcRenderer` 或 `@electron-toolkit/preload` 的完整 `electronAPI`；每个能力必须包装为具体方法。
- 禁止 renderer 直接获得任意文件系统、进程、shell、环境变量或数据库能力。
- sidecar 仅绑定回环动态端口；进程参数和日志必须脱敏。
- sidecar 生产路径从 `process.resourcesPath` 解析；禁止依赖 `cwd`、`__dirname` 对源码树的偶然指向或开发机绝对路径。
- safeStorage 不可用时必须显式降级/提示，不得静默改存明文。
- 外部 URL 使用协议和域名 allowlist，禁止直接 `shell.openExternal(userInput)`。
- 应用退出、崩溃和重复启动场景必须清理 sidecar，不能误删用户数据。
- electron-vite 环境变量必须按 main/preload/renderer 前缀隔离；JWT、runtime secret、密码、数据库路径不得写入 `VITE_`、`RENDERER_VITE_` 或任何会被静态打包的变量。
- main/preload 新增依赖时必须审查 electron-vite externalization 与 electron-builder 收集结果；不得使用未声明的幻影依赖。sandbox preload 如需第三方依赖，应完整打包或改为 Main 白名单能力，不得关闭 sandbox。
- 开发、CI 和发布统一使用 Node.js 22.12+ LTS、npm 10+，并从仓库根执行 npm workspace 命令。

## 7. 数据库与迁移规范

- schema 改动必须通过新 Alembic migration；禁止修改已发布迁移。
- migration 名称说明业务意图，升级和降级路径明确。
- 约束、索引和外键名称显式、稳定，和 `database.md` 一致。
- JSON 写入前使用版本化 schema 校验；读取历史 JSON 时提供兼容策略或明确迁移。
- 禁止在日志打印 SQL 参数中的正文和凭据。
- 测试至少覆盖新库升级和上一版本库升级；迁移前备份失败时禁止继续。

## 8. API 与错误处理

- 实现必须遵循 `api.md`，不得自行增加未登记字段、接口或错误码。
- HTTP 状态表达协议，业务 `code` 稳定；禁止所有错误都返回 HTTP 200。
- 404 用于不存在或不可见资源；不得通过不同消息泄露他人资源存在性。
- 参数错误提供安全的字段定位；内部异常返回 50001 和请求 ID，不返回堆栈。
- 文件下载验证 owner、状态和过期时间，设置安全文件名，不返回内部绝对路径。

## 9. 测试规范

### 9.1 测试分层

- 单元：日期边界、状态机、模板值、列规划、错误映射等纯逻辑。
- API：认证、所有权、统一响应、唯一约束、乐观锁和事务回滚。
- 前端：动态表单、路由守卫、拦截器、确认对话框和错误保留。
- 集成：Electron/sidecar 生命周期、迁移、safeStorage、文件保存。
- E2E：初始化到周报的主链路以及升级链路。

### 9.2 测试质量

- 测试名称描述行为和预期，不依赖执行顺序。
- 每个测试独立创建数据；不使用真实用户目录或生产数据库。
- 时间、随机 ID、文件目录和 sidecar 进程应可注入/替换。
- 不能仅断言 HTTP 200；必须验证状态、业务 code、数据库结果和副作用。
- Bug 修复先增加可复现测试，再修改实现。

## 10. Git 与任务协作

- 分支建议：`feat/<task-id>-short-name`、`fix/<task-id>-short-name`、`chore/<task-id>-short-name`。
- 提交信息：`type(scope): summary [TASK-ID]`，例如 `feat(auth): add token version validation [BE-04]`。
- 一个提交保持可理解和可验证；格式化变更不要与业务改动大面积混合。
- 提交前更新 `task.md` 的状态、实际交付物、测试结果和遗留风险。
- 不提交 `.env`、数据库、日志、导出文件、备份、密钥、构建缓存和本机路径。
- 不改写或丢弃其他 Agent 的未提交改动；发生重叠立即停止并协调。
- 技术方案按阶段实现。每个阶段完成并通过适用质量门禁后，必须复核工作树并创建一个独立 Conventional Commit；不得把下一阶段实现混入当前提交。
- 创建本地提交不代表允许推送远端；只有用户明确授权后才能 push。
- 多 Agent 并行时必须先划分互斥文件范围和依赖顺序；所有 Agent 共享工作树，主责 Agent 在提交前统一检查差异和运行质量门禁。

## 11. 代码审查规范

审查按优先级输出问题：

- `P0`：安全漏洞、数据丢失、越权、核心架构破坏，禁止合并。
- `P1`：业务错误、事务/并发问题、契约不符、关键测试缺失，修复后合并。
- `P2`：可维护性、边界测试或用户体验问题，可在本任务修复或登记后续任务。
- `P3`：非阻塞建议，不应以个人风格阻塞合并。

每条审查意见必须包含：级别、文件与行号、触发场景、实际影响、建议方向。审查者重点检查：

- 是否违反 `architecture.md` 的分层和唯一业务入口。
- 是否实现 `requirements.md` 的状态机、所有权和默认决策。
- API、错误码、数据库结构是否与文档一致。
- 事务、唯一约束、乐观锁和重复请求是否可靠。
- Electron 本地攻击面、Token、运行期密钥和日志是否安全。
- 测试是否覆盖失败路径，而不只覆盖 happy path。

审查完成后在 `task.md` 对应任务记录 Reviewer、结论和未解决项。存在 P0/P1 时任务不得标记 `DONE`。

## 12. 完成定义（DoD）

- 代码、测试、文档和迁移均已提交且范围一致。
- 全部适用的 lint、类型检查、单元/API/集成测试通过。
- 不含未批准架构变更、临时接口、硬编码敏感值和跨层访问。
- 关键异常有用户可理解的反馈，日志有请求 ID 且完成脱敏。
- 另一名 Agent 或技术负责人完成代码审查，无未解决 P0/P1。
- `task.md` 已记录交付物、验证命令、结果和遗留风险。
- `progress.md` 已更新当前真实能力与未实现项；对应阶段已经形成独立本地 Conventional Commit，且未擅自推送。
