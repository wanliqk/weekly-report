# API 接口规范

> 状态：V1 API 历史契约已实现；第二版 BE-10A/BE-10B/BE-10C 后端、FE-10 Electron/Vue 接入与 QA-10 端到端验收（含真实生产打包安装验证）均已完成，第二版全部交付
> 更新日期：2026-08-07
> 基础路径：`/api/v1`

## 0. 契约状态与当前实现

> **CR-20260807-01 事实边界**：第 1～12 节主要保留 V1 历史契约（第 7 节日报接口已被第 13.2 节取代、第 8 节导出与第 9 节周报的选择/内容字段已被第 13.4 节取代，见下）；第 13 节描述第二版契约。BE-10A 已实现 13.1 的 bootstrap/强制改密（用户删除除外）并移除设置 PATCH；BE-10B 已实现 13.1 的 `DELETE /users/{user_id}`、13.2 全部日报条目/日期接口、13.3 全部管理员日报/审计接口；BE-10C 已实现 13.4 的统计 API 与周报/导出的日期级来源适配；FE-10 已把 Electron/Vue renderer 的全部调用点（`electron/src/renderer/src/api/*.ts`）切换为本节描述的第二版契约，不再调用任何 V1 专属路径（如 `/system/bootstrap-admin`、单篇 `/daily-reports/{id}/archive`、`PATCH /settings/me`）。

本文件定义 V1 目标接口。接口出现在表格中不代表路由已经存在；联调和验收必须以当前代码、自动化测试与 `progress.md` 为准。

截至 2026-08-06：

- `GET /health` 已达目标契约：返回统一成功结构、`X-Request-Id`、`data.status`、`data.version` 和 `Cache-Control: no-store`，且豁免 `X-Runtime-Secret` 校验。
- 已配置精确 Trusted Host/CORS 基线（含 `expose_headers=["Content-Disposition"]`，供导出文件下载在 renderer 端读取服务端文件名），并已实现 `X-Runtime-Secret` 校验中间件（除 `/health`、`/docs`、`/openapi.json` 外的所有请求均需携带）。
- 统一异常响应基础已实现（`backend/app/core/errors.py`）：`RequestValidationError`（Pydantic 422）归一化为 `code=40001`/`HTTP 400`；`AppError` 基类供后续业务异常子类化；`OperationalError` 映射为 `50301`；未捕获异常映射为 `50001`，均不泄露堆栈或驱动原始报错文本。
- `GET /api/v1/system/bootstrap-status`、`POST /api/v1/system/bootstrap` 已在 BE-10A 更新：仍需 `X-Runtime-Secret`；空库原子创建输入的普通用户和固定 admin，双方拥有独立密码哈希/默认资源，重复或并发调用返回 `40001`。
- `POST /api/v1/auth/login`、`GET /api/v1/auth/me`、`PUT /api/v1/auth/password`、`POST /api/v1/auth/logout` 及五个 `/api/v1/users` 管理接口已在阶段 4 实现；除匿名入口外均同时校验 runtime secret、JWT、用户启用状态和 `token_version`，admin 接口还校验角色。
- 第 6 节三个模板接口、第 7 节六个日报接口、第 10 节三个设置/能力接口均已在阶段 5 实现（细节见各节末尾说明）。
- 第 8 节三个导出接口已在阶段 6 `EXPORT-01`/`EXPORT-02` 实现，选择字段和多来源渲染已随 `BE-10C` 更新（细节见第 13.4 节末尾说明）。
- 第 9 节六个周报接口已在阶段 7 `WEEKLY-01`/`WEEKLY-02` 实现，内容结构和来源查询已随 `BE-10C` 更新（细节见第 13.4 节末尾说明）。
- 第 4.1 节两个手动整库备份接口已在阶段 8 `BACKUP-01` 实现（细节见该节末尾说明）。
- 第 13.1 节 `DELETE /users/{user_id}`、第 13.2 节全部日报条目/日期容器接口、第 13.3 节全部管理员日报/审计接口已在 `BE-10B` 实现（细节见该节末尾说明）；第 7 节描述的 V1 日报接口（同日一篇、单篇归档）已被取代，不再是当前实现契约。
- 第 13.4 节的 `GET /statistics/monthly`、周报日期级来源适配、导出 `daily_report_day_ids` 选择均已在 `BE-10C` 实现（细节见该节末尾说明）。

