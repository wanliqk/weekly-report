# 数据库设计

> 状态：第二版 BE-10A 数据模型与 V1→V2 迁移、BE-10B 日期聚合与审计写入、BE-10C 周报/导出/统计下游查询均已实现
> 更新日期：2026-08-07
> 数据库：SQLite（SQLAlchemy 2.x + Alembic）

## 0. 当前实现状态

> **CR-20260807-01 事实边界**：第 1～7 节保留 V1 历史结构；第 8 节是当前 V2 数据契约。BE-10A 已落地 8.1、8.3 与认证/设置字段；BE-10B 已落地 8.2 的完整多条目事务与 8.4 的删除策略；BE-10C 已把周报、导出和完成统计的下游查询全部切换为读取 `daily_report_days.archive_snapshot_json`（不再读取条目级 `daily_reports.status='archived'`），实现 8.4 的统计查询口径。

- 当前共有 10 张业务表的 SQLAlchemy Model；Alembic 初始迁移 `3f6f955b87bb` 与 V2 迁移 `8b1d4e6f2a90` 均已落地，启动时迁移前备份/轮转保持不变，未使用 `create_all()` 代替迁移。
- 下列表、约束、索引、事务与备份**规则**仍是权威契约来源；实现细节（如具体文件路径）以代码为准，本节只记录"哪些已经真实存在"，不重复描述设计意图。
- 现有 Repository/Service 已适配日期容器所有权连接和周报日期来源 FK；`admin_audit_events` 的模型/迁移随 BE-10A 落地，写入事务（撤销提交、用户删除）随 `BE-10B` 实现；周报/导出/统计的日期级正式来源查询随 `BE-10C` 实现，未新增表或列（复用既有 `daily_report_days`/`weekly_report_sources`/`export_jobs`/`weekly_reports` schema）。
- 迁移与备份基础设施验证方式：`backend/tests/test_migrations.py`（空库 upgrade/降级/幂等）、`backend/tests/test_migrate_backup.py`（备份触发条件、轮转、路径边界、失败停止启动）、`backend/tests/test_db_engine.py`（PRAGMA 实际连接值）。
- 实现后以 migration、Model、自动化测试和 `progress.md` 共同证明状态；若代码与本文冲突，先修正文档或请求确认。

## 1. 全局约定

- 主键统一使用应用层生成的 ULID（26 字符文本），不得与 UUIDv7 或其他主键格式混用。
- 数据库时间保存 UTC，字段名使用 `_at`；API 输出带时区的 ISO 8601。
- `work_date`、`week_start`、`week_end` 保存 `YYYY-MM-DD`，按 Asia/Shanghai 解释。
- 布尔值由 ORM 映射，并用默认值和非空约束保证确定性。
- JSON 在 SQLite 中保存为 TEXT/JSON 语义；写入前经 Pydantic schema 校验，禁止任意结构落库。
- 外键开启且明确删除策略；业务正式记录默认不级联物理删除。
- V1 不提供业务记录物理删除接口。

## 2. 关系概览

```text
users 1──1 user_settings
users 1──1 report_templates 1──N template_versions
users 1──N daily_reports ──N:1 template_versions
users 1──N weekly_reports 1──N weekly_report_sources N──1 daily_reports
users 1──N export_jobs
```

## 3. 表设计

### 3.1 `users`

| 字段 | 类型 | 约束/说明 |
|---|---|---|
| `id` | VARCHAR(26) | PK |
| `username` | VARCHAR(64) | NOT NULL；规范化后唯一 |
| `username_normalized` | VARCHAR(64) | NOT NULL；应用统一 trim/casefold |
| `display_name` | VARCHAR(100) | NOT NULL |
| `password_hash` | VARCHAR(255) | NOT NULL；Argon2id |
| `role` | VARCHAR(16) | NOT NULL；CHECK `admin/user` |
| `token_version` | INTEGER | NOT NULL DEFAULT 1；大于 0 |
| `is_active` | BOOLEAN | NOT NULL DEFAULT true |
| `password_changed_at` | DATETIME | NOT NULL UTC |
| `created_at` | DATETIME | NOT NULL UTC |
| `updated_at` | DATETIME | NOT NULL UTC |

