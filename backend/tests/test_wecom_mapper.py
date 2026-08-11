from datetime import UTC, date, datetime

import pytest

from app.core.ulid import generate_ulid
from app.schemas.daily_report_day import DayArchiveSnapshotData, DayArchiveSnapshotEntryData
from app.schemas.template import CoreType, FieldType, TemplateFieldData
from app.schemas.wecom import (
    FieldMappingTarget,
    UnmappedFieldPolicy,
    WeComFieldMappingConfig,
    WeComFieldMappingRule,
    WeComQuestionSpec,
    WeComReplyType,
)
from app.services.wecom_mapper import build_wecom_preview, compute_schema_fingerprint

_SUBMITTED_AT = datetime(2026, 8, 8, 9, 0, tzinfo=UTC)


def _field(
    key: str,
    label: str,
    *,
    sort_order: int,
    field_type: FieldType = "text",
    core_type: CoreType | None = None,
    required: bool = False,
    enabled: bool = True,
    options: list[str] | None = None,
) -> TemplateFieldData:
    return TemplateFieldData(
        field_key=key,
        label=label,
        description="",
        field_type=field_type,
        required=required,
        enabled=enabled,
        sort_order=sort_order,
        options=options or [],
        core_type=core_type,
    )


def _entry(
    *,
    template_snapshot: list[TemplateFieldData],
    content: dict[str, object],
    daily_report_id: str | None = None,
    submitted_at: datetime = _SUBMITTED_AT,
    template_version_id: str = "template-version-1",
) -> DayArchiveSnapshotEntryData:
    return DayArchiveSnapshotEntryData(
        daily_report_id=daily_report_id or generate_ulid(),
        submitted_at=submitted_at,
        template_version_id=template_version_id,
        template_snapshot=template_snapshot,
        content=content,
    )


def _snapshot(
    entries: list[DayArchiveSnapshotEntryData], *, work_date: date = date(2026, 8, 8)
) -> DayArchiveSnapshotData:
    return DayArchiveSnapshotData(work_date=work_date, entries=entries)


def _field_mapping(
    rules: list[WeComFieldMappingRule] | None = None,
    *,
    unmapped_policy: UnmappedFieldPolicy = "block",
) -> WeComFieldMappingConfig:
    return WeComFieldMappingConfig(
        schema_version=1, rules=rules or [], unmapped_policy=unmapped_policy
    )


def _rule(field_key: str, target: FieldMappingTarget) -> WeComFieldMappingRule:
    return WeComFieldMappingRule(field_key=field_key, target=target)


def _spec(
    question_id: str,
    *,
    reply_type: WeComReplyType,
    sub_type: str | None = None,
    submit_order: int = 0,
) -> WeComQuestionSpec:
    return WeComQuestionSpec(
        question_id=question_id, reply_type=reply_type, sub_type=sub_type, submit_order=submit_order
    )


def _minimal_entry() -> DayArchiveSnapshotEntryData:
    key = "today-text"
    fields = [
        _field(key, "今日工作内容", sort_order=10, field_type="textarea", core_type="today_work")
    ]
    return _entry(template_snapshot=fields, content={key: "内容"})


# --- Core fields (date/today/tomorrow) -------------------------------------


def test_core_today_and_tomorrow_fields_map_directly() -> None:
    today_key = "today-field"
    tomorrow_key = "tomorrow-field"
    fields = [
        _field(
            today_key, "今日工作内容", sort_order=10, field_type="textarea", core_type="today_work"
        ),
        _field(
            tomorrow_key,
            "明日工作计划",
            sort_order=20,
            field_type="textarea",
            core_type="tomorrow_plan",
        ),
    ]
    entry = _entry(
        template_snapshot=fields,
        content={today_key: "完成了模块A开发", tomorrow_key: "开始模块B设计"},
    )
    snapshot = _snapshot([entry])

    preview = build_wecom_preview(snapshot, _field_mapping())

    assert preview.date_answer == "2026年08月08日"
    assert preview.today_work_answer == "完成了模块A开发"
    assert preview.tomorrow_plan_answer == "开始模块B设计"
    assert preview.source_count == 1
    assert preview.today_work_char_count == len("完成了模块A开发")
    assert preview.tomorrow_plan_char_count == len("开始模块B设计")
    assert preview.unmapped_field_keys == []