本文后续示例均为目标契约；实现任务不得为了匹配“已存在”的假象跳过测试或状态更新。

## 1. 通用协议

- JSON 编码 UTF-8，字段统一 `snake_case`。
- 工作日期格式 `YYYY-MM-DD`；时间为带时区 ISO 8601。
- 除 `/health`、bootstrap status、bootstrap admin 和 login 外，接口必须校验 JWT。
- 除 `GET /health` 外，所有本地 API 请求必须带 `X-Runtime-Secret`；健康检查不校验该请求头且不得返回敏感信息。
- 响应头返回 `X-Request-Id`。
- 列表默认按业务日期降序、ID 降序稳定排序；默认 `page=1`、`page_size=20`，最大 100。
- 资源所有权不足默认返回 404，避免枚举他人资源。

## 2. 响应格式

成功：

```json
{"code": 0, "msg": "success", "data": {}}
```

分页：

```json
{
  "code": 0,
  "msg": "success",
  "data": {"items": [], "page": 1, "page_size": 20, "total": 0}
}
```

失败：

```json
{
  "code": 40901,
  "msg": "该工作日期已存在日报",
  "data": {"existing_report_id": "01K..."}
}
```

文件流是成功响应唯一不使用 JSON 包装的接口；文件接口失败仍返回统一 JSON。

## 3. 错误码

| code | HTTP | 含义 |
|---:|---:|---|
| 40001 | 400 | 参数或业务规则校验失败 |
| 40101 | 401 | 用户名或密码错误 |
| 40102 | 401 | Token 无效、过期或版本失效 |
| 40103 | 401 | 运行期密钥（`X-Runtime-Secret`）缺失或无效 |
| 40301 | 403 | 角色权限不足 |
| 40302 | 403 | 仅用于明确可暴露的所有权冲突；普通越权用 404 |
| 40401 | 404 | 资源不存在或不可见 |
| 40901 | 409 | 同日期日报已存在 |
| 40902 | 409 | 非法日报状态流转 |
| 40903 | 409 | 同自然周周报已存在 |
| 40904 | 409 | 乐观锁版本冲突 |
| 42201 | 422 | 模板字段缺失或类型不匹配 |
| 50001 | 500 | 内部错误 |
| 50301 | 503 | 数据库繁忙或服务暂不可用 |

FastAPI/Pydantic 默认 422 必须转换为统一结构，并在 `data.errors` 返回安全的字段定位信息。

## 4. 系统与认证

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/health` | 本机运行期 | 存活与版本，不含路径/密钥 |
| GET | `/system/bootstrap-status` | 匿名 | 是否需要初始化 |
| POST | `/system/bootstrap` | 仅空用户表 | 原子创建普通用户和固定 admin |
| POST | `/auth/login` | 匿名 | 返回 24h access token |
| GET | `/auth/me` | 登录 | 当前用户、权限和 `must_change_password` |
| PUT | `/auth/password` | 登录 | 修改密码并使旧 Token 失效 |
| POST | `/auth/logout` | 登录 | 客户端清 Token；V1 无黑名单 |

JWT 声明至少包含 `sub`、`role`、`ver`、`iat`、`exp`、`jti`。每次鉴权检查用户启用状态和 `token_version`。

登录成功的 `data` 为 `{"access_token":"...","expires_at":"带时区 ISO 8601"}`；`/auth/me` 与用户管理接口只返回 `id`、`username`、`display_name`、`role`、`is_active`、`created_at`，不返回密码哈希或 `token_version`。V1 logout 不维护服务端黑名单，只要求客户端清理 Token。

目标健康检查契约：

- `GET /health` 不使用 `/api/v1` 前缀，不要求 JWT 或 `X-Runtime-Secret`。
- 仅用于 Electron 主进程判断 sidecar 存活；后端仍必须只监听 `127.0.0.1`。
- 成功返回 HTTP 200、`Cache-Control: no-store`，响应如下：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "status": "ok",
    "version": "0.1.0"
  }
}
```

