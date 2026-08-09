"""Deterministic mapper: a formal daily snapshot -> the WeCom three-question answers.

`docs/方案设计.md` §7 (read in full, not the one-line `ai-docs/modules.md`
summary — `ai-docs/issues.md` ISS-023 records why that distinction matters
in this codebase) defines the routing and formatting rules implemented
here. This module is a pure transformation layer: no I/O, no database
access, no network calls, no knowledge of `wecom_sync_profiles` rows.
`WECOM-06` owns persisting results, invoking this module, and deciding
whether a non-empty `unmapped_field_keys` actually blocks a sync — this
module only reports facts.

## The "责任人" ambiguity, resolved

§7.2's `PROJECT_LIST` example block shows a "责任人" line directly under
"完成状态", which reads as if every project entry carried its own 责任人.
§7.1's table describes it differently: "责任人类自定义字段" is listed as an
independent custom field routed to `today_work` via `field_mapping_json`,
using the generic "label: formatted value" rule — the same rule that
applies to any other custom field, not a `PROJECT_LIST`-specific one.

The real data model settles this: `ProjectListEntry`
(`app/schemas/daily_report.py`) only has `project`, `content`, `status` —
there is no per-entry 责任人 attribute anywhere in the schema, and
`default_template_fields()` (`app/services/user.py`) never creates one
either. `PROJECT_LIST` is always a *custom* field (`core_type is None`);
"责任人" is therefore treated here as what the schema actually supports: an
ordinary custom field that a user maps to `today_work` like any other,
formatted as "责任人:<value>" and appended, in `template_snapshot`
`sort_order`, after any `PROJECT_LIST` blocks in the same entry. No
`PROJECT_LIST`-specific "responsible person" sub-line is invented.

## Half-width `:` instead of the design doc's full-width colon

`docs/方案设计.md` §7.2's literal example text uses the full-width Chinese
colon (U+FF1A). Every existing Python source file in this repository
(`app/**`, checked repo-wide) avoids full-width Chinese punctuation
entirely: Ruff's `RUF001`/`RUF002`/`RUF003`
(`ambiguous-unicode-character-*`) are enabled with no per-file-ignore and
no `noqa` usage anywhere, and existing Chinese message strings
consistently use spaces or half-width punctuation instead of full-width
commas/colons/parentheses. This module follows that established,
repo-wide convention rather than reproducing the design doc's exact
glyph: every "label: value" line emitted here uses a half-width `:`. This
is a deliberate, reported deviation from the literal example text.
"""

import hashlib
import json
from datetime import date

from pydantic import BaseModel

from app.schemas.daily_report import DailyFieldValue, ProjectListEntry
from app.schemas.daily_report_day import DayArchiveSnapshotData, DayArchiveSnapshotEntryData
from app.schemas.template import TemplateFieldData
from app.schemas.wecom import WeComFieldMappingConfig, WeComQuestionSpec

# `docs/方案设计.md` §7.2 fixed status labels.
_PROJECT_STATUS_LABELS: dict[str, str] = {
    "TODO": "待开始",
    "DOING": "进行中",
    "DONE": "已完成",
}

# Matches `app/services/export.py`'s `_MULTISELECT_SEPARATOR` so a
# `multiselect` value reads the same way across every local -> external
# rendering path in this codebase; §7.2 leaves the connector unspecified.
_MULTISELECT_SEPARATOR = "、"


class WeComMappedPreview(BaseModel):
    """§5.2 step 3: what the preview endpoint needs, computed by a pure function."""

    date_answer: str
    today_work_answer: str
    tomorrow_plan_answer: str
    source_count: int
    today_work_char_count: int
    tomorrow_plan_char_count: int
    unmapped_field_keys: list[str]
    payload_fingerprint: str


def _format_date_answer(work_date: date) -> str:
    """§7.2's only concrete date example is "2026年08月08日" — a fixed,

    zero-padded Chinese-unit rendering. Per the task brief this function
    deliberately does not parse a remote `qdata_format` string; if a real
    target form is ever found to need a different date rendering, that is
    a `WECOM-04`/`WECOM-06` protocol concern, not a reason to guess at
    dynamic format codes here.
    """
    return f"{work_date.year:04d}年{work_date.month:02d}月{work_date.day:02d}日"