def test_zero_entries_snapshot_produces_empty_answers_without_crashing() -> None:
    snapshot = _snapshot([], work_date=date(2026, 8, 8))

    preview = build_wecom_preview(snapshot, _field_mapping())

    assert preview.source_count == 0
    assert preview.today_work_answer == ""
    assert preview.tomorrow_plan_answer == ""
    assert preview.date_answer == "2026年08月08日"
    assert preview.unmapped_field_keys == []


# --- Dynamic custom fields ---------------------------------------------------


def test_custom_field_with_a_mapping_rule_is_appended_with_its_label() -> None:
    """Resolves the §7.1 vs §7.2 "责任人" ambiguity: an independent

    责任人-labeled custom field (as opposed to `ProjectListEntry.owner`,
    which PROD-028 excludes from the sync text entirely — see
    `test_responsible_person_is_a_custom_field_appended_after_project_list_blocks`)
    is mapped like any other custom field and formatted with the generic
    "标签:格式化值" rule.
    """
    responsible_key = generate_ulid()
    fields = [_field(responsible_key, "责任人", sort_order=30, field_type="text")]
    entry = _entry(template_snapshot=fields, content={responsible_key: "张三"})
    snapshot = _snapshot([entry])
    mapping = _field_mapping([_rule(responsible_key, "today_work")])

    preview = build_wecom_preview(snapshot, mapping)

    assert preview.today_work_answer == "责任人:张三"
    assert preview.unmapped_field_keys == []


def test_custom_field_rule_can_target_tomorrow_plan() -> None:
    risk_key = generate_ulid()
    fields = [_field(risk_key, "风险提示", sort_order=30, field_type="text")]
    entry = _entry(template_snapshot=fields, content={risk_key: "接口联调风险"})
    snapshot = _snapshot([entry])
    mapping = _field_mapping([_rule(risk_key, "tomorrow_plan")])

    preview = build_wecom_preview(snapshot, mapping)

    assert preview.tomorrow_plan_answer == "风险提示:接口联调风险"
    assert preview.today_work_answer == ""


def test_unmapped_custom_field_is_recorded_when_policy_is_block() -> None:
    note_key = generate_ulid()
    fields = [_field(note_key, "备注", sort_order=30, field_type="text")]
    entry = _entry(template_snapshot=fields, content={note_key: "有一些备注"})
    snapshot = _snapshot([entry])

    preview = build_wecom_preview(snapshot, _field_mapping(unmapped_policy="block"))

    assert preview.unmapped_field_keys == [note_key]
    assert preview.today_work_answer == ""
    assert preview.tomorrow_plan_answer == ""


def test_unmapped_custom_field_is_silently_skipped_when_policy_is_ignore() -> None:
    note_key = generate_ulid()
    fields = [_field(note_key, "备注", sort_order=30, field_type="text")]
    entry = _entry(template_snapshot=fields, content={note_key: "有一些备注"})
    snapshot = _snapshot([entry])

    preview = build_wecom_preview(snapshot, _field_mapping(unmapped_policy="ignore"))

    assert preview.unmapped_field_keys == []
    assert preview.today_work_answer == ""


def test_a_rule_targeting_ignore_drops_the_field_even_though_it_has_a_value() -> None:
    note_key = generate_ulid()
    fields = [_field(note_key, "备注", sort_order=30, field_type="text")]
    entry = _entry(template_snapshot=fields, content={note_key: "不需要同步"})
    snapshot = _snapshot([entry])
    mapping = _field_mapping([_rule(note_key, "ignore")])

    preview = build_wecom_preview(snapshot, mapping)

    assert preview.unmapped_field_keys == []
    assert preview.today_work_answer == ""
    assert preview.tomorrow_plan_answer == ""


def test_unmapped_field_keys_are_deduplicated_across_multiple_sources() -> None:
    note_key = generate_ulid()
    fields = [_field(note_key, "备注", sort_order=10, field_type="text")]
    first = _entry(template_snapshot=fields, content={note_key: "第一篇备注"})
    second = _entry(template_snapshot=fields, content={note_key: "第二篇备注"})
    snapshot = _snapshot([first, second])

    preview = build_wecom_preview(snapshot, _field_mapping(unmapped_policy="block"))

    assert preview.unmapped_field_keys == [note_key]


