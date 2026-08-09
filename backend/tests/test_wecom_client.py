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

from app.integrations.wecom.client import (
    _MAX_JOURNAL_ENTRIES,
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


async def test_list_journals_success() -> None:
    fixture = _load_json_fixture("get_journal_list_response.json")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/wework/journal/get_journal_list"
        assert request.url.params.get("sid") == "SYNTHETIC_WEDOC_SID_0000000000"
        return _json_response(200, fixture)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        page = await client.list_journals(_valid_cookie_jar(), "SYNTHETIC-TEMPLATE-1", None)
    finally:
        await client.aclose()

    assert len(page.entries) == 6
    assert page.entries[0].journalid == "SYNTHETIC-JOURNAL-0000000000000001"
    assert page.entries[0].reply_id == "9000000000000011"
    assert page.entries[-1].journalid == "SYNTHETIC-JOURNAL-0000000000000006"


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


async def test_list_journals_business_code_rejected() -> None:
    payload = {"errcode": 100, "errmsg": "denied", "entrys": []}

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, payload)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComBusinessRejected) as excinfo:
            await client.list_journals(_valid_cookie_jar(), "SYNTHETIC-TEMPLATE-1", None)
    finally:
        await client.aclose()
    assert excinfo.value.biz_code == 100


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


async def test_list_journals_missing_entrys_is_protocol_changed() -> None:
    payload = {"errcode": 0, "errmsg": ""}

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, payload)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComProtocolChanged):
            await client.list_journals(_valid_cookie_jar(), "SYNTHETIC-TEMPLATE-1", None)
    finally:
        await client.aclose()


async def test_list_journals_oversized_entrys_is_protocol_changed() -> None:
    huge_entry = {
        "journalid": "x",
        "createtime": 1,
        "reply_id": "1",
        "reply_name": "n",
        "template_id": "t",
        "form_id": "f",
        "submission_type": 1,
    }
    payload = {
        "errcode": 0,
        "errmsg": "",
        "entrys": [huge_entry] * (_MAX_JOURNAL_ENTRIES + 1),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, payload)

    client = WeComInternalClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(WeComProtocolChanged):
            await client.list_journals(_valid_cookie_jar(), "SYNTHETIC-TEMPLATE-1", None)
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
