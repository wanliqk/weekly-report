# 数据库设计

> 状态：目标数据库契约已基线化（V1；尚未实现）
> 更新日期：2026-08-05
> 数据库：SQLite（SQLAlchemy 2.x + Alembic）

## 0. 当前实现状态

- 阶段 3（`DB-01`/`DB-02`/`DB-03`）已实现：异步 Engine/Session（`backend/app/db/engine.py`、`session.py`）、PRAGMA（`foreign_keys`/`journal_mode=WAL`/`synchronous=NORMAL`/`busy_timeout`）、8 张业务表的 SQLAlchemy Model（`backend/app/models/`）、Alembic 初始迁移（`backend/alembic/versions/3f6f955b87bb_initial_schema.py`）、启动时迁移前备份/轮转（`backend/app/db/migrate.py`）均已落地，代码与测试为准，未使用 `create_all()` 代替迁移。
- 下列表、约束、索引、事务与备份**规则**仍是权威契约来源；实现细节（如具体文件路径）以代码为准，本节只记录"哪些已经真实存在"，不重复描述设计意图。
- Repository、Service 层（`backend/app/repositories/`、`app/services/`）尚未实现，仍是空壳；本文件描述的"所有权过滤查询""乐观锁条件更新"等业务访问模式，目前只在 `backend/tests/test_model_constraints.py` 中以 ORM 直接操作的方式验证了可行性，尚无业务代码强制执行——阶段 4 起的 Repository/Service 落地时必须遵循本文件规则，不得引入新的访问模式。
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