索引：`uq_users_username_normalized`、`ix_users_active_role(is_active, role)`。

### 3.2 `user_settings`

| 字段 | 类型 | 约束/说明 |
|---|---|---|
| `user_id` | VARCHAR(26) | PK/FK `users.id` |
| `auto_archive_on_submit` | BOOLEAN | NOT NULL DEFAULT false |
| `timezone` | VARCHAR(64) | NOT NULL DEFAULT `Asia/Shanghai`；V1 不允许其他值 |
| `created_at` / `updated_at` | DATETIME | NOT NULL UTC |

### 3.3 `report_templates`

| 字段 | 类型 | 约束/说明 |
|---|---|---|
| `id` | VARCHAR(26) | PK |
| `user_id` | VARCHAR(26) | NOT NULL FK `users.id` |
| `name` | VARCHAR(100) | NOT NULL DEFAULT `日报模板` |
| `current_version_no` | INTEGER | NOT NULL；大于 0 |
| `created_at` / `updated_at` | DATETIME | NOT NULL UTC |

约束：`uq_report_templates_user_id(user_id)`。

### 3.4 `template_versions`

| 字段 | 类型 | 约束/说明 |
|---|---|---|
| `id` | VARCHAR(26) | PK |
| `template_id` | VARCHAR(26) | NOT NULL FK `report_templates.id` |
| `version_no` | INTEGER | NOT NULL；从 1 递增 |
| `fields_json` | TEXT | NOT NULL；完整有序字段数组 |
| `created_by` | VARCHAR(26) | NOT NULL FK `users.id` |
| `created_at` | DATETIME | NOT NULL UTC |

约束：`uq_template_versions_template_version(template_id, version_no)`。版本行创建后禁止 UPDATE/DELETE。

字段 JSON：

```json
[
  {
    "field_key": "01K...",
    "label": "今日工作内容",
    "description": "",
    "field_type": "textarea",
    "required": true,
    "enabled": true,
    "sort_order": 10,
    "options": [],
    "core_type": "today_work"
  }
]
```

`core_type` 仅核心字段使用，值为 `today_work` 或 `tomorrow_plan`，用于约束其不可删除；普通字段为 `null`。

### 3.5 `daily_reports`

| 字段 | 类型 | 约束/说明 |
|---|---|---|
| `id` | VARCHAR(26) | PK |
| `user_id` | VARCHAR(26) | NOT NULL FK `users.id` |
| `work_date` | DATE/TEXT | NOT NULL |
| `status` | VARCHAR(16) | NOT NULL；CHECK `draft/submitted/archived` |
| `template_version_id` | VARCHAR(26) | NOT NULL FK `template_versions.id` |
| `template_snapshot_json` | TEXT | NOT NULL；创建时完整字段快照 |
| `content_json` | TEXT | NOT NULL；`field_key -> typed value` |
| `version` | INTEGER | NOT NULL DEFAULT 1；乐观锁 |
| `submitted_at` | DATETIME | NULL UTC |
| `archived_at` | DATETIME | NULL UTC |
| `created_at` / `updated_at` | DATETIME | NOT NULL UTC |

约束与索引：

- `uq_daily_reports_user_work_date(user_id, work_date)`。
- `ix_daily_reports_user_status_date(user_id, status, work_date DESC)`。
- `ix_daily_reports_user_date(user_id, work_date DESC, id DESC)`。
- 基础 CHECK：draft 时归档时间为空；archived 时提交/归档时间非空。完整时间一致性仍由 Service 保证。

内容 JSON 示例：

```json
{
  "01K-FIELD-1": "完成接口设计",
  "01K-FIELD-2": ["开发", "评审"],
  "01K-FIELD-3": 2.5
}
```

### 3.6 `weekly_reports`