def test_zero_is_not_treated_as_an_empty_value() -> None:
    count_key = generate_ulid()
    fields = [_field(count_key, "数量", sort_order=10, field_type="number")]
    entry = _entry(template_snapshot=fields, content={count_key: 0})
    snapshot = _snapshot([entry])
    mapping = _field_mapping([_rule(count_key, "today_work")])

    preview = build_wecom_preview(snapshot, mapping)

    assert preview.today_work_answer == "数量:0"


def test_multiselect_values_join_with_a_dun_hao_separator() -> None:
    tag_key = generate_ulid()
    fields = [
        _field(
            tag_key,
            "标签",
            sort_order=10,
            field_type="multiselect",
            options=["前端", "后端", "测试"],
        )
    ]
    entry = _entry(template_snapshot=fields, content={tag_key: ["前端", "后端"]})
    snapshot = _snapshot([entry])
    mapping = _field_mapping([_rule(tag_key, "today_work")])

    preview = build_wecom_preview(snapshot, mapping)

    assert preview.today_work_answer == "标签:前端、后端"


def test_disabled_field_is_skipped_even_if_it_somehow_carries_a_value() -> None:
    """Defensive: `validate_daily_content` never lets a disabled field's key

    into `content` in the first place, but the mapper explicitly skips
    disabled fields rather than relying solely on that upstream invariant.
    """
    key = generate_ulid()
    fields = [_field(key, "已停用字段", sort_order=10, field_type="text", enabled=False)]
    entry = _entry(template_snapshot=fields, content={key: "不应出现"})
    snapshot = _snapshot([entry])
    mapping = _field_mapping([_rule(key, "today_work")])

    preview = build_wecom_preview(snapshot, mapping)

    assert preview.today_work_answer == ""
    assert preview.unmapped_field_keys == []


# --- PROJECT_LIST -------------------------------------------------------------


def test_project_list_single_item_formats_two_lines() -> None:
    key = generate_ulid()
    fields = [_field(key, "项目列表", sort_order=10, field_type="PROJECT_LIST")]
    entry = _entry(
        template_snapshot=fields,
        content={key: [{"project": "报表系统", "content": "完成导出", "owner": "张三"}]},
    )
    snapshot = _snapshot([entry])

    preview = build_wecom_preview(snapshot, _field_mapping())

    # PROD-028: `owner`/`assistant`/... are internal-only tracking fields —
    # only `project`/`content` ever reach the WeCom sync text.
    assert preview.today_work_answer == "项目:报表系统\n工作内容:完成导出"


def test_project_list_multiple_items_blank_line_separated() -> None:
    key = generate_ulid()
    fields = [_field(key, "项目列表", sort_order=10, field_type="PROJECT_LIST")]
    entry = _entry(
        template_snapshot=fields,
        content={
            key: [
                {"project": "P1", "content": "C1"},
                {"project": "P2", "content": "C2"},
                {"project": "P3", "content": "C3"},
            ]
        },
    )
    snapshot = _snapshot([entry])

    preview = build_wecom_preview(snapshot, _field_mapping())

    assert preview.today_work_answer == (
        "项目:P1\n工作内容:C1\n\n项目:P2\n工作内容:C2\n\n项目:P3\n工作内容:C3"
    )


def test_project_list_field_type_wins_over_a_coincidental_today_work_core_type() -> None:
    """§7 priority rule: PROJECT_LIST formatting applies even if `core_type`

    happens to also be `today_work` — a shape the real template editor
    never produces (`PROJECT_LIST` is always a custom field), but the
    mapper must not silently fall back to raw-text formatting if it does.
    """
    key = generate_ulid()
    fields = [
        _field(key, "项目列表", sort_order=10, field_type="PROJECT_LIST", core_type="today_work")
    ]
    entry = _entry(
        template_snapshot=fields,
        content={key: [{"project": "P1", "content": "C1"}]},
    )
    snapshot = _snapshot([entry])

    preview = build_wecom_preview(snapshot, _field_mapping())

    assert preview.today_work_answer == "项目:P1\n工作内容:C1"


