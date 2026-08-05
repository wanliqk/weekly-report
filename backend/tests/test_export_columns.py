from app.schemas.template import FieldType, TemplateFieldData
from app.services.export import plan_export_columns


def _field(
    key: str, label: str, *, sort_order: int, field_type: FieldType = "text"
) -> TemplateFieldData:
    return TemplateFieldData(
        field_key=key,
        label=label,
        description="",
        field_type=field_type,
        required=False,
        enabled=True,
        sort_order=sort_order,
        options=[],
    )


def test_columns_follow_first_seen_order_across_snapshots() -> None:
    older = [_field("k1", "今日工作", sort_order=10), _field("k2", "明日计划", sort_order=20)]
    newer = [
        _field("k1", "今日工作", sort_order=10),
        _field("k2", "明日计划", sort_order=20),
        _field("k3", "风险", sort_order=30),
    ]

    columns = plan_export_columns([older, newer])

    assert [column.field_key for column in columns] == ["k1", "k2", "k3"]


def test_label_change_does_not_split_the_column_but_latest_label_wins() -> None:
    older = [_field("k1", "今日进展", sort_order=10)]
    newer = [_field("k1", "今日工作内容", sort_order=10)]

    columns = plan_export_columns([older, newer])

    assert len(columns) == 1
    assert columns[0].header == "今日工作内容"


def test_field_removed_from_later_template_still_appears_after_current_fields() -> None:
    older = [_field("k1", "旧字段", sort_order=10), _field("k2", "今日工作", sort_order=20)]
    newer = [_field("k2", "今日工作", sort_order=10)]

    columns = plan_export_columns([older, newer])

    assert [column.field_key for column in columns] == ["k1", "k2"]


def test_duplicate_labels_across_different_field_keys_are_disambiguated() -> None:
    snapshot = [
        _field("01AAAAAAAAAAAAAAAAAAAAAAAA", "备注", sort_order=10),
        _field("01BBBBBBBBBBBBBBBBBBBBBBBB", "备注", sort_order=20),
    ]

    columns = plan_export_columns([snapshot])

    headers = [column.header for column in columns]
    assert headers == ["备注(AAAA)", "备注(BBBB)"]
    assert len(set(headers)) == 2


def test_empty_snapshot_list_produces_no_columns() -> None:
    assert plan_export_columns([]) == []
