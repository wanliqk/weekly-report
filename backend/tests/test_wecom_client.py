"""Contract tests for `WeComInternalClient` (`WECOM-04`).

Everything here runs against `httpx.MockTransport` — no real network calls are
ever made. Response/request shapes come from the all-synthetic fixtures under
`tests/fixtures/wecom/` (`WECOM-00`); nothing here reads the `.gitignore`d
real sample under `backend/wx-ribao/`.
"""

from __future__ import annotations

import copy
import json
import logging
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import httpx
import pytest

from app.core.wecom_logging import WECOM_RAW_LOGGER_NAME
from app.integrations.wecom.client import (
    _MAX_FORK_ITEMS,
    WeComAuthExpired,
    WeComBusinessRejected,
    WeComInternalClient,
    WeComOutcomeUncertain,
    WeComProtocolChanged,
    WeComSchemaChanged,
    WeComTransportFailed,
    _assert_allowed_target,
    select_cookie_header,
)
from app.integrations.wecom.schemas import (
    WeComAnswerItem,
    WeComCookieIn,
    WeComSubmitDailyPayload,
)

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "wecom"

_SameSite = Literal["unspecified", "no_restriction", "lax", "strict"]


def _load_json_fixture(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURE_DIR / name).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _load_text_fixture(name: str) -> str:
    return (_FIXTURE_DIR / name).read_text(encoding="utf-8")


def _cookie(
    name: str,
    value: str,
    *,
    domain: str = "doc.weixin.qq.com",
    path: str = "/",
    secure: bool = True,
    http_only: bool = True,
    same_site: _SameSite = "lax",
    expiration_date: float | None = None,
) -> WeComCookieIn:
    return WeComCookieIn(
        name=name,
        value=value,
        domain=domain,
        path=path,
        secure=secure,
        http_only=http_only,
        same_site=same_site,
        expiration_date=expiration_date,
    )


def _valid_cookie_jar(*, sid: str = "SYNTHETIC_WEDOC_SID_0000000000") -> list[WeComCookieIn]:
    return [
        _cookie("wedoc_sid", sid),
        _cookie("TOK", "SYNTHETIC_TOK_00000000000000"),
    ]


def _json_response(
    status_code: int, payload: dict[str, Any], *, content_type: str = "application/json"
) -> httpx.Response:
    body = json.dumps(payload).encode("utf-8")
    return httpx.Response(status_code, content=body, headers={"content-type": content_type})


_BOUNDARY_RE = re.compile(r"boundary=([^\s;]+)")
_NAME_RE = re.compile(r'name="([^"]*)"')


def _parse_multipart_fields(request: httpx.Request) -> list[tuple[str, str]]:
    """Minimal parser for the specific (no real files, no binary parts)
    multipart shape this Client produces — good enough for assertions,
    not a general-purpose multipart parser."""
    content_type = request.headers.get("content-type", "")
    match = _BOUNDARY_RE.search(content_type)
    assert match is not None, "expected a multipart boundary in Content-Type"
    boundary = match.group(1).strip('"').encode("ascii")

    fields: list[tuple[str, str]] = []
    for raw_part in request.content.split(b"--" + boundary):
        part = raw_part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        header_blob, sep, value = part.partition(b"\r\n\r\n")
        if not sep:
            continue
        name_match = _NAME_RE.search(header_blob.decode("utf-8"))
        if name_match is None:
            continue
        fields.append((name_match.group(1), value.decode("utf-8")))
    return fields


def _submit_payload(**overrides: Any) -> WeComSubmitDailyPayload:
    defaults: dict[str, Any] = {
        "form_id": "SYNTHETIC-FORM-1",
        "template_id": "SYNTHETIC-TEMPLATE-1",
        "items": [WeComAnswerItem(question_id="1", text_reply="x")],
    }
    defaults.update(overrides)
    return WeComSubmitDailyPayload(**defaults)


# -- success paths -----------------------------------------------------------


