# Agent 启动上下文

> 适用分支：`v1`
> 快照日期：2026-08-05
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
- Electron 已具备单实例窗口基线；窗口启用 `contextIsolation` 与 sandbox，禁用 `nodeIntegration`，并拒绝任意新窗口及非当前页面导航。
- preload 当前只暴露只读的运行平台信息。
- renderer 当前只有工程状态首页和一项状态文案单元测试，业务页面尚未接入。
- FastAPI/uv/Python 3.12 项目已建立，绑定配置只允许 `127.0.0.1`，Uvicorn 固定单 worker，端口默认可设为动态端口 `0`。
- 后端目前只有 `/health`、统一成功响应模型、请求 ID 中间件、受限 CORS/Host 配置及对应测试。
- SQLAlchemy、Alembic、认证、业务模型、Repository、Service、业务 API、sidecar 进程管理和发布产物尚不能从当前代码证明已实现。
- `build/sidecar/` 当前只是发布产物占位目录。

“依赖已列入清单”不等于对应业务已完成；“技术方案已描述”也不等于已经落地。

## 5. 当前阶段与下一步

- 已完成阶段：工程基线。
- 尚未开始阶段：Desktop Bootstrap。
- 下一阶段目标：Electron 管理 FastAPI sidecar 生命周期，完成动态端口、随机 `runtime_secret`、健康检查、开发/生产启动差异、数据/日志目录、安全 preload 契约和退出清理。
- Desktop Bootstrap 完成前，不得把数据库、认证、日报、周报或导出能力标为已完成。

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