def _format_scalar_value(value: DailyFieldValue) -> str | None:
    """Formats one non-`PROJECT_LIST` field value; `None` means "omit entirely".

    Empty inputs (`None`, blank/whitespace-only string, empty list) format
    to `None` so callers never emit a blank line for them. `0`/`0.0` are
    real values (not "empty"), matching `_is_empty()` in
    `app/services/daily_report.py`.
    """
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, list):
        # Only `multiselect`'s `list[str]` reaches here — `PROJECT_LIST`
        # fields are routed to `_format_project_list_block` before this
        # function is ever called for them.
        text_items = [item for item in value if isinstance(item, str)]
        if not text_items:
            return None
        return _MULTISELECT_SEPARATOR.join(text_items)
    return str(value)


def _format_project_list_block(entries: list[ProjectListEntry]) -> str | None:
    """§7.2: one `项目/工作内容/完成状态` block per entry, blank line between entries.

    Uses a half-width `:` — see the module docstring's "Half-width `:`"
    section for why this departs from §7.2's full-width example glyph.
    """
    if not entries:
        return None
    blocks = [
        f"项目:{item.project}\n工作内容:{item.content}\n"
        f"完成状态:{_PROJECT_STATUS_LABELS[item.status]}"
        for item in entries
    ]
    return "\n\n".join(blocks)


def _project_list_items(value: DailyFieldValue) -> list[ProjectListEntry]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, ProjectListEntry)]


def _route_entry(
    entry: DayArchiveSnapshotEntryData, field_mapping: WeComFieldMappingConfig
) -> tuple[list[str], list[str], list[str]]:
    """Routes one archive entry's fields per §7.1's four ordered rules.

    Returns `(today_work_segments, tomorrow_plan_segments, unmapped_field_keys)`
    for this entry alone; the caller combines segments across entries.
    """
    rules_by_key = {rule.field_key: rule for rule in field_mapping.rules}
    today_segments: list[str] = []
    tomorrow_segments: list[str] = []
    unmapped_field_keys: list[str] = []

    fields: list[TemplateFieldData] = sorted(
        entry.template_snapshot, key=lambda field: field.sort_order
    )
    for field in fields:
        if not field.enabled:
            # A disabled field can never carry a value at save/submit time
            # (`validate_daily_content` in `app/services/daily_report.py`
            # rejects any content key that isn't currently enabled), so
            # this is a defensive no-op given the data invariant, not a
            # behavior-changing branch.
            continue

        value = entry.content.get(field.field_key)

        # Rule 1: PROJECT_LIST always wins, even over a coincidental
        # core_type, per the task brief's explicit priority note.
        if field.field_type == "PROJECT_LIST":
            block = _format_project_list_block(_project_list_items(value))
            if block is not None:
                today_segments.append(block)
            continue

        # Rule 2: the core "今日工作内容" field contributes its raw text
        # directly — it *is* the answer body, not a labeled addendum.
        if field.core_type == "today_work":
            formatted = _format_scalar_value(value)
            if formatted is not None:
                today_segments.append(formatted)
            continue

        # Rule 3: same for "明日工作计划". Whether an empty core field
        # should block submission is a `WECOM-06` precheck concern, not
        # this pure mapper's job.
        if field.core_type == "tomorrow_plan":
            formatted = _format_scalar_value(value)
            if formatted is not None:
                tomorrow_segments.append(formatted)
            continue

        # Rule 4: custom field — routed by the saved field_mapping rule,
        # or reported as unmapped when non-empty and unruled.
        rule = rules_by_key.get(field.field_key)
        if rule is None:
            has_value = _format_scalar_value(value) is not None
            if has_value and field_mapping.unmapped_policy == "block":
                unmapped_field_keys.append(field.field_key)
            continue
        if rule.target == "ignore":
            continue
        formatted = _format_scalar_value(value)
        if formatted is None:
            continue
        line = f"{field.label}:{formatted}"
        if rule.target == "today_work":
            today_segments.append(line)
        else:
            tomorrow_segments.append(line)

    return today_segments, tomorrow_segments, unmapped_field_keys