async def test_get_template_info_success() -> None:
    fixture = _load_json_fixture("get_template_combine_info_response.json")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/journal/get_template_combine_info"
        return _json_response(200, fixture)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        result = await client.get_template_info(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()

    assert result.template_id == "SYNTHETIC-TEMPLATE-0000000000000001"
    assert result.form_id == "SYNTHETIC-FORM-0000000000000000000fork"
    assert len(result.entries) == 1
    assert result.entries[0].journalid == "SYNTHETIC-JOURNAL-0000000000000001"
    assert len(result.questions) == 5
    question_ids = [question.question_id for question in result.questions]
    assert question_ids == [
        "1000000001",
        "1000000002",
        "1000000003",
        "1000000004",
        "1000000005",
    ]
    assert result.questions[1].must_reply is True
    assert result.questions[0].reply_type == 11
    assert result.appro == []


async def test_get_template_info_supports_live_form_info_shape() -> None:
    fixture = _load_json_fixture("get_template_combine_info_response.json")
    form = fixture["body"].pop("form")
    fixture["body"].pop("form_id")
    fixture["body"]["form_info"] = form

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, fixture)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        result = await client.get_template_info(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()

    assert result.form_id == "SYNTHETIC-FORM-0000000000000000000fork"
    assert result.template_id == "SYNTHETIC-TEMPLATE-0000000000000001"
    assert len(result.entries) == 1
    assert len(result.questions) == 5


async def test_get_template_info_supports_live_template_entry_shape() -> None:
    fixture = _load_json_fixture("get_template_combine_info_response.json")
    fixture["body"]["entrys"] = [
        {
            "journalid": "SYNTHETIC-LIVE-JOURNAL-1",
            "createtime": 1_800_000_000,
            "createvid": "SYNTHETIC-LIVE-CREATOR-1",
            "doc_info": {"form_id": "SYNTHETIC-LIVE-FORM-1"},
            "content": "SYNTHETIC-IGNORED-CONTENT",
            "template_name": "SYNTHETIC-IGNORED-TEMPLATE-NAME",
            "reportvids": ["SYNTHETIC-APPROVER-1", "SYNTHETIC-APPROVER-2"],
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, fixture)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        result = await client.get_template_info(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()

    entry = result.entries[0]
    assert entry.journalid == "SYNTHETIC-LIVE-JOURNAL-1"
    assert entry.createtime == 1_800_000_000
    assert entry.reply_id == "SYNTHETIC-LIVE-CREATOR-1"
    assert entry.reply_name == ""
    assert entry.form_id == "SYNTHETIC-LIVE-FORM-1"
    assert entry.reportvids == ["SYNTHETIC-APPROVER-1", "SYNTHETIC-APPROVER-2"]


async def test_get_template_info_parses_template_appro_list() -> None:
    """`ai-docs/issues.md` `ISS-054`: `body.template_info.appro[]` is the
    template's own configured approver list — a template-scoped fallback
    recipient source, independent of any specific past submission."""
    fixture = _load_json_fixture("get_template_combine_info_response.json")
    fixture["body"]["template_info"] = {
        "appro": [
            {"vid": 9000000000000091, "name": "SYNTHETIC-APPROVER-A", "tagid": 0},
            {"vid": "9000000000000092", "name": "SYNTHETIC-APPROVER-B"},
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, fixture)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        result = await client.get_template_info(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()

    assert [(a.vid, a.name) for a in result.appro] == [
        ("9000000000000091", "SYNTHETIC-APPROVER-A"),
        ("9000000000000092", "SYNTHETIC-APPROVER-B"),
    ]


async def test_get_template_info_skips_malformed_appro_entries_without_failing() -> None:
    fixture = _load_json_fixture("get_template_combine_info_response.json")
    fixture["body"]["template_info"] = {
        "appro": [
            {"vid": "9000000000000091", "name": "SYNTHETIC-APPROVER-A"},
            {"name": "SYNTHETIC-APPROVER-MISSING-VID"},
            "SYNTHETIC-NOT-EVEN-A-DICT",
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, fixture)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        result = await client.get_template_info(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()

    assert [(a.vid, a.name) for a in result.appro] == [("9000000000000091", "SYNTHETIC-APPROVER-A")]


async def test_get_form_detail_success() -> None:
    fixture = _load_json_fixture("formcol_detail_response.json")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/formcol/detail"
        assert request.url.params.get("form_id") == "SYNTHETIC-FORM-x"
        assert request.url.params.get("f") == "json"
        assert request.url.params.get("lang") == "zh"
        assert "_t" in request.url.params
        # Unlike every other endpoint, this one carries no `sid`/`wedoc_xsrf`.
        assert request.url.params.get("sid") is None
        return _json_response(200, fixture)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        detail = await client.get_form_detail(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()

    assert detail.form_id == "SYNTHETIC-FORM-0000000000000000000base"
    assert detail.creater_vid == "9000000000000011"
    assert detail.creater_name == "王小明"
    assert len(detail.questions) == 3
    question_ids = [question.question_id for question in detail.questions]
    assert question_ids == ["1000000001", "1000000002", "1000000003"]
    assert detail.questions[1].reply_type == 24
    assert len(detail.fork_items) == 1
    assert detail.fork_items[0].form_id == "SYNTHETIC-FORM-0000000000000000000fork"
    assert detail.fork_items[0].status == 1


async def test_submit_daily_success() -> None:
    fixture = _load_json_fixture("answer_page_response.json")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/formcol/answer_page"
        return _json_response(200, fixture)

    payload = _submit_payload(
        form_id="SYNTHETIC-FORM-0000000000000000000base",
        template_id="SYNTHETIC-TEMPLATE-0000000000000001",
        items=[
            WeComAnswerItem(question_id="1000000001", text_reply="2026年01月01日"),
            WeComAnswerItem(
                question_id="1000000002",
                text_reply="1. 完成示例模块的需求评审\n2. 编写示例接口的单元测试",
            ),
            WeComAnswerItem(question_id="1000000003", text_reply="示例明日计划内容"),
        ],
        mngreporter_vids=["9000000000000001"],
    )

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        result = await client.submit_daily(_valid_cookie_jar(), payload)
    finally:
        await client.aclose()

    assert result.answer_id == "1"
    assert result.reply_id == "9000000000000012"
    assert result.journal_uuid == "SYNTHETIC-JOURNAL-UUID-0000000000000000000000000001"
    assert result.user_vid == "9000000000000012"
    assert result.has_repeat_before_replys is False


# -- multipart shape -----------------------------------------------------


async def test_submit_daily_multipart_shape_matches_fixture_field_order() -> None:
    request_fixture_text = _load_text_fixture("answer_page_request.http")
    expected_field_names = re.findall(r'name="([^"]+)"', request_fixture_text)
    fixture_boundary_match = re.search(r"boundary=([^\s;]+)", request_fixture_text)
    assert fixture_boundary_match is not None
    fixture_boundary = fixture_boundary_match.group(1)

    response_fixture = _load_json_fixture("answer_page_response.json")
    captured: dict[str, httpx.Request] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return _json_response(200, response_fixture)

    chinese_text = "1. 完成示例模块的需求评审\n2. 编写示例接口的单元测试"
    payload = _submit_payload(
        form_id="SYNTHETIC-FORM-0000000000000000000base",
        template_id="SYNTHETIC-TEMPLATE-0000000000000001",
        items=[
            WeComAnswerItem(question_id="1000000003", text_reply="示例明日计划内容"),
            WeComAnswerItem(question_id="1000000001", text_reply="2026年01月01日"),
            WeComAnswerItem(question_id="1000000002", text_reply=chinese_text),
        ],
        mngreporter_vids=["9000000000000001", "9000000000000002"],
    )

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        await client.submit_daily(_valid_cookie_jar(), payload)
    finally:
        await client.aclose()

    request = captured["request"]
    content_type = request.headers.get("content-type", "")
    assert content_type.startswith("multipart/form-data; boundary=")
    request_boundary = content_type.split("boundary=", 1)[1]
    # Must be freshly generated per request, never the fixed placeholder
    # recorded in the reference fixture.
    assert request_boundary != fixture_boundary

    fields = _parse_multipart_fields(request)
    field_names = [name for name, _value in fields]
    assert field_names == expected_field_names

    values = dict(fields)
    assert values["form_id"] == "SYNTHETIC-FORM-0000000000000000000base"
    assert values["type"] == "8"
    assert values["use_anonymous"] == "false"
    assert values["submit_again"] == "true"
    assert values["isSendToRoom"] == "false"
    assert values["f"] == "json"
    assert json.loads(values["check_setting"]) == {"can_anonymous": 2}

    form_reply = json.loads(values["form_reply"])
    reply_by_question = {item["question_id"]: item["text_reply"] for item in form_reply["items"]}
    assert reply_by_question["1000000002"] == chinese_text

    wwjournal_data = json.loads(values["wwjournal_data"])
    entry = wwjournal_data["entry"]
    assert entry["mngreporter"] == [{"vid": "9000000000000001"}, {"vid": "9000000000000002"}]
    assert entry["reporter"] == []
    assert entry["templateid"] == "SYNTHETIC-TEMPLATE-0000000000000001"
    assert entry["doc_info"] == {
        "type": 2,
        "form_id": "SYNTHETIC-FORM-0000000000000000000base",
        "template_id": "SYNTHETIC-TEMPLATE-0000000000000001",
    }


async def test_submit_daily_rich_text_item_uses_div_wrapped_html_shape() -> None:
    """Real capture (`docs/方案设计.md` §2.4 revision, `ISS-040`): a WeCom
    "rich text" question (`reply_type=24`) rejects/mangles a bare
    `text_reply` and needs `rich_text_reply: {text_reply, plain_text_reply}`
    instead — `text_reply` HTML-escaped and `<div>`-wrapped, `plain_text_reply`
    the raw original string."""
    response_fixture = _load_json_fixture("answer_page_response.json")
    captured: dict[str, httpx.Request] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return _json_response(200, response_fixture)

    payload = _submit_payload(
        items=[
            WeComAnswerItem(question_id="1000000002", text_reply="完成 A&B <验收>", rich_text=True),
            WeComAnswerItem(question_id="1000000001", text_reply="2026年01月01日", rich_text=False),
        ]
    )

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        await client.submit_daily(_valid_cookie_jar(), payload)
    finally:
        await client.aclose()

    values = dict(_parse_multipart_fields(captured["request"]))
    form_reply = json.loads(values["form_reply"])
    items_by_question = {item["question_id"]: item for item in form_reply["items"]}

    rich_item = items_by_question["1000000002"]
    assert "text_reply" not in rich_item
    assert rich_item["rich_text_reply"]["plain_text_reply"] == "完成 A&B <验收>"
    assert rich_item["rich_text_reply"]["text_reply"] == "<div>完成 A&amp;B &lt;验收&gt;</div>"

    date_item = items_by_question["1000000001"]
    assert "rich_text_reply" not in date_item
    assert date_item["text_reply"] == "2026年01月01日"


async def test_submit_daily_rich_text_item_renders_multiline_text_with_br() -> None:
    response_fixture = _load_json_fixture("answer_page_response.json")
    captured: dict[str, httpx.Request] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return _json_response(200, response_fixture)

    payload = _submit_payload(
        items=[
            WeComAnswerItem(question_id="1000000002", text_reply="第一行\n第二行", rich_text=True)
        ]
    )

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        await client.submit_daily(_valid_cookie_jar(), payload)
    finally:
        await client.aclose()

    values = dict(_parse_multipart_fields(captured["request"]))
    form_reply = json.loads(values["form_reply"])
    rich_item = form_reply["items"][0]
    assert rich_item["rich_text_reply"]["text_reply"] == "<div>第一行<br>第二行</div>"
    assert rich_item["rich_text_reply"]["plain_text_reply"] == "第一行\n第二行"


async def test_submit_daily_boundary_is_randomized_per_request() -> None:
    response_fixture = _load_json_fixture("answer_page_response.json")
    boundaries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        content_type = request.headers.get("content-type", "")
        boundaries.append(content_type.split("boundary=", 1)[1])
        return _json_response(200, response_fixture)

    payload = _submit_payload()
    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        await client.submit_daily(_valid_cookie_jar(), payload)
        await client.submit_daily(_valid_cookie_jar(), payload)
    finally:
        await client.aclose()

    assert len(boundaries) == 2
    assert boundaries[0] != boundaries[1]


# -- cookie URL filtering (pure function) ---------------------------------


def test_select_cookie_header_filters_by_domain() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    jar = [
        _cookie("wedoc_sid", "sid-value", domain="doc.weixin.qq.com"),
        _cookie("other", "other-value", domain="not-doc.weixin.qq.com"),
    ]
    header, sid = select_cookie_header(jar, "https://doc.weixin.qq.com/journal/x", now=now)
    assert "wedoc_sid=sid-value" in header
    assert "other=other-value" not in header
    assert sid == "sid-value"


def test_select_cookie_header_includes_parent_domain_cookie() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    jar = [_cookie("wedoc_sid", "sid-value", domain=".weixin.qq.com")]
    header, sid = select_cookie_header(jar, "https://doc.weixin.qq.com/journal/x", now=now)
    assert sid == "sid-value"
    assert "wedoc_sid=sid-value" in header


def test_select_cookie_header_filters_by_path() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    jar = [
        _cookie("wedoc_sid", "sid-value", path="/journal"),
        _cookie("scoped", "scoped-value", path="/other"),
    ]
    header, sid = select_cookie_header(jar, "https://doc.weixin.qq.com/journal/x", now=now)
    assert sid == "sid-value"
    assert "scoped=scoped-value" not in header


def test_select_cookie_header_excludes_expired_cookie() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    expired_at = (now - timedelta(days=1)).timestamp()
    jar = [_cookie("wedoc_sid", "sid-value", expiration_date=expired_at)]
    header, sid = select_cookie_header(jar, "https://doc.weixin.qq.com/journal/x", now=now)
    assert sid is None
    assert header == ""


def test_select_cookie_header_keeps_not_yet_expired_cookie() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    future = (now + timedelta(days=1)).timestamp()
    jar = [_cookie("wedoc_sid", "sid-value", expiration_date=future)]
    header, sid = select_cookie_header(jar, "https://doc.weixin.qq.com/journal/x", now=now)
    assert sid == "sid-value"


def test_select_cookie_header_excludes_secure_cookie_on_non_https_url() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    jar = [
        _cookie("wedoc_sid", "sid-value", secure=True),
        _cookie("insecure_ok", "value", secure=False),
    ]
    header, sid = select_cookie_header(jar, "http://doc.weixin.qq.com/journal/x", now=now)
    assert sid is None
    assert "insecure_ok=value" in header
    assert "wedoc_sid=sid-value" not in header


async def test_missing_wedoc_sid_raises_auth_expired_without_sending_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("must not send a request when wedoc_sid is missing")

    jar = [_cookie("TOK", "SYNTHETIC_TOK_00000000000000")]
    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComAuthExpired):
            await client.get_template_info(jar, "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()


# -- business failures ---------------------------------------------------


async def test_get_template_info_business_code_rejected() -> None:
    payload = {"head": {"ret": 12345, "msg": "denied"}, "body": {}}

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, payload)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComBusinessRejected) as excinfo:
            await client.get_template_info(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()
    assert excinfo.value.biz_code == 12345
    assert excinfo.value.biz_message == "denied"
    assert excinfo.value.detail is not None
    assert "head.ret" in excinfo.value.detail
    assert "12345" not in excinfo.value.detail


async def test_get_form_detail_business_code_rejected() -> None:
    payload = {"head": {"ret": 100, "msg": "denied"}, "body": {}}

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, payload)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComBusinessRejected) as excinfo:
            await client.get_form_detail(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()
    assert excinfo.value.biz_code == 100
    assert excinfo.value.biz_message == "denied"
    assert excinfo.value.detail is not None
    assert "head.ret" in excinfo.value.detail


async def test_submit_daily_business_code_rejected() -> None:
    payload = {"head": {"ret": 1, "msg": "denied"}, "body": {}}

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, payload)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComBusinessRejected) as excinfo:
            await client.submit_daily(_valid_cookie_jar(), _submit_payload())
    finally:
        await client.aclose()
    assert excinfo.value.biz_code == 1
    assert excinfo.value.biz_message == "denied"
    assert excinfo.value.detail is not None
    assert "head.ret" in excinfo.value.detail


async def test_business_message_is_bounded_length() -> None:
    payload = {"head": {"ret": 7, "msg": "x" * 500}, "body": {}}

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, payload)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComBusinessRejected) as excinfo:
            await client.get_form_detail(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()
    assert excinfo.value.biz_message is not None
    assert len(excinfo.value.biz_message) == 200


# -- post-200 business rejections must still be logged -----------------------
#
# Regression coverage: `_parse_template_info`/`_parse_journal_page`/
# `_parse_submission_result` raise *after* the HTTP layer already saw a plain
# 200, so a rejection they raise has to be captured by the same `_log()` call
# the transport layer uses — otherwise a real sync attempt's business
# rejection (WeComSyncService.execute()'s call path, unlike
# WeComConnectionService.validate_connection()'s own extra wrapping) leaves no
# trace at all in wecom.log.


def _enable_client_logger() -> logging.Logger:
    target_logger = logging.getLogger("app.integrations.wecom.client")
    target_logger.disabled = False
    return target_logger


async def test_get_form_detail_business_rejection_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    payload = {"head": {"ret": 100, "msg": "no permission"}, "body": {}}

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, payload)

    target_logger = _enable_client_logger()
    was_disabled = target_logger.disabled
    try:
        client = WeComInternalClient(transport=httpx.MockTransport(handler))
        try:
            with caplog.at_level(logging.DEBUG, logger="app.integrations.wecom.client"):
                with pytest.raises(WeComBusinessRejected):
                    await client.get_form_detail(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
        finally:
            await client.aclose()
    finally:
        target_logger.disabled = was_disabled

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert "outcome=business_rejected" in record.getMessage()
    diagnostics = record.wecom_diagnostics  # type: ignore[attr-defined]
    assert diagnostics["business_code"] == 100
    assert diagnostics["business_message"] == "no permission"
    assert "head.ret" in diagnostics["schema_paths"]


async def test_submit_daily_business_rejection_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    payload = {"head": {"ret": 1, "msg": "duplicate submission"}, "body": {}}

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, payload)

    target_logger = _enable_client_logger()
    was_disabled = target_logger.disabled
    try:
        client = WeComInternalClient(transport=httpx.MockTransport(handler))
        try:
            with caplog.at_level(logging.DEBUG, logger="app.integrations.wecom.client"):
                with pytest.raises(WeComBusinessRejected):
                    await client.submit_daily(_valid_cookie_jar(), _submit_payload())
        finally:
            await client.aclose()
    finally:
        target_logger.disabled = was_disabled

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert "outcome=business_rejected" in record.getMessage()
    diagnostics = record.wecom_diagnostics  # type: ignore[attr-defined]
    assert diagnostics["business_code"] == 1
    assert diagnostics["business_message"] == "duplicate submission"
    assert "head.ret" in diagnostics["schema_paths"]


async def test_get_form_detail_non_numeric_ret_still_yields_key_diagnostics(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Regression for a real production observation on the now-removed
    `list_journals` endpoint (`ISS-038`): a live response whose business code
    doesn't coerce to a normal integer previously surfaced only as an opaque
    `business_code=-1` with no way to tell *what* the response actually
    looked like. `get_form_detail` shares the same `head.ret`-based parsing
    as every other endpoint, so this same failure mode is covered here too:
    `schema_paths` always accompanies it."""
    payload: dict[str, Any] = {"head": {"ret": None}, "body": {"stat_info": {}}}

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, payload)

    target_logger = _enable_client_logger()
    was_disabled = target_logger.disabled
    try:
        client = WeComInternalClient(transport=httpx.MockTransport(handler))
        try:
            with caplog.at_level(logging.DEBUG, logger="app.integrations.wecom.client"):
                with pytest.raises(WeComBusinessRejected) as excinfo:
                    await client.get_form_detail(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
        finally:
            await client.aclose()
    finally:
        target_logger.disabled = was_disabled

    assert excinfo.value.biz_code == -1
    assert excinfo.value.biz_message is not None
    assert "None" in excinfo.value.biz_message
    assert excinfo.value.detail is not None
    assert "head.ret" in excinfo.value.detail

    diagnostics = caplog.records[0].wecom_diagnostics  # type: ignore[attr-defined]
    assert "head.ret" in diagnostics["schema_paths"]
    assert diagnostics["business_message"] == excinfo.value.biz_message


async def test_get_form_detail_empty_string_ret_is_described_not_silent() -> None:
    """A real production observation on the now-removed `list_journals`
    endpoint (`ISS-038`): its business code came back as an empty string
    with no accompanying message, rather than the documented `0`/non-zero
    int. This asserts the same coercion-failure description applies equally
    to `get_form_detail`'s `head.ret`."""
    payload = {"head": {"ret": ""}, "body": {"stat_info": {}}}

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, payload)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComBusinessRejected) as excinfo:
            await client.get_form_detail(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()

    assert excinfo.value.biz_code == -1
    assert excinfo.value.biz_message is not None
    assert "''" in excinfo.value.biz_message


# -- HTML login-page responses --------------------------------------------


async def test_get_template_info_html_response_is_auth_expired() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"<html><body>please login</body></html>",
            headers={"content-type": "text/html; charset=utf-8"},
        )

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComAuthExpired):
            await client.get_template_info(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()


async def test_submit_daily_html_response_is_auth_expired() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"<html><body>please login</body></html>",
            headers={"content-type": "text/html; charset=utf-8"},
        )

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComAuthExpired):
            await client.submit_daily(_valid_cookie_jar(), _submit_payload())
    finally:
        await client.aclose()