| 字段 | 类型 | 约束/说明 |
|---|---|---|
| `id` | VARCHAR(26) | PK |
| `user_id` | VARCHAR(26) | NOT NULL FK `users.id` |
| `week_start` / `week_end` | DATE/TEXT | NOT NULL；周一/周日 |
| `generated_content_json` | TEXT | NOT NULL；最近自动生成基线 |
| `content_json` | TEXT | NOT NULL；当前可编辑内容 |
| `source_snapshot_json` | TEXT | NOT NULL；来源日期和摘要 |
| `generated_at` | DATETIME | NOT NULL UTC |
| `version` | INTEGER | NOT NULL DEFAULT 1 |
| `created_at` / `updated_at` | DATETIME | NOT NULL UTC |

约束：`uq_weekly_reports_user_week(user_id, week_start)`；索引 `ix_weekly_reports_user_week(user_id, week_start DESC, id DESC)`。

周报 JSON 固定结构：

```json
{
  "days": [
    {
      "work_date": "2026-08-04",
      "daily_report_id": "01K...",
      "fields": [
        {"field_key": "01K...", "label": "今日工作内容", "value": "..."}
      ]
    }
  ],
  "supplement": "",
  "next_week_plan": "",
  "risks": ""
}
```

### 3.7 `weekly_report_sources`

| 字段 | 类型 | 约束/说明 |
|---|---|---|
| `weekly_report_id` | VARCHAR(26) | PK/FK `weekly_reports.id` |
| `daily_report_id` | VARCHAR(26) | PK/FK `daily_reports.id` |
| `work_date` | DATE/TEXT | NOT NULL；冗余用于稳定排序 |
| `included_at` | DATETIME | NOT NULL UTC |

索引：`ix_weekly_sources_daily(daily_report_id)`。重生成在同一事务替换当前来源关系。

### 3.8 `export_jobs`

| 字段 | 类型 | 约束/说明 |
|---|---|---|
| `id` | VARCHAR(26) | PK |
| `user_id` | VARCHAR(26) | NOT NULL FK `users.id` |
| `status` | VARCHAR(16) | CHECK `processing/succeeded/failed/expired` |
| `request_json` | TEXT | NOT NULL；ID 或筛选条件 |
| `file_name` | VARCHAR(255) | NULL；仅文件名 |
| `file_path` | TEXT | NULL；后端内部绝对路径 |
| `record_count` | INTEGER | NOT NULL DEFAULT 0 |
| `error_message` | TEXT | NULL；脱敏、限制长度 |
| `created_at` / `expires_at` | DATETIME | NOT NULL UTC |

索引：`ix_export_jobs_user_created(user_id, created_at DESC)`、`ix_export_jobs_expiry(status, expires_at)`。

## 4. 事务边界

| 用例 | 必须原子完成 |
|---|---|
| 首次初始化/创建用户 | 用户、设置、模板、默认版本 |
| 发布模板 | 校验字段、插入版本、更新当前版本号 |
| 创建日报 | 读取当前版本、插入日报、快照和空内容 |
| 提交/自动归档 | 校验快照、状态条件更新、提交/归档时间 |
| 周报生成 | 周唯一性、读取来源、写周报/快照/来源关系 |
| 周报重生成 | 乐观锁、替换两份内容、来源快照和关系 |
| 修改/重置密码 | 更新哈希、密码时间、递增 token_version |

**首次初始化的并发安全**：“判断 `users` 是否为空”与“写入首个 admin”若拆成两条语句（先 `SELECT COUNT`，再 `INSERT`），两个并发请求可能都读到空表后各自写入，产生两个 admin。`AUTH-01`（`backend/app/repositories/user.py::create_if_no_users_exist`）改用单条 `INSERT INTO users (...) SELECT ... WHERE NOT EXISTS (SELECT id FROM users)`：SQLite 同一时刻只允许一个连接持有写锁执行这条语句，后到的调用要么阻塞到 `busy_timeout`、要么在拿到锁时重新求值 `NOT EXISTS`（此时已为假），从而插入 0 行——不需要新表或应用层锁即可保证互斥。后续任何“先查是否已存在、再写入单例/去重记录”的场景应复用同一模式，而不是引入独立的锁表。

## 5. 迁移与备份规范