`version` 取后端项目版本（`FastAPI(version=...)` 单一来源），不返回路径、主机名、进程参数、密钥、数据库或依赖信息。此契约已在阶段2 Desktop Bootstrap 落地并有对应测试（`backend/tests/test_health.py`、`test_sidecar_bootstrap.py`）。

### 4.1 手动整库备份

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/system/backups` | admin | checkpoint 后创建一致性短期备份 |
| GET | `/system/backups/{id}/file` | 创建该备份的 admin | 下载 SQLite 备份文件 |

创建响应只返回随机 `id`、安全文件名 `file_name` 和 `expires_at`，不得返回内部路径。短期文件 15 分钟过期，应用启动时清理残留。由于整库备份包含全体用户数据，普通用户不得调用，前端必须在创建前展示敏感数据提示。

上述两个接口已在阶段 8 `BACKUP-01` 实现。备份不登记业务表，使用进程内 `BackupRegistry`（随机 ULID 映射到文件路径/创建者/过期时间）保存，进程重启即清空，配合启动时对残留文件的目录级清理；创建时会先在同一次调用内对已过期条目做懒清理。生成先执行 `PRAGMA wal_checkpoint(TRUNCATE)` 再用 `sqlite3.Connection.backup()` 做一致性快照，阻塞 I/O 通过 `asyncio.to_thread` 卸载。下载校验角色为 admin 且必须是创建该备份的同一账号，非创建者（含其他 admin）返回 40401，不用 40302/40301 区分，避免暴露备份是否存在；懒过期判断在下载前进行，过期即删除文件并从注册表移除。所有文件路径在删除或读取前都会校验解析后仍位于 `manual_backup_temp_dir` 内。

## 5. 用户管理

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/users` | admin | 分页查询账号元数据 |
| POST | `/users` | admin | 创建用户、设置和默认模板 |
| GET | `/users/{id}` | admin | 查看账号元数据 |
| PATCH | `/users/{id}` | admin | 修改显示名、角色、启用状态 |
| PUT | `/users/{id}/password` | admin | 重置密码并递增 token_version |

管理员接口不返回日报、周报、模板内容或导出文件。修改角色/状态时必须保护最后一个有效管理员。

上述五个用户管理接口已实现。用户名以 `strip().casefold()` 规范化并按大小写无关唯一约束判重；创建用户会在同一事务中建立默认设置、模板和首个模板版本。修改角色/状态或重置密码会递增 `token_version`，使旧 Token 失效。

## 6. 日报模板

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/report-templates/current` | 登录 | 当前模板和版本字段 |
| PUT | `/report-templates/current` | 登录 | 校验并发布新版本 |
| GET | `/report-templates/versions` | 登录 | 本人的历史版本摘要 |

模板字段请求：

```json
{
  "field_key": "01K...",
  "label": "今日工作内容",
  "description": "",
  "field_type": "textarea",
  "required": true,
  "enabled": true,
  "sort_order": 10,
  "options": []
}
```

后端负责新字段稳定 ID 的产生或接受服务端预分配 ID；新字段请求省略 `field_key`，既有字段必须原样携带当前稳定键，前端不得自行替换。发布响应返回新 `version_no`。

上述三个模板接口已实现。发布会写入新的完整字段 JSON 版本并条件推进 `current_version_no`，不会更新/删除历史版本；并发冲突返回 40904。服务端校验六类字段、排序、选项、核心字段不可删除且至少启用一个。

## 7. 日报

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/daily-reports` | 登录 | `date_from/date_to/status/page/page_size` 查询 |
| POST | `/daily-reports` | 登录 | 按当前模板创建草稿 |
| GET | `/daily-reports/{id}` | 所有者 | 详情、快照和内容 |
| PATCH | `/daily-reports/{id}` | 所有者、draft | 保存内容，必须带 `version` |
| POST | `/daily-reports/{id}/submit` | 所有者、draft | 校验并提交/自动归档 |
| POST | `/daily-reports/{id}/archive` | 所有者、submitted | 归档 |

创建请求：`{"work_date":"2026-08-04"}`。

保存请求：