# -- non-JSON / missing required fields -----------------------------------


async def test_get_template_info_missing_body_is_protocol_changed() -> None:
    payload = {"head": {"ret": 0}}

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, payload)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComProtocolChanged):
            await client.get_template_info(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()


async def test_get_form_detail_missing_stat_info_is_protocol_changed() -> None:
    payload = {"head": {"ret": 0}, "body": {}}

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, payload)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComProtocolChanged):
            await client.get_form_detail(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()


async def test_get_form_detail_oversized_fork_items_is_protocol_changed() -> None:
    huge_fork_item = {
        "form_id": "SYNTHETIC-FORM-0000000000000000000fork",
        "title": "日报",
        "ctime": 1,
        "mtime": 1,
        "status": 1,
    }
    payload = {
        "head": {"ret": 0},
        "body": {
            "stat_info": {
                "form_id": "SYNTHETIC-FORM-x",
                "creater_vid": "1",
                "creater_name": "n",
                "question_infos": [],
                "fork_items": [huge_fork_item] * (_MAX_FORK_ITEMS + 1),
            }
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, payload)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComProtocolChanged):
            await client.get_form_detail(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()


async def test_get_template_info_malformed_question_item_is_schema_changed() -> None:
    fixture = _load_json_fixture("get_template_combine_info_response.json")
    broken = copy.deepcopy(fixture)
    del broken["body"]["form"]["question"]["items"][0]["question_id"]

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, broken)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComSchemaChanged):
            await client.get_template_info(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()


async def test_get_template_info_protocol_diagnostic_contains_only_bounded_key_paths() -> None:
    payload = {
        "head": {"ret": 0},
        "body": {
            "combine_info": {
                "template_id": "SECRET-TEMPLATE-VALUE",
                "form": {"question": {"items": [{"title": "SECRET-QUESTION-TITLE"}]}},
            }
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, payload)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComProtocolChanged) as caught:
            await client.get_template_info(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()

    detail = caught.value.detail
    assert detail is not None
    assert "body.combine_info.template_id" in detail
    assert "body.combine_info.form.question.items[]" in detail
    assert "SECRET-TEMPLATE-VALUE" not in detail
    assert "SECRET-QUESTION-TITLE" not in detail


async def test_get_template_info_entry_diagnostic_contains_keys_not_values() -> None:
    fixture = _load_json_fixture("get_template_combine_info_response.json")
    fixture["body"]["entrys"] = [
        {"reply_id": "SECRET-REMOTE-ID", "reply_name": "SECRET-DISPLAY-NAME"}
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, fixture)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComProtocolChanged) as caught:
            await client.get_template_info(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()

    detail = caught.value.detail
    assert detail is not None
    assert "entrys[].reply_id" in detail
    assert "entrys[].reply_name" in detail
    assert "SECRET-REMOTE-ID" not in detail
    assert "SECRET-DISPLAY-NAME" not in detail


async def test_submit_daily_missing_answer_replys_is_outcome_uncertain() -> None:
    payload = {"head": {"ret": 0}, "body": {"user_vid": "1"}}

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, payload)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComOutcomeUncertain):
            await client.submit_daily(_valid_cookie_jar(), _submit_payload())
    finally:
        await client.aclose()