def test_project_list_coexists_with_the_core_today_work_text_field() -> None:
    text_key = "today-text"
    list_key = generate_ulid()
    fields = [
        _field(
            text_key, "今日工作内容", sort_order=10, field_type="textarea", core_type="today_work"
        ),
        _field(list_key, "项目列表", sort_order=20, field_type="PROJECT_LIST"),
    ]
    entry = _entry(
        template_snapshot=fields,
        content={
            text_key: "整体进展顺利",
            list_key: [{"project": "P1", "content": "C1"}],
        },
    )
    snapshot = _snapshot([entry])

    preview = build_wecom_preview(snapshot, _field_mapping())

    assert preview.today_work_answer == "整体进展顺利\n项目:P1\n工作内容:C1"


def test_empty_project_list_contributes_nothing() -> None:
    key = generate_ulid()
    fields = [_field(key, "项目列表", sort_order=10, field_type="PROJECT_LIST")]
    entry = _entry(template_snapshot=fields, content={key: []})
    snapshot = _snapshot([entry])

    preview = build_wecom_preview(snapshot, _field_mapping())

    assert preview.today_work_answer == ""


def test_responsible_person_is_a_custom_field_appended_after_project_list_blocks() -> None:
    """The independent 责任人-labeled custom field here is unrelated to

    `ProjectListEntry.owner` (PROD-028) — see `wecom_mapper.py`'s "责任人"
    docstring section for why both can coexist without the entry's own
    `owner` ever reaching the sync text.
    """
    list_key = generate_ulid()
    owner_key = generate_ulid()
    fields = [
        _field(list_key, "项目列表", sort_order=10, field_type="PROJECT_LIST"),
        _field(owner_key, "责任人", sort_order=20, field_type="text"),
    ]
    entry = _entry(
        template_snapshot=fields,
        content={
            list_key: [{"project": "P1", "content": "C1", "owner": "王五"}],
            owner_key: "李四",
        },
    )
    snapshot = _snapshot([entry])
    mapping = _field_mapping([_rule(owner_key, "today_work")])

    preview = build_wecom_preview(snapshot, mapping)

    assert preview.today_work_answer == "项目:P1\n工作内容:C1\n责任人:李四"


# --- Multi-source (same-day multiple entries) --------------------------------


def test_single_source_has_no_section_header() -> None:
    preview = build_wecom_preview(_snapshot([_minimal_entry()]), _field_mapping())

    assert preview.today_work_answer == "内容"
    assert "日报" not in preview.today_work_answer


def test_multiple_sources_get_numbered_section_headers_in_snapshot_order() -> None:
    key = "today-text"
    fields = [
        _field(key, "今日工作内容", sort_order=10, field_type="textarea", core_type="today_work")
    ]
    first = _entry(
        template_snapshot=fields,
        content={key: "第一篇内容"},
        submitted_at=datetime(2026, 8, 8, 9, 0, tzinfo=UTC),
    )
    second = _entry(
        template_snapshot=fields,
        content={key: "第二篇内容"},
        submitted_at=datetime(2026, 8, 8, 14, 0, tzinfo=UTC),
    )
    snapshot = _snapshot([first, second])

    preview = build_wecom_preview(snapshot, _field_mapping())

    assert preview.today_work_answer == "日报 1\n第一篇内容\n\n日报 2\n第二篇内容"
    assert preview.source_count == 2


def test_three_sources_preserve_snapshot_order_even_when_one_is_empty() -> None:
    key = "today-text"
    fields = [
        _field(key, "今日工作内容", sort_order=10, field_type="textarea", core_type="today_work")
    ]
    first = _entry(template_snapshot=fields, content={key: "第一篇"})
    second = _entry(template_snapshot=fields, content={key: ""})
    third = _entry(template_snapshot=fields, content={key: "第三篇"})
    snapshot = _snapshot([first, second, third])

    preview = build_wecom_preview(snapshot, _field_mapping())

    assert preview.today_work_answer == "日报 1\n第一篇\n\n日报 2\n\n日报 3\n第三篇"
    assert preview.source_count == 3


# --- Empty values leave no trace ---------------------------------------------


