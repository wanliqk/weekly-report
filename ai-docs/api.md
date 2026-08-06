# API 接口规范

> 状态：V1 API 历史契约已实现；第二版 BE-10A 初始化/认证/设置基线已实现，其余待后续阶段
> 更新日期：2026-08-07
> 基础路径：`/api/v1`

## 0. 契约状态与当前实现

> **CR-20260807-01 事实边界**：第 1～12 节主要保留 V1 历史契约；第 13 节描述第二版契约。BE-10A 已实现 13.1 的 bootstrap/强制改密（用户删除除外）并移除设置 PATCH，其余目标仍不得视为完成。

本文件定义 V1 目标接口。接口出现在表格中不代表路由已经存在；联调和验收必须以当前代码、自动化测试与 `progress.md` 为准。

截至 2026-08-06：

- `GET /health` 已达目标契约：返回统一成功结构、`X-Request-Id`、`data.status`、`data.version` 和 `Cache-Control: no-store`，且豁免 `X-Runtime-Secret` 校验。
- 已配置精确 Trusted Host/CORS 基线（含 `expose_headers=["Content-Disposition"]`，供导出文件下载在 renderer 端读取服务端文件名），并已实现 `X-Runtime-Secret` 校验中间件（除 `/health`、`/docs`、`/openapi.json` 外的所有请求均需携带）。
- 统一异常响应基础已实现（`backend/app/core/errors.py`）：`RequestValidationError`（Pydantic 422）归一化为 `code=40001`/`HTTP 400`；`AppError` 基类供后续业务异常子类化；`OperationalError` 映射为 `50301`；未捕获异常映射为 `50001`，均不泄露堆栈或驱动原始报错文本。
- `GET /api/v1/system/bootstrap-status`、`POST /api/v1/system/bootstrap` 已在 BE-10A 更新：仍需 `X-Runtime-Secret`；空库原子创建输入的普通用户和固定 admin，双方拥有独立密码哈希/默认资源，重复或并发调用返回 `40001`。
- `POST /api/v1/auth/login`、`GET /api/v1/auth/me`、`PUT /api/v1/auth/password`、`POST /api/v1/auth/logout` 及五个 `/api/v1/users` 管理接口已在阶段 4 实现；除匿名入口外均同时校验 runtime secret、JWT、用户启用状态和 `token_version`，admin 接口还校验角色。
- 第 6 节三个模板接口、第 7 节六个日报接口、第 10 节三个设置/能力接口均已在阶段 5 实现（细节见各节末尾说明）。
- 第 8 节三个导出接口已在阶段 6 `EXPORT-01`/`EXPORT-02` 实现（细节见该节末尾说明）。
- 第 9 节六个周报接口已在阶段 7 `WEEKLY-01`/`WEEKLY-02` 实现（细节见该节末尾说明）。
- 第 4.1 节两个手动整库备份接口已在阶段 8 `BACKUP-01` 实现（细节见该节末尾说明）。

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

### 13.3 管理员日报与审计

| 方法 | 路径 | 权限 | 第二版语义 |
|---|---|---|---|
| GET | `/admin/daily-reports/submitted` | admin | 待归档条目元数据，不返回正文/模板快照 |
| POST | `/admin/daily-reports/{report_id}/revoke-submission` | admin | `{version,reason}` 撤销为草稿并审计 |
| GET | `/admin/audit-events` | admin | 按动作/日期分页查白名单审计 |

撤销只允许 open 日期下 submitted 条目；成功后清空提交时间、保留正文、版本加一，所有者详情返回最近撤销原因和时间。

### 13.4 统计、设置、周报和导出

| 方法 | 路径 | 权限 | 第二版语义 |
|---|---|---|---|
| GET | `/statistics/monthly?month=YYYY-MM` | 本人 | 月历、完成率、日报/周报篇数、当前连续天数 |
| GET | `/settings/me` | 本人 | 固定时区/能力；删除自动归档字段 |
| PATCH | `/settings/me` | 本人 | 第二版移除 |
| GET/POST/PUT | `/weekly-reports...` | 本人 | 路径保持，来源改为日期级正式日报 |
| POST | `/exports` | 本人 | 显式选择改为 `daily_report_day_ids`；筛选只选 archived 日期 |

统计当前月分母截至 Asia/Shanghai 今天，历史月为整月，未来月分母 0 且完成率 null；完成日期只认 archived 日期，日报篇数为 submitted/archived 来源条目，周报按 `week_start` 月份，连续天数按今天/昨天规则。

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