- 只允许 Alembic 修改 schema，禁止启动时 `create_all` 代替迁移。
- 每个迁移包含 `upgrade` 和可行的 `downgrade`；不可逆迁移需在脚本和评审中明确说明。
- 迁移先在上一个发布版本的真实备份副本上验证。
- 应用迁移前执行 WAL checkpoint 和 SQLite backup API；备份成功后才迁移。
- 不允许修改已经发布的迁移文件；修复使用新迁移。
- 表/列/索引命名必须稳定，代码与本文不一致时先修改设计并获批。
- 初始 migration 必须一次性建立本文 V1 表、外键、CHECK、唯一约束和索引，并测试“空库 upgrade 到 head”；发布后不得回改该 migration。
- 迁移命令与数据文件必须使用测试专用临时目录验证，不得让测试读写真实 `userData` 或 `.local-data` 数据。
- **已知坑 1**：`alembic revision --autogenerate` 在 SQLite 方言下无法反射“表达式索引”（例如按 `desc()` 排序的列），会**静默丢弃**这类索引、不报错也不在 diff 里提示——初始迁移已实测踩过（`ix_daily_reports_user_date` 等 4 个 `DESC` 索引被自动漏掉）。每次跑完 autogenerate 必须把生成的 `upgrade()`/`downgrade()` 和 Model 逐项核对，手动补回表达式索引；这类索引要用模块级 `op.create_index(name, table, [..., sa.text('col DESC')])`，不要放进 `with op.batch_alter_table(...) as batch_op:` 里调用 `batch_op.create_index(...)`（其类型签名只接受纯字符串列名，混入 `sa.text()` 会被 mypy 拒绝）。
- **已知坑 2**：`run_startup_migrations()`（`backend/app/db/migrate.py`）内部用 `asyncio.run()` 驱动 Alembic，是同步函数。测试里如果在**异步** fixture 或异步测试函数内直接调用它，会报 `asyncio.run() cannot be called from a running event loop`。需要它的测试必须拆成两层 fixture：一个同步 fixture 先跑 `ensure_runtime_directories()` + `run_startup_migrations()`，再由一个依赖它的异步 fixture 创建 Engine/Session（参考 `backend/tests/test_model_constraints.py` 的 `migrated_settings`/`session_factory` 写法）。

## 6. 数据访问与删除策略

- 用户业务数据默认永久保留；V1 无删除用户/日报/周报 API。
- 禁用用户不删除数据。
- 导出临时文件下载后或 24 小时过期可清理，任务记录转为 `expired`。
- 手动整库备份是 admin 的受控运维能力；短期下载文件不登记业务表，使用进程内随机 ID 映射，15 分钟过期并在启动时清理残留。
- 所有业务 Repository 查询必须同时包含资源 ID 和 `user_id` 条件。
- 文件清理和备份轮转必须先校验解析后的目标位于配置目录内。

## 7. 实现验收门禁

- `uv run alembic upgrade head` 可在空数据库成功执行，且 `alembic current` 指向唯一 head。
- `PRAGMA foreign_keys`、`journal_mode`、`busy_timeout` 和 `synchronous` 的实际连接值有自动化验证。
- 唯一约束、CHECK、所有权过滤、乐观锁、事务回滚、数据库繁忙映射和迁移失败停止启动均有测试。
- migration、Model、Repository 字段命名与本文件一致；任何偏差先形成显式设计决策。
- 数据阶段通过 Ruff、mypy、pytest 后更新 `task.md`/`progress.md`，并单独创建 Conventional Commit。

## 8. 第二版数据库契约

### 8.1 表和关系

```text
users 1 --- n daily_report_days 1 --- n daily_reports
                         |
                         +--- n weekly_report_sources n --- 1 weekly_reports

users 1 --- n admin_audit_events (actor 可 SET NULL，目标仅保存逻辑标识)
```

#### `daily_report_days`

- 字段：`id` ULID PK、`user_id` FK RESTRICT、`work_date`、`status(open/archived)`、`archive_snapshot_json` nullable、`source_count` default 0、`archived_by` nullable FK RESTRICT、`archived_at` nullable、`version` default 1、时间戳。
- 唯一约束：`UNIQUE(user_id, work_date)`。
- 状态 CHECK：open 时正式快照/归档人/归档时间为空且来源数为 0；archived 时均完整且来源数大于 0。
- 索引：`(user_id, work_date DESC, id DESC)`、`(user_id, status, work_date DESC)`。