def test_none_blank_and_empty_list_values_leave_no_trace() -> None:
    today_key = "today-text"
    note_key = generate_ulid()
    multiselect_key = generate_ulid()
    fields = [
        _field(
            today_key, "今日工作内容", sort_order=10, field_type="textarea", core_type="today_work"
        ),
        _field(note_key, "备注", sort_order=20, field_type="text"),
        _field(
            multiselect_key, "标签", sort_order=30, field_type="multiselect", options=["a", "b"]
        ),
    ]
    entry = _entry(
        template_snapshot=fields,
        content={today_key: None, note_key: "   ", multiselect_key: []},
    )
    snapshot = _snapshot([entry])
    mapping = _field_mapping([_rule(note_key, "today_work"), _rule(multiselect_key, "today_work")])

    preview = build_wecom_preview(snapshot, mapping)

    assert preview.today_work_answer == ""
    assert preview.today_work_char_count == 0
    assert preview.unmapped_field_keys == []


# --- Date formatting (including calendar boundaries) --------------------------


@pytest.mark.parametrize(
    ("work_date", "expected"),
    [
        (date(2026, 2, 28), "2026年02月28日"),
        (date(2028, 2, 29), "2028年02月29日"),  # leap day
        (date(2025, 12, 31), "2025年12月31日"),
        (date(2026, 1, 1), "2026年01月01日"),
    ],
)
def test_date_answer_formats_boundary_dates_correctly(work_date: date, expected: str) -> None:
    snapshot = _snapshot([_minimal_entry()], work_date=work_date)

    preview = build_wecom_preview(snapshot, _field_mapping())

    assert preview.date_answer == expected


# --- Historical multi-template isolation --------------------------------------


def test_each_entry_uses_only_its_own_template_snapshot_not_a_global_current_template() -> None:
    """Two different template "versions" (different field sets and different

    field order) coexist within one day's entries; the mapper must route
    each purely from its own `template_snapshot`/`content` pair, never from
    "the current template" and never from another entry's snapshot.
    """
    old_today_key = "old-today"
    old_note_key = generate_ulid()
    old_fields = [
        _field(
            old_today_key, "今日工作", sort_order=10, field_type="textarea", core_type="today_work"
        ),
        _field(old_note_key, "旧备注字段", sort_order=20, field_type="text"),
    ]
    new_today_key = "new-today"
    new_tomorrow_key = "new-tomorrow"
    new_fields = [
        # Reversed sort_order relative to declaration order, and a
        # different field set entirely (`old_note_key` does not exist here).
        _field(
            new_tomorrow_key,
            "明日计划",
            sort_order=10,
            field_type="textarea",
            core_type="tomorrow_plan",
        ),
        _field(
            new_today_key,
            "今日工作内容",
            sort_order=20,
            field_type="textarea",
            core_type="today_work",
        ),
    ]

    old_entry = _entry(
        template_snapshot=old_fields,
        content={old_today_key: "旧模板今日内容", old_note_key: "旧模板备注"},
        submitted_at=datetime(2026, 8, 8, 8, 0, tzinfo=UTC),
        template_version_id="template-version-old",
    )
    new_entry = _entry(
        template_snapshot=new_fields,
        content={new_today_key: "新模板今日内容", new_tomorrow_key: "新模板明日内容"},
        submitted_at=datetime(2026, 8, 8, 15, 0, tzinfo=UTC),
        template_version_id="template-version-new",
    )
    snapshot = _snapshot([old_entry, new_entry])
    mapping = _field_mapping([_rule(old_note_key, "today_work")])

    preview = build_wecom_preview(snapshot, mapping)

    assert preview.today_work_answer == (
        "日报 1\n旧模板今日内容\n旧备注字段:旧模板备注\n\n日报 2\n新模板今日内容"
    )
    assert preview.tomorrow_plan_answer == "日报 1\n\n日报 2\n新模板明日内容"


# --- compute_schema_fingerprint ------------------------------------------------