```json
{
  "version": 3,
  "content": {
    "01K-FIELD-1": "完成日报模块设计",
    "01K-FIELD-2": ["开发", "评审"]
  }
}
```

服务端只依据日报快照解释和校验内容。40901 响应必须包含 `existing_report_id`。

提交与归档请求均必须携带当前内容版本：`{"version":3}`。保存、提交和归档成功后响应返回递增后的新 `version`；非法状态返回 40902，陈旧版本返回 40904，字段/必填校验失败返回 42201 和 `data.errors`。

上述六个日报接口已实现。列表按 `work_date DESC, id DESC` 稳定排序并限制 `page_size<=100`；所有详情、列表和条件更新均强制当前 `owner_id`。创建允许历史、未来和闰日，在同一事务中保存当前模板完整快照；提交可依据个人设置在同一条件更新中原子归档。

## 8. Excel 导出

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/daily-report-exports` | 登录 | 创建导出任务 |
| GET | `/daily-report-exports/{id}` | 所有者 | 状态、条数、过期时间 |
| GET | `/daily-report-exports/{id}/file` | 所有者、succeeded | `.xlsx` 二进制下载 |

创建参数只能二选一：

```json
{"report_ids": ["01K..."]}
```

或：

```json
{"filter": {"date_from": "2026-08-01", "date_to": "2026-08-31", "status": "archived"}}
```

服务端始终再次施加 `owner=current_user` 和 `status=archived`。成功文件响应设置安全文件名和标准 xlsx MIME 类型，不暴露内部路径。

上述三个导出接口已实现。`report_ids` 与 `filter` 由 Pydantic 校验二选一；显式 ID 中任何一个非本人或非归档记录都会使整个请求被拒绝并在 `data.invalid_report_ids` 中列出，不做部分导出。创建为同步请求内完成校验、生成、落盘和状态落库（终态为 `succeeded`/`failed`，不引入后台任务队列）。导出文件 24 小时后过期，`GET .../file` 会在返回前做懒过期判断（过期即转 `expired` 并删除文件，与所有权、状态是否 `succeeded` 一样，未通过均统一返回 40401，不暴露具体原因）；应用启动时另有一次清理扫描。跨模板版本的动态列按 `field_key` 稳定合并，历史新增字段追加在后，重复表头文本加 `field_key` 后缀消歧；自由文本字段值以 `=` 开头会被转义为纯文本，避免生成可执行的 Excel 公式。

## 9. 周报

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/weekly-reports/availability` | 登录 | `week_start` 对应周范围及日报可用性 |
| GET | `/weekly-reports` | 登录 | 按周范围分页查询 |
| POST | `/weekly-reports` | 登录 | 生成或返回 40903 |
| GET | `/weekly-reports/{id}` | 所有者 | 当前内容、基线和来源 |
| PUT | `/weekly-reports/{id}` | 所有者 | 保存编辑，必须带 `version` |
| POST | `/weekly-reports/{id}/regenerate` | 所有者 | 显式确认后覆盖 |

生成请求：`{"week_start":"2026-08-03"}`。

重生成请求：

```json
{"version": 4, "confirm_overwrite": true}
```

`week_start` 非周一返回 40001。若同周已存在，40903 的 `data` 返回 `existing_weekly_report_id`。重生成同时执行乐观锁检查。

上述六个接口已实现。`availability` 展示自然周内 7 天各自的日报状态（`draft`/`submitted`/`archived`/无日报）供前端提示未归档日期，只读、不写入任何记录；生成（`POST`）会重新查询归档日报，不信任 `availability` 的预检结果。`PUT` 只接受并覆盖 `supplement`/`next_week_plan`/`risks` 三个自由文本字段（`content.days` 保持不变），从机制上保证人工编辑不反写日报。`regenerate` 的 `confirm_overwrite` 服务端强制校验为 `true`（缺省即 422，传 `false` 返回 40001），确认后原子重建 `days`、来源快照，并把 `supplement`/`next_week_plan`/`risks` 重置为空——不保留任何历史版本。

