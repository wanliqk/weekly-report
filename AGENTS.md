# 仓库贡献指南

## 分支定位与信息边界

`v1` 是本项目全新的主线基准，按主分支管理。除非用户明确要求，不得查看、引用、复制或合并其他分支及既往 Git 历史中的实现、配置、命令和约定。所有判断仅以当前工作树为准：`docs/需求理解.md` 定义产品范围，`docs/方案设计.md` 定义技术架构；实现与文档冲突时先修正文档或请求确认。

## 架构与目录

代码按技术方案组织：`electron/` 包含 Electron main、preload 和 Vue 3 renderer；`backend/` 包含 FastAPI 应用、Alembic 迁移与测试；`build/` 存放图标、安装器和 sidecar 打包配置；`docs/` 存放需求与设计。

Electron 只负责桌面生命周期和受限 IPC，Vue 只通过 REST API 访问业务数据。所有业务写操作必须进入 FastAPI，并遵循 `API → Service → Repository → Model/DB`；SQLite 只能由单个后端进程访问。

## 构建、测试与开发

工程基线应统一提供以下命令：

- `npm ci`：安装根工作区锁定依赖。
- `npm run dev`：启动 Electron、Vue 与本地 FastAPI 开发链路。
- `npm run lint`、`npm run typecheck`、`npm test`：执行前端质量门禁。
- `npm run build`、`npm run build:win`：生成生产构建和 Windows 安装包。
- 在 `backend/` 运行 `uv sync --frozen`、`uv run ruff check .`、`uv run mypy`、`uv run pytest`：验证 Python sidecar。

开发环境固定为 Windows 10/11、PowerShell 7、Node.js 22.12+、npm 10+、Python 3.12。清单尚未建立时应先完成工程基线，不得伪造命令结果。

## 编码与接口规范

TypeScript/Vue 使用两个空格缩进，Python 使用四个空格缩进。前端使用 Prettier、ESLint；后端使用 Ruff（每行不超过 100 字符）和严格模式 mypy。Vue 组件用 `PascalCase`，TypeScript 标识符用 `camelCase`，Python 与 API 字段用 `snake_case`。

API 基础路径为 `/api/v1`，统一返回 `{code,msg,data}`；时间使用带时区的 ISO 8601，业务日期使用 `YYYY-MM-DD`。API 层不得直接操作 ORM，Repository 不得承载业务状态机。

## 测试规范

后端使用 pytest/httpx，渲染进程使用 Vitest，关键桌面流程使用 Playwright。Python 测试命名为 `test_*.py`，Vue 测试放在 `__tests__/*.test.ts`，Electron 测试命名为 `*.test.mjs`。重点覆盖权限隔离、日报状态流转、唯一约束、跨年周与闰日、并发重复操作、数据库迁移及 sidecar 启停。

## 提交与拉取请求

从 `v1` 起统一采用 Conventional Commits，例如 `feat(daily): 增加日报归档`、`fix(auth): 修复令牌失效校验`。每个提交只处理一个明确问题。拉取请求必须说明变更范围、关联任务、验证命令及结果；界面变更附截图，并明确标注数据库、API、安全或打包影响。

代码实现按技术方案分阶段推进。每个阶段完成并通过对应质量门禁后，必须复核工作树并创建一个独立的 Conventional Commit；不得把下一阶段的实现混入当前阶段提交。创建本地提交不代表允许推送远端，推送仍需用户明确授权。

## 安全与代理执行约束

FastAPI 只监听 `127.0.0.1` 动态端口，禁止绑定 `0.0.0.0` 或启动多 worker。Electron 必须启用 `contextIsolation` 和 sandbox、禁用 `nodeIntegration`；JWT 由 `safeStorage` 保存，不得写入 `localStorage`。日志不得包含密码、JWT、运行时密钥或报告正文；不得提交 `.env`、本地数据库、日志和构建产物。

自动化操作使用 PowerShell 7 语法，文件检索优先使用 `rg`，不得混用 Bash heredoc 或转义规则。修改前只检查当前 `v1` 工作树；未经明确授权，不得通过其他分支或历史提交补全信息。