def test_schema_fingerprint_is_deterministic_and_well_formed() -> None:
    date_q = _spec("q-date", reply_type="date", submit_order=0)
    today_q = _spec("q-today", reply_type="text", submit_order=1)
    tomorrow_q = _spec("q-tomorrow", reply_type="text", submit_order=2)

    first = compute_schema_fingerprint(date_q, today_q, tomorrow_q)
    second = compute_schema_fingerprint(date_q, today_q, tomorrow_q)

    assert first == second
    assert len(first) == 64
    assert first == first.lower()
    int(first, 16)  # must be valid hex


def test_schema_fingerprint_changes_when_question_id_changes() -> None:
    today_q = _spec("q-today", reply_type="text", submit_order=1)
    tomorrow_q = _spec("q-tomorrow", reply_type="text", submit_order=2)
    baseline = compute_schema_fingerprint(
        _spec("q-date", reply_type="date", submit_order=0), today_q, tomorrow_q
    )

    changed = compute_schema_fingerprint(
        _spec("q-date-2", reply_type="date", submit_order=0), today_q, tomorrow_q
    )

    assert changed != baseline


def test_schema_fingerprint_changes_when_reply_type_changes() -> None:
    date_q = _spec("q-date", reply_type="date", submit_order=0)
    tomorrow_q = _spec("q-tomorrow", reply_type="text", submit_order=2)
    baseline = compute_schema_fingerprint(
        date_q, _spec("q-today", reply_type="text", submit_order=1), tomorrow_q
    )

    changed = compute_schema_fingerprint(
        date_q, _spec("q-today", reply_type="select", submit_order=1), tomorrow_q
    )

    assert changed != baseline


def test_schema_fingerprint_ignores_sub_type() -> None:
    """`ISS-040`: `sub_type` deliberately does not participate — the
    execute-time structure source (`formcol/detail`) never carries `ext`
    and so can never populate it, which would otherwise make every
    execute-time fingerprint permanently mismatch the connect-time one."""
    today_q = _spec("q-today", reply_type="text", submit_order=1)
    tomorrow_q = _spec("q-tomorrow", reply_type="text", submit_order=2)

    full_fp = compute_schema_fingerprint(
        _spec("q-date", reply_type="date", sub_type="full", submit_order=0), today_q, tomorrow_q
    )
    short_fp = compute_schema_fingerprint(
        _spec("q-date", reply_type="date", sub_type="short", submit_order=0), today_q, tomorrow_q
    )
    none_fp = compute_schema_fingerprint(
        _spec("q-date", reply_type="date", sub_type=None, submit_order=0), today_q, tomorrow_q
    )

    assert full_fp == short_fp == none_fp


# --- payload_fingerprint (via build_wecom_preview) -----------------------------


def test_payload_fingerprint_is_deterministic_and_well_formed() -> None:
    snapshot = _snapshot([_minimal_entry()])
    mapping = _field_mapping()

    first = build_wecom_preview(snapshot, mapping).payload_fingerprint
    second = build_wecom_preview(snapshot, mapping).payload_fingerprint

    assert first == second
    assert len(first) == 64
    assert first == first.lower()
    int(first, 16)  # must be valid hex


def test_payload_fingerprint_changes_when_snapshot_content_changes() -> None:
    key = "today-text"
    fields = [
        _field(key, "今日工作内容", sort_order=10, field_type="textarea", core_type="today_work")
    ]
    mapping = _field_mapping()
    baseline_snapshot = _snapshot([_entry(template_snapshot=fields, content={key: "内容A"})])
    changed_snapshot = _snapshot([_entry(template_snapshot=fields, content={key: "内容B"})])

    baseline = build_wecom_preview(baseline_snapshot, mapping).payload_fingerprint
    changed = build_wecom_preview(changed_snapshot, mapping).payload_fingerprint

    assert baseline != changed


def test_payload_fingerprint_changes_when_field_mapping_changes() -> None:
    note_key = generate_ulid()
    fields = [_field(note_key, "备注", sort_order=10, field_type="text")]
    entry = _entry(template_snapshot=fields, content={note_key: "内容"})
    snapshot = _snapshot([entry])

    unmapped = build_wecom_preview(snapshot, _field_mapping()).payload_fingerprint
    mapped = build_wecom_preview(
        snapshot, _field_mapping([_rule(note_key, "today_work")])
    ).payload_fingerprint

    assert unmapped != mapped
