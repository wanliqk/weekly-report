# AI 协作上下文

`ai-docs/` 是面向 AI Agent 的快速上下文层，用于把产品范围、架构约束、模块边界、任务状态和协作规则组织成便于检索的短文档。它不能替代上游需求、技术方案或当前代码，也不能把计划中的能力描述为已经实现。

## 1. 信息优先级

发生冲突时按以下顺序判断：

1. 用户在当前对话中的最新明确指令。
2. 当前工作树中的 `AGENTS.md`。
3. `docs/需求理解.md` 与 `docs/方案设计.md`。
4. 当前代码与锁文件，用于判断“现在实际实现了什么”。
5. `ai-docs/` 中的派生汇总。

当前实现优先于 `ai-docs/` 判断完成状态，但不能反向覆盖已确认的需求和设计。如果实现与上游文档冲突，不得自行把实现认定为新规范：先在 `ai-docs/issues.md` 记录差异，并修正文档或请求用户确认。

## 2. 文档目录

| 文件 | 用途 | 何时读取 |
|---|---|---|
| `README.md` | AI 文档入口、优先级和维护规则 | 每次进入项目 |
| `requirements.md` | V1 产品范围、业务规则和验收基线 | 判断做什么、是否越界 |
| `architecture.md` | 总体架构、安全边界和运行链路 | 设计或跨模块修改前 |
| `modules.md` | 模块职责、依赖方向和代码落点 | 划分任务、定位代码时 |
| `database.md` | 数据模型、约束、事务和迁移规则 | 数据层工作前 |
| `api.md` | REST API、响应结构和错误码契约 | 前后端接口工作前 |
| `coding-rule.md` | Windows、编码、测试、安全和提交规范 | 修改代码或运行命令前 |
| `task.md` | 可执行任务、依赖、状态和验收门禁 | 领取和推进任务时 |
| `progress.md` | 已完成事实、当前阶段和下一步 | 恢复上下文时 |
| `decisions.md` | 已采用技术决策及其影响 | 遇到方案选择时 |
| `issues.md` | 未解决问题、阻塞和文档/实现差异 | 遇到异常或冲突时 |
| `agent-context.md` | Agent 启动必读顺序和当前事实快照 | 每个新会话首先读取 |

## 3. 推荐使用方式

新 Agent 先按 `agent-context.md` 的顺序建立上下文，再从 `task.md` 选择依赖已满足的任务。涉及数据库、API 或具体模块时，只补读对应专题文档和必要源码，避免无目的加载整个仓库。

任务实施期间应持续区分以下内容：

- **事实**：可由当前工作树、质量门禁结果或已创建的本地提交直接证明。
- **已确认约束**：来自用户、`AGENTS.md`、需求或技术方案，尚未实现也必须遵守。
- **计划**：准备实施但尚未由代码和验证结果证明的内容。
- **问题**：无法安全推断、存在冲突或阻塞的内容。

## 4. 维护规则

- 产品范围变化：先更新 `docs/需求理解.md`，再同步 `requirements.md` 和受影响专题文档。
- 架构或接口变化：先更新 `docs/方案设计.md`，再同步 `architecture.md`、`database.md`、`api.md` 或 `decisions.md`。
- 任务状态变化：同步更新 `task.md` 与 `progress.md`；只有通过对应验证后才能标记完成。
- 发现冲突或阻塞：写入 `issues.md`，说明证据、影响和待确认事项。
- 每个实现阶段通过质量门禁后创建独立 Conventional Commit；本地提交不等于允许推送远端。
- 不在这些文档中记录密码、JWT、runtime secret、报告正文、本地数据库内容或其他敏感数据。
- 不引用其他分支或既往 Git 历史来补全上下文，除非用户明确授权。

## 5. 当前阶段

截至 2026-08-09，V1 规划的全部 9 个阶段和 CR-20260807-01 第二版增量均已交付。CR-20260808-02 企业微信日报反向同步已完成 `WECOM-00`（敏感样例治理）、`WECOM-01`（需求/技术方案文档）、`WECOM-02`（三张 ORM 表/Repository/Pydantic 配置契约/迁移）、`WECOM-03`（Electron Main 登录窗口/`safeStorage` Cookie jar/窄 IPC/Main-only secret）、`WECOM-04`（`WeComInternalClient` 三方法/Cookie URL 筛选/六种分类异常）、`WECOM-05`（`wecom_mapper.py` 字段路由/`PROJECT_LIST` 格式化/结构与载荷指纹）、`WECOM-06`（`WeComConnectionService`/`WeComSyncService`、公开 `/api/v1/wecom/**` 与 Main-only `/api/v1/internal/wecom/**` API、崩溃恢复、独立审查）。renderer UI 仍未实现，当前产品仍保持 `wecom_sync=false` 和占位 UI，且 Electron 现有连接入口因 `form_id`/`credential_slot` 尚未真正接通（见 `issues.md` `ISS-031`）在真实点击时仍无法完整走通，不得把已交付的后端能力当作用户可用的完整业务功能。下一可领取任务是 `WECOM-07`（Electron/Vue 交互）。具体事实以 `progress.md`、任务依赖以 `task.md` 为准。
