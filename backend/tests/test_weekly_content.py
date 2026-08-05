import json
from datetime import date

import pytest

from app.models import DailyReport
from app.services.weekly_report import (
    WeeklyWeekStartInvalidError,
    build_weekly_content,
    week_end_for,
)


def _fields(pairs: list[tuple[str, str, bool]]) -> str:
    return json.dumps(
        [
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
        ],
        ensure_ascii=False,
    )


def _report(work_date: date, *, fields: str, content: dict[str, object]) -> DailyReport:
    return DailyReport(
        id=f"day-{work_date.isoformat()}",
        user_id="owner",
        work_date=work_date,
        status="archived",
        template_version_id="version",
        template_snapshot_json=fields,
        content_json=json.dumps(content, ensure_ascii=False),
        version=1,
    )


def test_week_end_for_returns_the_following_sunday() -> None:
    assert week_end_for(date(2026, 8, 3)) == date(2026, 8, 9)


def test_week_end_for_rejects_a_non_monday_week_start() -> None:
    with pytest.raises(WeeklyWeekStartInvalidError):
        week_end_for(date(2026, 8, 4))


def test_week_end_for_handles_a_cross_year_week() -> None:
    assert week_end_for(date(2025, 12, 29)) == date(2026, 1, 4)


def test_build_weekly_content_only_carries_enabled_fields_in_sort_order() -> None:
    report = _report(
        date(2026, 8, 3),
        fields=_fields([("k2", "明日计划", True), ("k1", "今日工作", True), ("k3", "停用", False)]),
        content={"k1": "写代码", "k2": "写测试", "k3": "不应出现"},
    )

    content = build_weekly_content([report])

    assert len(content.days) == 1
    day = content.days[0]
    assert day.work_date == date(2026, 8, 3)
    assert day.daily_report_id == report.id
    assert [field.field_key for field in day.fields] == ["k2", "k1"]
    assert [field.value for field in day.fields] == ["写测试", "写代码"]


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
    report = _report(
        date(2026, 8, 3),
        fields=_fields([("k1", "今日工作", True)]),
        content={},
    )

    content = build_weekly_content([report])

    assert content.days[0].fields[0].value is None