# -- explicit, off-by-default raw request/response body debug switch --------
#
# `Settings.wecom_debug_raw_body` (plumbed to the Client as the constructor
# keyword below) is a deliberate, user-authorized troubleshooting exception
# to the "no body in logs" rule — but the Cookie/header boundary must hold
# regardless of it, since this Client never has a way to pass a header into
# the raw-body logger to begin with.


def _enable_raw_logger() -> logging.Logger:
    target_logger = logging.getLogger(WECOM_RAW_LOGGER_NAME)
    target_logger.disabled = False
    return target_logger


async def test_raw_debug_disabled_by_default_emits_no_raw_records(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fixture = _load_json_fixture("get_template_combine_info_response.json")

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, fixture)

    raw_logger = _enable_raw_logger()
    was_disabled = raw_logger.disabled
    try:
        client = WeComInternalClient(transport=httpx.MockTransport(handler))
        try:
            with caplog.at_level(logging.DEBUG, logger=WECOM_RAW_LOGGER_NAME):
                await client.get_template_info(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
        finally:
            await client.aclose()
    finally:
        raw_logger.disabled = was_disabled

    assert caplog.records == []


async def test_raw_debug_enabled_logs_request_and_response_bodies_without_cookie(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fixture = _load_json_fixture("get_template_combine_info_response.json")

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, fixture)

    secret_cookie_value = "SYNTHETIC_TOK_00000000000000"
    jar = _valid_cookie_jar(sid="SYNTHETIC_WEDOC_SID_RAW_TEST")

    raw_logger = _enable_raw_logger()
    was_disabled = raw_logger.disabled
    try:
        client = WeComInternalClient(transport=httpx.MockTransport(handler), debug_raw_body=True)
        try:
            with caplog.at_level(logging.DEBUG, logger=WECOM_RAW_LOGGER_NAME):
                await client.get_template_info(jar, "SYNTHETIC-FORM-RAW-TEST")
        finally:
            await client.aclose()
    finally:
        raw_logger.disabled = was_disabled

    assert len(caplog.records) == 2
    request_message = caplog.records[0].getMessage()
    response_message = caplog.records[1].getMessage()

    assert "direction=request" in request_message
    assert "SYNTHETIC-FORM-RAW-TEST" in request_message
    assert "direction=response" in response_message
    assert "SYNTHETIC-TEMPLATE-0000000000000001" in response_message

    for message in (request_message, response_message):
        assert secret_cookie_value not in message
        assert "SYNTHETIC_WEDOC_SID_RAW_TEST" not in message
        assert "Cookie" not in message


async def test_raw_debug_covers_submit_daily_multipart_request_too(
    caplog: pytest.LogCaptureFixture,
) -> None:
    response_fixture = _load_json_fixture("answer_page_response.json")

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, response_fixture)

    secret_cookie_value = "SYNTHETIC_TOK_00000000000000"
    jar = _valid_cookie_jar()
    payload = _submit_payload(
        items=[WeComAnswerItem(question_id="1000000002", text_reply="真实日报内容示例")]
    )

    raw_logger = _enable_raw_logger()
    was_disabled = raw_logger.disabled
    try:
        client = WeComInternalClient(transport=httpx.MockTransport(handler), debug_raw_body=True)
        try:
            with caplog.at_level(logging.DEBUG, logger=WECOM_RAW_LOGGER_NAME):
                await client.submit_daily(jar, payload)
        finally:
            await client.aclose()
    finally:
        raw_logger.disabled = was_disabled

    assert len(caplog.records) == 2
    request_message = caplog.records[0].getMessage()
    assert "direction=request" in request_message
    # This is the one call where the raw body genuinely is real report text —
    # confirms the switch does what it says, not that it's silently no-op'd.
    assert "真实日报内容示例" in request_message
    assert secret_cookie_value not in request_message