#### `daily_reports`

- 删除 V1 的 `user_id/work_date` 与 `uq_daily_reports_user_work_date`；新增 `day_id` FK `daily_report_days.id` RESTRICT 和全局唯一 `client_request_id VARCHAR(64)`。
- 保留条目 ID、三态、模板版本/快照、内容、乐观锁和时间戳。draft 的提交/归档时间均空；submitted 只有提交时间；archived 两者均有。
- 索引：`(day_id, status, submitted_at, id)`。所有权查询必须 join 日期表并约束其 `user_id`。

#### `weekly_report_sources`

- `daily_report_id` 改为 `daily_report_day_id`，FK 指向日期表，主键为 `(weekly_report_id, daily_report_day_id)`；历史值保持不变。

#### `admin_audit_events`

- 字段：`id`、受 CHECK 限制的 `action`、`actor_user_id` nullable/SET NULL、`actor_username_snapshot`、`target_type`、`target_id`、`target_owner_id` nullable、`reason`、`metadata_json`、`created_at`。
- 目标不建外键，保证被撤销条目随后作为草稿删除时，审计仍可保留；`metadata_json` 只能写白名单元数据，禁止正文和模板快照。

#### 其他表

- `users` 增加 `must_change_password BOOLEAN NOT NULL DEFAULT 0`。
- 重建 `user_settings` 删除 `auto_archive_on_submit`，保留 `timezone`。
- `weekly_reports` 的三份 JSON 升级为 `schema_version=2`，按日期包含来源条目数组。

### 8.2 正式快照和事务

`daily_report_days.archive_snapshot_json` 为不可变版本化 JSON：`schema_version/work_date/entries[]`；每个 entry 保存来源 ID、提交时间、模板版本、完整模板快照和内容。来源按 `submitted_at ASC, id ASC` 固化，不做跨来源字段压平。

日期级归档事务必须锁定/条件触碰日期行，复查 open、无 draft 且至少一个 submitted；同一事务构造快照、把全部 submitted 改为 archived、写同一归档时间并关闭日期。更新行数不一致立即回滚。创建、保存、删除、提交和 admin 撤销也必须先锁定同一日期行，以协调与归档的竞态。

**已实现（BE-10B）**：`DailyReportDayService.archive()`（`backend/app/services/daily_report_day.py`）用两段式实现锁定——先对日期行做 `status='open'` 条件 `UPDATE`（`touch_open_for_write`）抢占 SQLite 单写者锁并复查仍为 open，再读取当天条目决策（有 draft 返回 `40906`、无 submitted 返回 `40907`），最后批量翻转条目并翻转日期行为 archived；日期已归档时重复调用幂等返回既有结果。创建条目改用 `insert_entry_if_day_open`（`INSERT ... SELECT ... WHERE EXISTS`）单语句关闭"日期是否仍为 open"的检查竞态，与 `AUTH-01` 的 `create_if_no_users_exist` 同一模式；已用真实 `asyncio.gather` 验证创建与归档并发时二者互斥（XOR：要么创建的草稿使归档失败，要么归档已完成使创建返回 `40905`）。

### 8.3 V1 升级映射

1. 每个旧日报创建 `daily_report_days.id=old_daily_report.id`；旧 archived 变为 archived 日期和单来源正式快照，旧 draft/submitted 变为 open 日期。
2. 重建条目表，`day_id=old.id`、`client_request_id=old.id`，其余字段和字节内容保留。
3. 周报来源列改名且值不变；逐行把旧周报 `days[]` 包成 `schema_version=2` 的单 entry 结构。
4. 已有用户的强制改密标志为 false；重建设置表丢弃自动归档字段。
5. 验证日期数=旧日报数、条目数/周报来源数不变、归档日期数=旧 archived 数、`PRAGMA foreign_key_check` 无错误后提交。

downgrade 只有在每日期最多一条且周报快照可无损还原时允许；出现同日多条则明确拒绝，以升级前自动备份恢复，不得合并或删除用户数据。

### 8.4 第二版删除与统计