## 10. 设置与能力

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/settings/me` | 登录 | 当前用户设置 |
| GET | `/capabilities` | 登录 | 返回能力开关，如 `wecom_sync:false` |

V1 不定义任何企业微信同步接口，点击占位入口只在前端显示本地提示。

BE-10A 后设置只读：`timezone` 固定返回 `Asia/Shanghai`，`PATCH /settings/me` 已移除，能力响应仍为 `{"wecom_sync":false}`。Electron 设置页仍是 V1 界面，待 FE-10 移除自动归档开关。

## 11. 幂等、并发与缓存

- V1 不引入通用幂等键；依靠唯一约束、条件更新和乐观锁保证重复请求安全。
- 创建类接口发生唯一冲突时返回已存在资源 ID；不得生成重复记录。
- 更新成功后返回新 `version`；客户端必须用新版本替换本地值。
- 业务响应默认 `Cache-Control: no-store`；文件下载按过期时间控制。
- 前端收到 40102 清理 Token 并跳转登录；收到 40904 保留未提交输入并提示重新加载。

## 12. 接口变更规则

- 新增/删除接口、修改字段语义、错误码、权限或状态码前必须先更新本文件。
- V1 内新增响应字段应保持向后兼容；删除/改名必须经过版本化评审。
- Agent 不得自行创建“临时接口”；联调缺口记录到 `task.md`，由技术负责人定契约。
- 每组接口完成后必须同时更新实现状态、契约测试和 `progress.md`；阶段质量门禁通过后创建独立 Conventional Commit，未获用户授权不得推送。

## 13. 第二版 API 目标契约

### 13.1 初始化、认证和用户

| 方法 | 路径 | 权限 | 第二版语义 |
|---|---|---|---|
| GET | `/system/bootstrap-status` | 匿名 | 保持不变 |
| POST | `/system/bootstrap` | 仅空系统 | 输入普通用户信息，原子创建普通用户和固定 admin |
| GET | `/auth/me` | 登录 | 增加 `must_change_password` |
| PUT | `/auth/password` | 登录 | 改密后清除强制标志并使旧 Token 失效 |
| DELETE | `/users/{user_id}` | admin | `{confirm_username,reason}`；仅无业务账号可删 |

移除 `/system/bootstrap-admin`。除 `/auth/me`、`PUT /auth/password`、`POST /auth/logout` 外，`must_change_password=true` 调用业务接口返回 `40303`。管理员重置密码后目标用户也进入强制改密状态。

`DELETE /users/{user_id}` 已在 `BE-10B` 实现：拒绝删除当前登录账号，`confirm_username` 须与目标账号原始 `username` 精确匹配（非规范化比较），无业务记录（`daily_report_days`/`weekly_reports`/`export_jobs`）时物理删除并清理默认关联资源，否则返回 `40910`；末位有效管理员保护复用 `USER-01` 的条件更新模式，已用真实并发测试验证只保留一个活跃管理员；成功删除写入 `admin_audit_events`（`action=user_deleted`）。

`GET /users`、`GET /users/{user_id}` 响应新增 `can_delete: bool` 与 `cannot_delete_reason: "self"|"last_active_admin"|"has_business_records"|null`（`docs/方案设计.md` §7.3），供界面提前禁用删除按钮；仅供 UX 提示，`DELETE` 时服务端仍重新校验全部条件。

### 13.2 日报条目与日期

| 方法 | 路径 | 权限 | 第二版语义 |
|---|---|---|---|
| GET | `/daily-reports` | 本人 | 按日期/状态分页列来源条目 |
| POST | `/daily-reports` | 本人 | `{work_date,client_request_id}` 幂等创建草稿 |
| GET | `/daily-reports/{report_id}` | 本人 | 条目和最近撤销信息 |
| PATCH | `/daily-reports/{report_id}` | 本人 | `{version,content}` 保存草稿 |
| DELETE | `/daily-reports/{report_id}` | 本人 | `{version}` 删除草稿 |
| POST | `/daily-reports/{report_id}/submit` | 本人 | `{version}` 提交，不自动归档 |
| GET | `/daily-report-days?month=YYYY-MM` | 本人 | 月历摘要 |
| GET | `/daily-report-days/{work_date}` | 本人 | 日期计数、条目或正式快照 |
| POST | `/daily-report-days/{work_date}/archive` | 本人 | `{confirm_archive:true}` 日期级归档 |

删除单篇 `/daily-reports/{id}/archive`。月历摘要返回草稿/已提交/归档/总数、能否创建/归档及禁用原因；日期已归档时重复归档幂等返回已有正式结果，不改写归档时间。

上述九个接口均已在 `BE-10B` 实现。创建按 `client_request_id` 幂等：同一 key 且所有者/日期一致返回既有条目（响应 `created:false`），不存在时创建新草稿（响应 `created:true`），跨用户或跨日期复用同一 key 返回 `40908`（不泄露对方条目内容）。日期容器与全部子写操作（创建/保存/删除/提交/归档）共用同一并发互斥点：归档在读取当天条目前先对日期行做条件 `UPDATE` 占用 SQLite 写锁，创建改用 `INSERT ... SELECT ... WHERE EXISTS` 单语句关闭"日期是否仍为 open"的检查竞态；均已用真实 `asyncio.gather` 并发测试验证（含创建与归档并发时二者互斥、双管理员并发互删只保留一个活跃管理员）。归档按 `submitted_at ASC, id ASC` 聚合当天全部已提交条目为不可变 `archive_snapshot_json`，并把这些条目的状态一并翻转为 `archived`。条目响应（`GET/POST/PATCH/submit`）均新增 `day_id`；月历摘要按 `docs/方案设计.md` §8.3 只返回存在 `daily_report_days` 记录的日期（不为整月合成占位行），字段为 `work_date/day_id/status/draft_count/submitted_count/archived_count/total_count/can_create/can_archive/archive_disabled_reason`（原 `disabled_reason` 已更名为 `archive_disabled_reason` 以对齐方案原文，日期详情接口同步改名）。

### 13.3 管理员日报与审计

| 方法 | 路径 | 权限 | 第二版语义 |
|---|---|---|---|
| GET | `/admin/daily-reports/submitted` | admin | 待归档条目元数据，不返回正文/模板快照 |
| POST | `/admin/daily-reports/{report_id}/revoke-submission` | admin | `{version,reason}` 撤销为草稿并审计 |
| GET | `/admin/audit-events` | admin | 按动作/日期分页查白名单审计 |

撤销只允许 open 日期下 submitted 条目；成功后清空提交时间、保留正文、版本加一，所有者详情返回最近撤销原因、操作者用户名和时间（`GET /daily-reports/{id}` 响应的 `last_revocation.actor_username`；复用已有的 `admin_audit_events.actor_username_snapshot` 列，未新增“显示名”快照列）。

上述三个接口均已在 `BE-10B` 实现。待归档列表和撤销均通过原始列 SQL 选择返回，服务端从不加载 `content_json`/`template_snapshot_json`（不依赖响应 schema 兜底过滤，已通过独立安全审查确认）；撤销的 `reason` 服务端去空白后校验非空，写入 `admin_audit_events` 的 `metadata_json` 只含 `work_date` 等白名单字段。审计事件查询支持按 `action`（`daily_submission_revoked`/`user_deleted`）和日期范围过滤。

### 13.4 统计、设置、周报和导出

| 方法 | 路径 | 权限 | 第二版语义 |
|---|---|---|---|
| GET | `/statistics/monthly?month=YYYY-MM` | 本人 | 月历、完成率、日报/周报篇数、当前连续天数 |
| GET | `/settings/me` | 本人 | 固定时区/能力；删除自动归档字段 |
| PATCH | `/settings/me` | 本人 | 第二版移除 |
| GET/POST/PUT | `/weekly-reports...` | 本人 | 路径保持，来源改为日期级正式日报 |
| POST | `/daily-report-exports` | 本人 | 显式选择改为 `daily_report_day_ids`；筛选只选 archived 日期。路径本身不改名（`docs/方案设计.md` §8 明确未列出的导出/周报/备份接口保持既有路径），此前草案曾写作 `/exports`，已按方案原文订正 |

统计当前月分母截至 Asia/Shanghai 今天，历史月为整月，未来月分母 0 且完成率 null；完成日期只认 archived 日期，日报篇数为 submitted/archived 来源条目，周报按 `week_start` 月份，连续天数按今天/昨天规则。

上述统计、周报、导出适配均已在 `BE-10C` 实现。

**`GET /statistics/monthly`**：响应 `{month, effective_date_from, effective_date_to, denominator_days, completed_days, completion_rate, daily_report_count, weekly_report_count, current_streak_days, days}`；`completion_rate` 四舍五入到小数点后一位，分母为 0（未来月）时为 `null`；`days` 复用与 `GET /daily-report-days?month=` 相同的稀疏月历摘要（只含存在记录的日期）；`current_streak_days` 与所选 `month` 无关，始终基于 Asia/Shanghai 今天用今天/昨天规则向前查询最近完成日期。

**周报**：`WeeklyDay` 从单一 `daily_report_id`+`fields` 改为 `daily_report_day_id`+`entries: list[{daily_report_id,submitted_at,fields}]`，一个日期下可能有多个来源条目，各自保留独立字段值；`availability` 返回的逐日 `status` 现在反映日期容器状态（`archived`/日期开放且有草稿则 `draft`/日期开放且仅有已提交则 `submitted`/无记录则 `null`），不再是单一条目自身状态。

**导出**：`ExportCreateRequest.report_ids` 更名为 `daily_report_day_ids`；选择/筛选校验失败的响应字段同步更名为 `data.invalid_daily_report_day_ids`；基础列新增"来源条目数"；一个日期存在多篇来源时，同一字段的多个值在单元格内按提交顺序渲染为 `[1] 值`、`[2] 值`（换行分隔，保留来源边界），只有单一来源时保持字段原始类型（数字列不因合并逻辑被迫转为文本）；`=` 前缀公式注入防护对每个来源值和合并后的整体文本值均生效。

### 13.5 新错误码和幂等

| code | HTTP | 含义 |
|---:|---:|---|
| 40303 | 403 | 必须先修改临时密码 |
| 40905 | 409 | 日期已归档 |
| 40906 | 409 | 日期仍有草稿 |
| 40907 | 409 | 没有可归档条目 |
| 40908 | 409 | 创建幂等键冲突 |
| 40910 | 409 | 用户已有业务记录不能删除 |

创建请求的 `client_request_id` 由 renderer 生成并在同一意图重试时复用；同键返回既有条目，不同键可创建同日新条目。现有 404 所有权隐藏、40902 状态冲突、40904 乐观锁和 50301 数据库繁忙继续使用。

## 14. 企业微信同步目标 API（CR-20260808-02，WECOM-06 已实现）

> 后端 Service/Repository/API 与 WECOM-07 renderer 交互均已实现；`GET /capabilities` 现返回 `wecom_sync:true`。真实企业微信账号和生产发布级验证仍属于 `WECOM-08`。

### 14.1 公开 REST（`backend/app/api/v1/wecom.py`）

| 方法 | 路径 | 权限/用途 |
|---|---|---|
| GET | `/wecom/connection` | 本人连接状态和非敏感账号摘要；从未连接过返回 `connected:false,status:null`，区别于"曾连接后断开"的 `status:"disconnected"` |
| GET/PUT | `/wecom/profile` | 本人读取/版本化更新映射配置；未连接返回 `40911`；`PUT` 只接受 `expected_version`+必填 `field_mapping`（2026-08-11 起不再接受 `recipient_config`——`ISS-054`/`PROD-032`：收件人不再是用户配置项，由系统在连接/重连时自动解析），`question_mapping`/`schema_fingerprint`/`form_id`/`recipient_config` 只能由连接时发现产生；版本冲突复用 `40904` |
| POST | `/wecom/previews` | 本人预览指定 `daily_report_day_id` 的转换结果；非本人/不存在 `40401`，未归档复用 `40902`，未连接 `40911`；从不落库、不写日志 |
| POST | `/daily-report-days/{work_date}/wecom-syncs` | 本人幂等创建/取得同步记录（响应含 `created` 标记，与日报创建同一模式）；未归档/未连接同上 |
| GET | `/wecom/sync-records` | 本人按 `status`/`date_from`/`date_to`/`page`/`page_size` 查询历史 |
| GET | `/wecom/sync-records/{record_id}` | 本人同步详情，不含请求/响应原文；非本人 `404` |
| POST | `/wecom/sync-records/{record_id}/retry` | 只对 `failed/auth_required/schema_changed/duplicate_detected` 生效；`pending/syncing` 为无操作幂等返回；`succeeded` 复用 `40913`；`uncertain` 返回 `40914` |

所有公开接口继续使用 `/api/v1` 前缀，同时校验 runtime secret、JWT（`get_current_user`，含强制改密 `40303` 拦截）和 owner；越权统一 `40401`。

### 14.2 Main-only REST（`backend/app/api/v1/internal_wecom.py`）

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/internal/wecom/connections/validate` | Main 传入单次内存 Cookie jar + `credential_slot` + `form_id`，验证并保存非敏感绑定 |
| GET | `/internal/wecom/connections/credential-slot` | 按当前 JWT 返回本人不透明 `credential_slot` + `connection_status`（无绑定均为 `null`），供 Main 在应用重启后定位 `safeStorage` 密文并对账断开结果；不进入 preload/renderer |
| POST | `/internal/wecom/sync-records/{record_id}/execute` | Main 解密凭证后执行已预留记录；业务失败（`schema_changed`/`duplicate_detected`/`uncertain` 等）以对应错误码的非 2xx 响应返回，记录本身仍已落库为终态 |
| POST | `/internal/wecom/connections/disconnect` | 标记断开；凭证由 Main 删除；无绑定视为已满足的无操作 |