# -- timeout classification -------------------------------------------------


async def test_connect_timeout_is_transport_failed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("connect timed out")

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComTransportFailed):
            await client.get_template_info(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()


async def test_read_timeout_is_outcome_uncertain() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timed out")

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComOutcomeUncertain):
            await client.submit_daily(_valid_cookie_jar(), _submit_payload())
    finally:
        await client.aclose()


async def test_write_timeout_is_outcome_uncertain() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.WriteTimeout("write timed out")

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComOutcomeUncertain):
            await client.submit_daily(_valid_cookie_jar(), _submit_payload())
    finally:
        await client.aclose()


# -- redirects ---------------------------------------------------------------


async def test_redirect_response_is_auth_expired_and_not_followed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://doc.weixin.qq.com/login"})

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComAuthExpired):
            await client.get_template_info(_valid_cookie_jar(), "SYNTHETIC-FORM-x")
    finally:
        await client.aclose()


# -- host allowlist (SSRF defense) -------------------------------------------


def test_assert_allowed_target_rejects_foreign_host() -> None:
    with pytest.raises(WeComTransportFailed):
        _assert_allowed_target("https://evil.example.com/journal/get_template_combine_info")


def test_assert_allowed_target_rejects_lookalike_host() -> None:
    with pytest.raises(WeComTransportFailed):
        _assert_allowed_target("https://doc.weixin.qq.com.evil.com/journal/x")