def _compose_answer(entry_segment_lists: list[list[str]]) -> str:
    """Joins each entry's segments, then joins entries across sources.

    A single source never gets a "日报 N" header (§7.2: "只有一个来源时不
    添加冗余序号"); two or more sources each get one, in snapshot order, even
    if a particular source contributed nothing to this answer — the
    numbering stays positionally meaningful ("日报 2" is always the second
    entry in `entries`, never a re-numbered index of non-empty ones).
    """
    entry_texts = ["\n".join(segments) for segments in entry_segment_lists]
    if not entry_texts:
        return ""
    if len(entry_texts) == 1:
        return entry_texts[0]
    numbered = [
        f"日报 {index}\n{text}" if text else f"日报 {index}"
        for index, text in enumerate(entry_texts, start=1)
    ]
    return "\n\n".join(numbered)


def _build_answers(
    entries: list[DayArchiveSnapshotEntryData], field_mapping: WeComFieldMappingConfig
) -> tuple[str, str, list[str]]:
    today_lists: list[list[str]] = []
    tomorrow_lists: list[list[str]] = []
    unmapped_seen: dict[str, None] = {}
    for entry in entries:
        today_segments, tomorrow_segments, unmapped = _route_entry(entry, field_mapping)
        today_lists.append(today_segments)
        tomorrow_lists.append(tomorrow_segments)
        for field_key in unmapped:
            unmapped_seen.setdefault(field_key, None)
    return (
        _compose_answer(today_lists),
        _compose_answer(tomorrow_lists),
        list(unmapped_seen),
    )


def _compute_payload_fingerprint(
    date_answer: str, today_work_answer: str, tomorrow_plan_answer: str
) -> str:
    """SHA-256 of the three mapped answers, normalized to a stable JSON encoding.

    `sort_keys=True` and fixed `separators` make the encoding independent
    of any incidental dict-ordering; the same three strings always produce
    the same digest, and any change to any one of them changes it.
    """
    normalized = json.dumps(
        {
            "date_answer": date_answer,
            "today_work_answer": today_work_answer,
            "tomorrow_plan_answer": tomorrow_plan_answer,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_wecom_preview(
    snapshot: DayArchiveSnapshotData, field_mapping: WeComFieldMappingConfig
) -> WeComMappedPreview:
    """Pure transform: a day's formal archive snapshot -> the WeCom preview payload.

    Each entry is routed using only its own `template_snapshot`/`content`
    pair (`docs/方案设计.md` §7.1: "不依赖数据库中的当前模板版本") — never the
    database's current template, and never another entry's snapshot.
    """
    date_answer = _format_date_answer(snapshot.work_date)
    today_work_answer, tomorrow_plan_answer, unmapped_field_keys = _build_answers(
        snapshot.entries, field_mapping
    )
    payload_fingerprint = _compute_payload_fingerprint(
        date_answer, today_work_answer, tomorrow_plan_answer
    )
    return WeComMappedPreview(
        date_answer=date_answer,
        today_work_answer=today_work_answer,
        tomorrow_plan_answer=tomorrow_plan_answer,
        source_count=len(snapshot.entries),
        today_work_char_count=len(today_work_answer),
        tomorrow_plan_char_count=len(tomorrow_plan_answer),
        unmapped_field_keys=unmapped_field_keys,
        payload_fingerprint=payload_fingerprint,
    )


def compute_schema_fingerprint(
    date_question: WeComQuestionSpec,
    today_question: WeComQuestionSpec,
    tomorrow_question: WeComQuestionSpec,
) -> str:
    """SHA-256 of the three target questions' normalized identity.

    A pure function of its three arguments only — no database access, no
    assumption that the specs came from a `wecom_sync_profiles` row. This
    lets `WECOM-06` call it identically for the locally saved config and
    for structure freshly re-read from the remote form, then compare the
    two digests to detect drift.

    Only `question_id`/`reply_type` participate. `sub_type` (from the
    connect-time-only `ext.qdata_sub_type`) deliberately does not: the
    execute-time structure source (`formcol/detail`, `WECOM-06` revision)
    never carries `ext` and so can never populate it, which would otherwise
    make every execute-time comparison against a connect-time fingerprint
    mismatch permanently rather than just detect real drift.
    """

    def _spec_payload(spec: WeComQuestionSpec) -> dict[str, str]:
        return {
            "question_id": spec.question_id,
            "reply_type": spec.reply_type,
        }

    normalized = json.dumps(
        {
            "date_question": _spec_payload(date_question),
            "today_question": _spec_payload(today_question),
            "tomorrow_question": _spec_payload(tomorrow_question),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
