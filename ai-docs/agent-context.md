# Agent 启动上下文

> 适用分支：`v1`
> 快照日期：2026-08-06
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
- 阶段 8 admin 手动整库备份 API（checkpoint+backup API 生成、进程内 `BackupRegistry`、15 分钟懒过期、仅创建者下载）与设置/企业微信占位/管理员备份 Vue 页面已完成实现、自测、质量门禁、独立审查（含专项安全审查），三项任务统一为 `DONE`；发布产物（PyInstaller/安装包）尚未实现。
- `build/sidecar/` 当前只是发布产物占位目录。

“依赖已列入清单”不等于对应业务已完成；“技术方案已描述”也不等于已经落地。

## 5. 当前阶段与下一步

- 已完成阶段：工程基线（`3a9fdbc`）、Desktop Bootstrap（`7386cae`）、数据基础与 API Foundation（`8480515`）、认证与用户管理（`1a50e75`）、模板、设置与日报闭环（`1d965fe`）、查询导出与桌面保存（`d6ab86e`）、周报闭环（`346b0ea`）、设置能力与受控备份（阶段 8，提交待创建后回填）。
- 当前阶段：阶段 8 已完成；阶段 9 质量与发布尚未开始。
- 下一步：进入阶段 9（`QA-09` 全链路 Playwright/E2E、`PKG-01` PyInstaller sidecar、`PKG-02` electron-builder 安装包、`REL-01` 干净机安装/升级/卸载验证）。
- 阶段 9 完成前，不得把发布能力标为已完成；未获授权不得推送远端。

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
- 企业微信在 V1 只做“功能暂未开放”占位，不发起外部请求。

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