def test_assert_allowed_target_rejects_non_https_scheme() -> None:
    with pytest.raises(WeComTransportFailed):
        _assert_allowed_target("http://doc.weixin.qq.com/journal/get_template_combine_info")


def test_assert_allowed_target_accepts_real_host() -> None:
    _assert_allowed_target("https://doc.weixin.qq.com/journal/get_template_combine_info")


# -- logging hygiene ----------------------------------------------------------


async def test_debug_log_never_contains_cookie_or_body(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fixture = _load_json_fixture("get_template_combine_info_response.json")

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, fixture)

    secret_cookie_value = "SYNTHETIC_TOK_00000000000000"
    jar = _valid_cookie_jar()
    assert any(cookie.value == secret_cookie_value for cookie in jar)

    # Some other test module in the full suite runs Alembic migrations
    # (`run_startup_migrations`), whose `env.py` calls
    # `logging.config.fileConfig(...)` with the library default
    # `disable_existing_loggers=True`. That permanently flips `.disabled`
    # on every logger object that already existed at that point — including
    # this module's, if `test_wecom_client.py` was already collected —
    # regardless of test order or file. `caplog.at_level()` only guards
    # against the separate `logging.disable()` global-suppression
    # mechanism, not this per-logger flag, so it has to be restored here.
    target_logger = logging.getLogger("app.integrations.wecom.client")
    was_disabled = target_logger.disabled
    target_logger.disabled = False
    try:
        client = WeComInternalClient(transport=httpx.MockTransport(handler))
        try:
            with caplog.at_level(logging.DEBUG, logger="app.integrations.wecom.client"):
                await client.get_template_info(jar, "SYNTHETIC-FORM-x")
        finally:
            await client.aclose()
    finally:
        target_logger.disabled = was_disabled

    assert caplog.records, "expected at least one debug log line"
    for record in caplog.records:
        message = record.getMessage()
        assert secret_cookie_value not in message
        assert "Cookie" not in message
        assert "form_id" not in message
    assert any(
        getattr(record, "wecom_diagnostics", {}).get("http_status") == 200
        for record in caplog.records
    )