路径仍位于 `/api/v1` 下，同时要求用户 JWT 和 `X-Main-Bridge-Secret`（`app/api/dependencies.py::require_main_bridge_secret`，`secrets.compare_digest` 恒定时间比较，缺失/错误返回 `40104`），`include_in_schema=False` 确保不进入公开 OpenAPI；`RuntimeSecretMiddleware` 已按路径前缀豁免该组端点（不要求也不校验 `X-Runtime-Secret`）。只接受结构化 Cookie jar，不接受原始 Cookie header、文件路径或任意目标 URL。

### 14.3 新增错误码（已实现）

| code | HTTP | 含义 |
|---:|---:|---|
| 40104 | 401 | `X-Main-Bridge-Secret` 缺失或无效 |
| 40911 | 409 | 企业微信未连接或登录已失效 |
| 40912 | 409 | 模板结构已变化 |
| 40913 | 409 | 正式日报已成功同步 |
| 40914 | 409 | 结果不确定，禁止直接重试 |
| 40915 | 409 | 检测到可能重复日报 |
| 50201 | 502 | 内部协议不符合已知契约 |
| 50302 | 503 | 企业微信暂时不可用且可确认未受理 |

日期未归档复用现有 `40902`（同步执行中也复用该码，附加 `data.status:"syncing"` 供调用方区分）。远端响应、Cookie、请求体和日报正文不透传；`last_error_message` 固定中文文案。

### 14.4 崩溃恢复

`app/__main__.py::main()` 启动时调用 `WeComSyncService.recover_stale_syncing_records()`：任何 `syncing` 超过 5 分钟（`STALE_SYNCING_LEASE_SECONDS`）仍未完成的记录转为 `uncertain`（绝不直接转 `failed`），与 `docs/方案设计.md` §10.3 一致；不区分用户，是启动期维护性清理（同 `cleanup_stale_manual_backups`/`ExportService.cleanup_expired` 的既有模式）。

## 15. PROJECT_LIST 条目契约（CR-20260812-01）

日报 `content` 中 `PROJECT_LIST` 字段的值是条目数组。每个条目按以下顺序包含 10 个字符串字段：`category`、`project`、`content`、`weight`、`planned_completion_date`、`actual_completion_date`、`owner`、`assistant`、`required_resources`、`completion_notes`。

`project`/`content` 是条目必填字段；`category` 缺省时为 `"重要"`，`weight` 及其余跟踪字段缺省时为 `""`。请求中的未知字段或非字符串跟踪字段返回 `42201`；历史持久化 JSON 缺少新增字段时，日报、归档快照和周报响应均在 Pydantic 解析阶段补齐默认值。
