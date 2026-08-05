# API 接口规范

> 状态：目标 API 契约已基线化（V1；系统、认证与用户管理已实现，其余业务待实现）
> 更新日期：2026-08-05
> 基础路径：`/api/v1`

## 0. 契约状态与当前实现

本文件定义 V1 目标接口。接口出现在表格中不代表路由已经存在；联调和验收必须以当前代码、自动化测试与 `progress.md` 为准。

截至 2026-08-05：

- `GET /health` 已达目标契约：返回统一成功结构、`X-Request-Id`、`data.status`、`data.version` 和 `Cache-Control: no-store`，且豁免 `X-Runtime-Secret` 校验。
- 已配置精确 Trusted Host/CORS 基线，并已实现 `X-Runtime-Secret` 校验中间件（除 `/health`、`/docs`、`/openapi.json` 外的所有请求均需携带）。
- 统一异常响应基础已实现（`backend/app/core/errors.py`）：`RequestValidationError`（Pydantic 422）归一化为 `code=40001`/`HTTP 400`；`AppError` 基类供后续业务异常子类化；`OperationalError` 映射为 `50301`；未捕获异常映射为 `50001`，均不泄露堆栈或驱动原始报错文本。**注意**：这只是异常处理基础设施，第 3 节列出的具体业务错误码（如 `40901`/`40902` 等）仍随各自业务任务（`DAILY-*`/`WEEKLY-*` 等）实现，本节状态更新不代表业务接口已存在。
- `GET /api/v1/system/bootstrap-status`、`POST /api/v1/system/bootstrap-admin` 已在阶段 4 `AUTH-01` 实现并有自动化测试（`backend/tests/test_system_bootstrap_api.py`、`test_bootstrap_service.py`）：仍需 `X-Runtime-Secret`；空库返回 `initialized:false`；创建成功后返回账号元数据（不含密码/哈希）并原子建立默认模板；重复调用返回 `40001`（含并发场景）。
- `POST /api/v1/auth/login`、`GET /api/v1/auth/me`、`PUT /api/v1/auth/password`、`POST /api/v1/auth/logout` 及五个 `/api/v1/users` 管理接口已在阶段 4 实现；除匿名入口外均同时校验 runtime secret、JWT、用户启用状态和 `token_version`，admin 接口还校验角色。模板、日报、导出、周报、设置和能力接口仍未实现。

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
| POST | `/system/bootstrap-admin` | 仅空用户表 | 原子创建首个 admin |
| POST | `/auth/login` | 匿名 | 返回 24h access token |
| GET | `/auth/me` | 登录 | 当前用户和权限 |
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

创建响应只返回随机 `backup_id`、安全文件名和 `expires_at`，不得返回内部路径。短期文件 15 分钟过期，应用启动时清理残留。由于整库备份包含全体用户数据，普通用户不得调用，前端必须在创建前展示敏感数据提示。

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

后端负责新字段稳定 ID 的产生或接受服务端预分配 ID；前端不得自行替换已有 `field_key`。发布响应返回新 `version_no`。

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

## 10. 设置与能力

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/settings/me` | 登录 | 当前用户设置 |
| PATCH | `/settings/me` | 登录 | 修改 `auto_archive_on_submit` |
| GET | `/capabilities` | 登录 | 返回能力开关，如 `wecom_sync:false` |

V1 不定义任何企业微信同步接口，点击占位入口只在前端显示本地提示。

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