- 只允许物理删除 draft；删除最后条目后可在同事务清理空 open 日期行。submitted/archived 和 archived 日期均不可删除。
- 用户物理删除前检查日报日期/条目、周报、导出及其他业务记录；有任一业务记录返回冲突，只能停用。外键 RESTRICT 是并发最终防线。
- 月历、统计、周报和导出均按 `user_id + 日期范围` 收敛查询；完成日期只认 archived 日期，日报篇数按 submitted/archived 来源条目计数。

**已实现（BE-10B，删除部分）**：`DailyReportService.delete()` 条件删除 `status='draft'` 的条目，删除后若 `daily_report_days` 下无剩余条目则同事务删除该空 open 日期行（`DailyReportDayRepository.delete_if_empty_open`）。`UserService.delete_user()` 检查 `daily_report_days`/`weekly_reports`/`export_jobs`（`daily_reports` 通过日期容器传递覆盖，无需单独查询）；无记录时同事务清理 `user_settings`/`template_versions`/`report_templates` 默认关联资源后物理删除 `users` 行；检查后并发产生业务记录的场景由外键 `RESTRICT` 触发 `IntegrityError` 兜底捕获为 `40910`。

**已实现（BE-10C，统计/周报/导出部分）**：月历、周报和导出均已改为按 `user_id + 日期范围` 查询 `daily_report_days`（`list_in_range`/`list_archived_in_range`/`get_by_ids_for_owner_archived`），不再查询条目级 `daily_reports` 表；完成日期只认 `daily_report_days.status='archived'`；`daily_report_count` 按工作日期归属月份统计 `daily_reports.status IN ('submitted','archived')` 的来源条目（`DailyReportRepository.count_submitted_or_archived_in_range`），`weekly_report_count` 按 `weekly_reports.week_start` 所在月统计（`WeeklyReportRepository.count_by_week_start_range`），`current_streak_days` 按 `daily_report_days.status='archived'` 的 `work_date` 集合用今天/昨天规则向前查询（`DailyReportDayRepository.list_archived_work_dates_on_or_before`，无窗口限制，个人数据规模下可接受全量查询）。

## 9. 企业微信同步数据库目标（CR-20260808-02）

> 以下三张表尚未实现，进入 `WECOM-02` 后才创建迁移。

### 9.1 `wecom_user_bindings`

- `id` ULID PK；`user_id` FK/UNIQUE/RESTRICT。
- `credential_slot` UNIQUE，只是不透明随机槽位，不是路径，不含 Cookie。
- `wecom_vid`、`display_name`、可空 `corp_id`。
- `status in (connected,expired,disconnected)`、`last_validated_at`、`last_auth_error_at`、正整数 `version`、时间戳。

### 9.2 `wecom_sync_profiles`

- 每用户唯一一行；`form_id`、`template_id`、可空 `journal_uuid`。
- `destination_fingerprint`、`schema_fingerprint` 均为规范化 SHA-256。
- `question_mapping_json`、`recipient_config_json`、`field_mapping_json` 必须有 `schema_version` 并经 Pydantic 校验。
- 正整数 `version`、`is_active`、时间戳。该表即模板/映射配置，不再重复建模板配置表。

### 9.3 `wecom_daily_sync_records`

- owner、`daily_report_day_id`、`profile_id/profile_version`、目标和载荷指纹。
- 状态：`pending/syncing/succeeded/failed/auth_required/schema_changed/duplicate_detected/uncertain`。
- `attempt_count`、`attempt_token`、必要远端 ID、脱敏错误类型/短消息和尝试/成功时间。
- UNIQUE `(daily_report_day_id,destination_fingerprint)`；索引 `(user_id,status,updated_at)`。
- 不保存 payload/response 原文；同步正文可从不可变正式快照重建。

### 9.4 凭证与删除

- 不新增 Cookie 表。加密 Cookie 文件不属于 SQLite 备份；数据库只持有 `credential_slot`。
- 无同步历史用户可在删除用户事务中显式清理 profile/binding；有同步记录继续触发 `40910` 业务数据保护。
- 外部 HTTP 调用不持有数据库事务；状态预留和按 `attempt_token` 完成使用两个短事务。
