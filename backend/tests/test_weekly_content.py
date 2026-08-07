import json
from datetime import UTC, date, datetime

import pytest

from app.models import DailyReportDay
from app.services.weekly_report import (
    WeeklyWeekStartInvalidError,
    build_weekly_content,
    week_end_for,
)

_SUBMITTED_AT = datetime(2026, 8, 3, 9, 0, 0, tzinfo=UTC)


def _fields(pairs: list[tuple[str, str, bool]]) -> list[dict[str, object]]:
    return [
        {
            "field_key": key,
            "label": label,
            "description": "",
            "field_type": "text",
            "required": False,
            "enabled": enabled,
            "sort_order": index * 10,
            "options": [],
            "core_type": None,
        }
        for index, (key, label, enabled) in enumerate(pairs)
    ]


def _archived_day(
    work_date: date,
    *,
    entries: list[tuple[str, list[dict[str, object]], dict[str, object]]],
) -> DailyReportDay:
    """Builds an archived day whose snapshot holds the given (id, fields, content) entries."""
    day_id = f"day-{work_date.isoformat()}"
    snapshot = {
        "schema_version": 2,
        "work_date": work_date.isoformat(),
        "entries": [
            {
                "daily_report_id": entry_id,
                "submitted_at": _SUBMITTED_AT.isoformat(),
                "template_version_id": "version",
                "template_snapshot": fields,
                "content": content,
            }
            for entry_id, fields, content in entries
        ],
    }
    return DailyReportDay(
        id=day_id,
        user_id="owner",
        work_date=work_date,
        status="archived",
        archive_snapshot_json=json.dumps(snapshot, ensure_ascii=False),
        source_count=len(entries),
        archived_by="owner",
        archived_at=_SUBMITTED_AT,
        version=2,
    )


def test_week_end_for_returns_the_following_sunday() -> None:
    assert week_end_for(date(2026, 8, 3)) == date(2026, 8, 9)


def test_week_end_for_rejects_a_non_monday_week_start() -> None:
    with pytest.raises(WeeklyWeekStartInvalidError):
        week_end_for(date(2026, 8, 4))


def test_week_end_for_handles_a_cross_year_week() -> None:
    assert week_end_for(date(2025, 12, 29)) == date(2026, 1, 4)


def test_build_weekly_content_only_carries_enabled_fields_in_sort_order() -> None:
    day = _archived_day(
        date(2026, 8, 3),
        entries=[
            (
                "entry-1",
                _fields(
                    [("k2", "明日计划", True), ("k1", "今日工作", True), ("k3", "停用", False)]
                ),
                {"k1": "写代码", "k2": "写测试", "k3": "不应出现"},
            )
        ],
    )

    content = build_weekly_content([day])

    assert len(content.days) == 1
    weekly_day = content.days[0]
    assert weekly_day.work_date == date(2026, 8, 3)
    assert weekly_day.daily_report_day_id == day.id
    assert len(weekly_day.entries) == 1
    entry = weekly_day.entries[0]
    assert entry.daily_report_id == "entry-1"
    assert [field.field_key for field in entry.fields] == ["k2", "k1"]
    assert [field.value for field in entry.fields] == ["写测试", "写代码"]


def test_build_weekly_content_defaults_free_text_areas_to_empty() -> None:
    content = build_weekly_content([])

    assert content.days == []
    assert content.supplement == ""
    assert content.next_week_plan == ""
    assert content.risks == ""


def test_build_weekly_content_preserves_supplied_free_text() -> None:
    content = build_weekly_content(
        [], supplement="补充说明", next_week_plan="下周计划", risks="风险项"
    )

    assert content.supplement == "补充说明"
    assert content.next_week_plan == "下周计划"
    assert content.risks == "风险项"


def test_build_weekly_content_missing_value_becomes_none() -> None:
    day = _archived_day(
        date(2026, 8, 3),
        entries=[("entry-1", _fields([("k1", "今日工作", True)]), {})],
    )

    content = build_weekly_content([day])

    assert content.days[0].entries[0].fields[0].value is None


def test_build_weekly_content_preserves_every_source_entry_for_a_multi_entry_day() -> None:
    day = _archived_day(
        date(2026, 8, 3),
        entries=[
            ("entry-1", _fields([("k1", "今日工作", True)]), {"k1": "上午的工作"}),
            ("entry-2", _fields([("k1", "今日工作", True)]), {"k1": "下午的工作"}),
        ],
    )

    content = build_weekly_content([day])

    assert len(content.days) == 1
    assert len(content.days[0].entries) == 2
    assert [entry.daily_report_id for entry in content.days[0].entries] == ["entry-1", "entry-2"]
    assert [entry.fields[0].value for entry in content.days[0].entries] == [
        "上午的工作",
        "下午的工作",
    ]
