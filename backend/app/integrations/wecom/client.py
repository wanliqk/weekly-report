"""`WeComInternalClient`: async HTTP client for WeCom's unofficial internal
journal endpoints (`docs/方案设计.md` §2.4/§8).

Scope boundary (`WECOM-04`): this module is a pure protocol client. It does
not know about local users, templates, `daily_report_days`, or the sync
state machine — it only knows how to turn a Cookie jar + a small set of
already-resolved values into one of the verified requests, and how to
turn the raw HTTP response back into a typed DTO or a classified exception.
Field mapping (which local field becomes which `question_id`) is `WECOM-05`;
orchestration/idempotency/retry policy is `WECOM-06`.

Security posture (`docs/方案设计.md` §12, `SEC-013`/`SEC-014`):
- The base URL is hardcoded to `https://doc.weixin.qq.com` and is not a
  constructor parameter; every request is re-validated against it
  immediately before being sent, so no caller-supplied value can ever change
  the target host (SSRF defense in depth).
- Redirects are never followed (`follow_redirects=False`); a 3xx response is
  treated as an auth-expired signal, not something to chase.
- Nothing about the request (Cookie header value, JSON/multipart body) is
  ever logged. The only optional debug log line carries method, host, a
  path template, an outcome category, and a duration.
"""

from __future__ import annotations

import html
import json
import logging
import re
import time
from collections import deque
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any, Final, TypeVar
from urllib.parse import urlsplit

import httpx
from pydantic import ValidationError

from app.core.clock import Clock, utc_now
from app.core.wecom_logging import WECOM_RAW_LOGGER_NAME, log_wecom_event, log_wecom_raw_body
from app.integrations.wecom.schemas import (
    WeComAnswerItem,
    WeComCookieIn,
    WeComFormDetail,
    WeComFormDetailForkItem,
    WeComQuestionItem,
    WeComSubmissionResult,
    WeComSubmitDailyPayload,
    WeComTemplateApprover,
    WeComTemplateEntry,
    WeComTemplateInfo,
)

logger = logging.getLogger(__name__)
_raw_logger = logging.getLogger(WECOM_RAW_LOGGER_NAME)

_ALLOWED_HOST: Final = "doc.weixin.qq.com"
_BASE_URL: Final = f"https://{_ALLOWED_HOST}"

_GET_TEMPLATE_INFO_PATH: Final = "/journal/get_template_combine_info"
_GET_FORM_DETAIL_PATH: Final = "/formcol/detail"
_SUBMIT_DAILY_PATH: Final = "/formcol/answer_page"

_SID_COOKIE_NAME: Final = "wedoc_sid"

# Defense against an unbounded/pathological response body — these are small
# JSON APIs; anything past these thresholds is treated as a protocol anomaly
# rather than parsed (docs/方案设计.md §8 point 3: "JSON 深度/大小合理性").
_MAX_RESPONSE_BYTES: Final = 5_000_000
_MAX_JSON_DEPTH: Final = 32
_MAX_SCHEMA_DIAGNOSTIC_DEPTH: Final = 6
_MAX_SCHEMA_DIAGNOSTIC_PATHS: Final = 64
_SCHEMA_KEY_PATTERN: Final = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")

# A single `fork_items` response claiming an implausible number of past
# submissions is treated as a protocol anomaly rather than trusted, same
# reasoning as `docs/方案设计.md` §10.2's now-superseded list-pagination cap.
_MAX_FORK_ITEMS: Final = 200

_DEFAULT_TIMEOUT: Final = httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0)

# WeCom's own business-rejection message text (`head.msg`/`errmsg`) is
# protocol metadata (an error *reason*, not report content or a credential),
# so it is safe to surface in the unredacted diagnostic log alongside
# `business_code` — bounded defensively since it's remote-supplied text.
_MAX_BUSINESS_MESSAGE_LENGTH: Final = 200

T = TypeVar("T")


class WeComClientError(Exception):
    """Base class for every classified failure this Client raises.

    `detail`, like `message`, must only ever carry safe-to-log
    classification context (an HTTP status, a business code, a field name) —
    never a Cookie, a request/response body, or a query string.
    """

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class WeComAuthExpired(WeComClientError):
    """Cookie invalid/expired, `wedoc_sid` missing, a 3xx redirect, or an
    HTML (login-page-shaped) response where JSON was expected."""


class WeComSchemaChanged(WeComClientError):
    """The remote form's question structure looks structurally broken (e.g.
    a `question` item is missing an identifying field).

    This only reports "something about the question structure looks off" at
    the raw-shape level; comparing the result against an *expected*
    structure/schema fingerprint is the caller's job (`WECOM-05`/`WECOM-06`)
    — this Client does not hold or maintain that expected-structure state.
    """


class WeComBusinessRejected(WeComClientError):
    """A definite non-zero business code (`head.ret` / `errcode`) — the
    remote explicitly processed the request and declined it."""

    def __init__(
        self,
        message: str,
        *,
        biz_code: int,
        biz_message: str | None = None,
        detail: str | None = None,
    ) -> None:
        super().__init__(message, detail=detail)
        self.biz_code = biz_code
        self.biz_message = biz_message


class WeComProtocolChanged(WeComClientError):
    """HTTP 200 with a body, but the shape doesn't match the documented
    contract (missing top-level node, oversized/too-deep JSON, an
    implausibly large list, non-JSON content type on what should be a safe
    read). Only raised for read-only calls, where nothing was submitted."""


class WeComTransportFailed(WeComClientError):
    """DNS/TLS/connect failure, or the target host failed Client-side
    allowlist validation — the request body was never sent."""


class WeComOutcomeUncertain(WeComClientError):
    """A write/read timed out, or `submit_daily`'s response came back
    malformed after HTTP 200 — the remote may or may not have accepted the
    write. Callers must reconcile remotely before ever retrying
    (`SEC-015`/`docs/方案设计.md` §10.3)."""


def _outcome_for_error(exc: WeComClientError) -> str:
    if isinstance(exc, WeComAuthExpired):
        return "auth_expired"
    if isinstance(exc, WeComSchemaChanged):
        return "schema_changed"
    if isinstance(exc, WeComBusinessRejected):
        return "business_rejected"
    if isinstance(exc, WeComProtocolChanged):
        return "protocol_changed"
    if isinstance(exc, WeComTransportFailed):
        return "transport_failed"
    return "outcome_uncertain"


def _coerce_biz_code(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return -1


def _coerce_biz_message(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value[:_MAX_BUSINESS_MESSAGE_LENGTH]


def _describe_unparseable_code(value: object) -> str:
    """Best-effort, still-safe description of a `head.ret`/`errcode` value
    that didn't coerce to an int. This is the same trust class as
    `business_code` itself (a status/classification field, not report
    content) — a dict/list shape is defensively described by type name only,
    never rendered, since a code field should never structurally be one."""
    if isinstance(value, dict | list):
        return f"<{type(value).__name__}>"
    return repr(value)[:64]


def _rich_text_html(text: str) -> str:
    """Best-effort reconstruction of WeCom's own rich-text-editor wire
    format for a plain string. Only the single-line case has been observed
    in a real capture (`<div>...</div>`, HTML-escaped); a multi-line answer
    is rendered here as one `<div>` with `<br>` line breaks, matching a
    common rich-text-editor convention — this specific multi-line rendering
    is unverified against a real WeCom submission and worth re-checking if
    a multi-line answer ever renders unexpectedly on the WeCom side.
    """
    escaped = html.escape(text, quote=False)
    return f"<div>{escaped.replace(chr(10), '<br>')}</div>"


def _serialize_answer_item(item: WeComAnswerItem) -> dict[str, Any]:
    if item.rich_text:
        return {
            "question_id": item.question_id,
            "rich_text_reply": {
                "text_reply": _rich_text_html(item.text_reply),
                "plain_text_reply": item.text_reply,
            },
        }
    return {"question_id": item.question_id, "text_reply": item.text_reply}


def _business_message_for_unparseable_code(
    *, coerced_code: int, explicit_message: str | None, raw_code: object
) -> str | None:
    if explicit_message is not None:
        return explicit_message
    if coerced_code != -1:
        return None
    return f"错误码无法解析为整数,原始类型/值:{_describe_unparseable_code(raw_code)}"


def _assert_allowed_target(url: str) -> None:
    """Reject anything that isn't `https://doc.weixin.qq.com/...`.

    Called immediately before every request is sent, even though the base
    URL is a hardcoded module constant — this is deliberate defense in depth
    (`docs/方案设计.md` §12: "HTTP Client 只允许固定 HTTPS 主机...防止 SSRF") and is
    also what the "host lock" test exercises directly.
    """
    parsed = urlsplit(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != _ALLOWED_HOST:
        raise WeComTransportFailed("目标主机不受信任,已拒绝发起请求")


def _cookie_domain_matches(cookie_domain: str, host: str) -> bool:
    domain = cookie_domain.strip().lower().lstrip(".")
    host = host.lower()
    return host == domain or host.endswith(f".{domain}")


def _cookie_path_matches(cookie_path: str, request_path: str) -> bool:
    """RFC 6265 §5.1.4 path-match: exact match, or `cookie_path` is a proper
    ancestor segment of `request_path`."""
    path = cookie_path or "/"
    if not path.startswith("/"):
        path = f"/{path}"
    if request_path == path:
        return True
    if request_path.startswith(path):
        return path.endswith("/") or request_path[len(path)] == "/"
    return False


def select_cookie_header(
    cookie_jar: Sequence[WeComCookieIn], url: str, *, now: datetime
) -> tuple[str, str | None]:
    """Filter `cookie_jar` down to what applies to `url` and build a
    `Cookie:` header value plus the extracted `wedoc_sid` (or `None`).

    A cookie is kept only if its domain matches (or is a parent domain of)
    the target host, its path is a match/ancestor of the target path, it
    isn't `secure`-only on a non-https URL, and it isn't already expired.
    Does not raise — callers decide what a missing `wedoc_sid` means.
    """
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    path = parsed.path or "/"
    is_https = parsed.scheme == "https"

    pairs: list[tuple[str, str]] = []
    wedoc_sid: str | None = None
    for cookie in cookie_jar:
        if not _cookie_domain_matches(cookie.domain, host):
            continue
        if not _cookie_path_matches(cookie.path, path):
            continue
        if cookie.secure and not is_https:
            continue
        if cookie.expiration_date is not None:
            expires_at = datetime.fromtimestamp(cookie.expiration_date, tz=UTC)
            if expires_at <= now:
                continue
        pairs.append((cookie.name, cookie.value))
        if cookie.name == _SID_COOKIE_NAME:
            wedoc_sid = cookie.value

    cookie_header = "; ".join(f"{name}={value}" for name, value in pairs)
    return cookie_header, wedoc_sid


def _json_depth(value: Any, *, current: int = 0) -> int:
    if current > _MAX_JSON_DEPTH:
        return current
    if isinstance(value, dict):
        if not value:
            return current + 1
        return max(_json_depth(v, current=current + 1) for v in value.values())
    if isinstance(value, list):
        if not value:
            return current + 1
        return max(_json_depth(v, current=current + 1) for v in value)
    return current


def _schema_paths(value: Any) -> str:
    """Return a bounded breadth-first list of JSON key paths, never values.

    This is diagnostic-only metadata for an explicitly unredacted ``wecom.log``.
    Remote keys must look like protocol identifiers; arbitrary/user-controlled
    strings are skipped. Lists inspect only their first item because every value
    is deliberately forbidden from this diagnostic surface.
    """

    paths: list[str] = []
    queue: deque[tuple[Any, str, int]] = deque([(value, "", 0)])
    while queue and len(paths) < _MAX_SCHEMA_DIAGNOSTIC_PATHS:
        current, prefix, depth = queue.popleft()
        if depth >= _MAX_SCHEMA_DIAGNOSTIC_DEPTH:
            continue
        if isinstance(current, dict):
            for key in sorted(current):
                if len(paths) >= _MAX_SCHEMA_DIAGNOSTIC_PATHS:
                    break
                if not isinstance(key, str) or _SCHEMA_KEY_PATTERN.fullmatch(key) is None:
                    continue
                path = f"{prefix}.{key}" if prefix else key
                paths.append(path)
                child = current[key]
                if isinstance(child, dict | list):
                    queue.append((child, path, depth + 1))
        elif isinstance(current, list) and current:
            list_path = f"{prefix}[]"
            paths.append(list_path)
            first = current[0]
            if isinstance(first, dict | list):
                queue.append((first, list_path, depth + 1))
    return ",".join(paths)


def _normalize_template_entry(entry: Any) -> Any:
    """Normalize the two observed read-only template-entry shapes.

    The current live response uses ``createvid`` and ``doc_info.form_id``;
    the legacy synthetic contract used ``reply_id`` and a top-level
    ``form_id``. The live shape no longer carries a display name, so keep it
    empty instead of guessing from unrelated template/content fields.
    """

    if not isinstance(entry, dict):
        return entry
    normalized = dict(entry)
    if "reply_id" not in normalized:
        normalized["reply_id"] = entry.get("createvid")
    if "reply_name" not in normalized:
        normalized["reply_name"] = ""
    if "form_id" not in normalized:
        doc_info = entry.get("doc_info")
        if isinstance(doc_info, dict):
            normalized["form_id"] = doc_info.get("form_id")
    return normalized


def _parse_approvers(body: dict[str, Any]) -> list[WeComTemplateApprover]:
    """`body.template_info.appro[]` — the template's own configured approver
    list (`ai-docs/issues.md` `ISS-054`), used as a template-scoped fallback
    recipient source when no submission history exists yet for
    `entrys[0].reportvids` to be read from. Best-effort like `fork_items`
    (`_parse_form_detail`): a missing/malformed node yields an empty list
    (never blocks connecting) rather than raising — this is a fallback data
    source, not a required protocol field."""
    template_info = body.get("template_info")
    appro = template_info.get("appro") if isinstance(template_info, dict) else None
    if not isinstance(appro, list):
        return []
    approvers: list[WeComTemplateApprover] = []
    for item in appro:
        if not isinstance(item, dict):
            continue
        try:
            approvers.append(WeComTemplateApprover.model_validate(item))
        except ValidationError:
            continue
    return approvers


def _parse_json_response(response: httpx.Response, *, on_send: bool) -> dict[str, Any]:
    """Validate status/content-type/size/depth and return the parsed JSON
    object. `on_send=True` (the submit endpoint, where the body has
    definitely left the process) turns shape failures into
    `WeComOutcomeUncertain` instead of `WeComProtocolChanged`, matching
    `docs/方案设计.md` §11's "HTTP 200 但 JSON/节点变化...若已发送提交则 uncertain,只读
    接口则 schema_changed/协议错误" rule.
    """
    if 300 <= response.status_code < 400:
        raise WeComAuthExpired("登录状态已失效(收到重定向响应)")
    if response.status_code in (401, 403):
        raise WeComAuthExpired("登录状态已失效")
    if response.status_code != 200:
        message = f"远端返回非预期状态码 {response.status_code}"
        raise WeComOutcomeUncertain(message) if on_send else WeComProtocolChanged(message)

    content_type = response.headers.get("content-type", "")
    if "json" not in content_type.lower():
        raise WeComAuthExpired("登录状态已失效(收到非 JSON 响应,疑似登录页拦截)")

    if len(response.content) > _MAX_RESPONSE_BYTES:
        message = "响应体超出合理大小,判定为协议异常"
        raise WeComOutcomeUncertain(message) if on_send else WeComProtocolChanged(message)

    try:
        payload = response.json()
    except ValueError as exc:
        message = "响应不是合法 JSON"
        if on_send:
            raise WeComOutcomeUncertain(message) from exc
        raise WeComProtocolChanged(message) from exc

    if not isinstance(payload, dict):
        message = "响应 JSON 顶层结构不是对象"
        if on_send:
            raise WeComOutcomeUncertain(message)
        raise WeComProtocolChanged(message)

    if _json_depth(payload) > _MAX_JSON_DEPTH:
        message = "响应 JSON 嵌套深度超出合理范围,判定为协议异常"
        if on_send:
            raise WeComOutcomeUncertain(message)
        raise WeComProtocolChanged(message)

    return payload


class WeComInternalClient:
    """Async HTTP client for the four verified WeCom internal endpoints.

    Exposes `get_template_info` (connect-time only), `get_form_detail`
    (execute-time structure re-check + duplicate check), and `submit_daily`
    (`docs/方案设计.md` §8, revised — the previous `list_journals` duplicate
    check has been retired in favor of `get_form_detail`'s own `fork_items`).
    Not thread-safe across event loops, same as any `httpx.AsyncClient`;
    construct one per request scope.
    """

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Clock = utc_now,
        debug_raw_body: bool = False,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=_DEFAULT_TIMEOUT,
            follow_redirects=False,
            transport=transport,
        )
        self._clock = clock
        # `Settings.wecom_debug_raw_body` — an explicit, user-authorized,
        # off-by-default troubleshooting exception. This Client stays a
        # "pure protocol client" (no `Settings` import) per its own module
        # docstring; callers (`WeComSyncService`/`WeComConnectionService`'s
        # `_new_client()`) resolve the flag and pass it in.
        self._debug_raw_body = debug_raw_body

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> WeComInternalClient:
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.aclose()

    # -- public protocol methods -------------------------------------------------

    async def get_template_info(
        self, cookie_jar: Sequence[WeComCookieIn], form_id: str
    ) -> WeComTemplateInfo:
        cookie_header, _sid = self._select_or_raise(cookie_jar, _GET_TEMPLATE_INFO_PATH)
        return await self._send_json(
            _GET_TEMPLATE_INFO_PATH,
            params={"_prefetch": "1"},
            json_body={
                "form_id": form_id,
                "fetch_journal_list": True,
                "is_pre_create": False,
                "is_answer_from_share": False,
                "is_answer_from_workplace": False,
                "fetch_submission_type": 1,
                "is_only_view": True,
            },
            cookie_header=cookie_header,
            on_send=False,
            parse=self._parse_template_info,
        )

    async def get_form_detail(
        self, cookie_jar: Sequence[WeComCookieIn], form_id: str
    ) -> WeComFormDetail:
        """`GET /formcol/detail` — the execute-time structure/duplicate-check
        source. Replaces the previous `get_template_info()` re-check plus the
        separate `list_journals()` duplicate-check call (both retired: see
        `docs/方案设计.md` §2.4/§10.2's revision history). Unlike every other
        method here, WeCom's own real traffic for this endpoint carries no
        `sid`/`wedoc_xsrf` query parameter — only Cookie auth."""
        cookie_header, _sid = self._select_or_raise(cookie_jar, _GET_FORM_DETAIL_PATH)
        return await self._send_get(
            _GET_FORM_DETAIL_PATH,
            params={
                "_t": str(int(self._clock().timestamp() * 1000)),
                "f": "json",
                "lang": "zh",
                "form_id": form_id,
            },
            cookie_header=cookie_header,
            parse=self._parse_form_detail,
        )

    async def submit_daily(
        self,
        cookie_jar: Sequence[WeComCookieIn],
        payload: WeComSubmitDailyPayload,
    ) -> WeComSubmissionResult:
        cookie_header, sid = self._select_or_raise(cookie_jar, _SUBMIT_DAILY_PATH)

        form_reply = json.dumps(
            {"items": [_serialize_answer_item(item) for item in payload.items]},
            ensure_ascii=False,
        )
        check_setting = json.dumps({"can_anonymous": 2}, ensure_ascii=False)
        wwjournal_data = json.dumps(
            {
                "entry": {
                    "mngreporter": [{"vid": vid} for vid in payload.mngreporter_vids],
                    "reporter": [{"vid": vid} for vid in payload.reporter_vids],
                    "templateid": payload.template_id,
                    "doc_info": {
                        "type": 2,
                        "form_id": payload.form_id,
                        "template_id": payload.template_id,
                    },
                }
            },
            ensure_ascii=False,
        )
        # Field order mirrors `tests/fixtures/wecom/answer_page_request.http`.
        fields: list[tuple[str, str]] = [
            ("form_id", payload.form_id),
            ("form_reply", form_reply),
            ("type", "8"),
            ("check_setting", check_setting),
            ("use_anonymous", "false"),
            ("submit_again", "true" if payload.submit_again else "false"),
            ("wwjournal_data", wwjournal_data),
            ("isSendToRoom", "false"),
            ("f", "json"),
        ]

        return await self._send_multipart(
            _SUBMIT_DAILY_PATH,
            params={"sid": sid, "wedoc_xsrf": "1"},
            fields=fields,
            cookie_header=cookie_header,
            parse=self._parse_submission_result,
        )

    # -- request plumbing ---------------------------------------------------------

    def _select_or_raise(self, cookie_jar: Sequence[WeComCookieIn], path: str) -> tuple[str, str]:
        url = f"{_BASE_URL}{path}"
        _assert_allowed_target(url)
        cookie_header, wedoc_sid = select_cookie_header(cookie_jar, url, now=self._clock())
        if not wedoc_sid:
            raise WeComAuthExpired("企业微信登录状态缺失(未找到 wedoc_sid),已拒绝发起请求")
        return cookie_header, wedoc_sid

    async def _send_json(
        self,
        path: str,
        *,
        params: dict[str, str],
        json_body: dict[str, Any],
        cookie_header: str,
        on_send: bool,
        parse: Callable[[dict[str, Any]], T],
    ) -> T:
        self._dump_raw_request(path, json.dumps(json_body, ensure_ascii=False))
        started = time.monotonic()
        try:
            response = await self._client.post(
                path, params=params, json=json_body, headers={"Cookie": cookie_header}
            )
        except (httpx.ConnectTimeout, httpx.ConnectError, httpx.PoolTimeout) as exc:
            transport_error = WeComTransportFailed("无法连接企业微信服务")
            self._log(path, started, error=transport_error)
            raise transport_error from exc
        except (httpx.WriteTimeout, httpx.ReadTimeout) as exc:
            uncertain_error = WeComOutcomeUncertain("请求超时,结果不确定")
            self._log(path, started, error=uncertain_error)
            raise uncertain_error from exc
        except httpx.HTTPError as exc:
            http_error = WeComTransportFailed("网络请求失败")
            self._log(path, started, error=http_error)
            raise http_error from exc
        self._dump_raw_response(path, response)

        # The parse step (`parse`, e.g. `_parse_template_info`) is folded into
        # this same try/except so a business/schema/protocol rejection found
        # *inside* an HTTP-200 JSON body is logged exactly like a transport
        # failure — logging only the HTTP-layer outcome here previously left
        # every post-200 business rejection silently unlogged.
        try:
            payload = _parse_json_response(response, on_send=on_send)
            result = parse(payload)
        except WeComClientError as exc:
            self._log(path, started, http_status=response.status_code, error=exc)
            raise
        self._log(path, started, http_status=response.status_code)
        return result

    async def _send_get(
        self,
        path: str,
        *,
        params: dict[str, str],
        cookie_header: str,
        parse: Callable[[dict[str, Any]], T],
    ) -> T:
        self._dump_raw_request(path, json.dumps(params, ensure_ascii=False))
        started = time.monotonic()
        try:
            response = await self._client.get(
                path, params=params, headers={"Cookie": cookie_header}
            )
        except (httpx.ConnectTimeout, httpx.ConnectError, httpx.PoolTimeout) as exc:
            transport_error = WeComTransportFailed("无法连接企业微信服务")
            self._log(path, started, error=transport_error)
            raise transport_error from exc
        except (httpx.WriteTimeout, httpx.ReadTimeout) as exc:
            uncertain_error = WeComOutcomeUncertain("请求超时,结果不确定")
            self._log(path, started, error=uncertain_error)
            raise uncertain_error from exc
        except httpx.HTTPError as exc:
            http_error = WeComTransportFailed("网络请求失败")
            self._log(path, started, error=http_error)
            raise http_error from exc
        self._dump_raw_response(path, response)

        try:
            payload = _parse_json_response(response, on_send=False)
            result = parse(payload)
        except WeComClientError as exc:
            self._log(path, started, http_status=response.status_code, error=exc)
            raise
        self._log(path, started, http_status=response.status_code)
        return result

    async def _send_multipart(
        self,
        path: str,
        *,
        params: dict[str, str],
        fields: list[tuple[str, str]],
        cookie_header: str,
        parse: Callable[[dict[str, Any]], T],
    ) -> T:
        # `files=[(name, (None, value)), ...]` forces httpx's own
        # `MultipartStream` encoding (random per-request boundary, never a
        # fixed/hardcoded string) while rendering byte-identical to a plain
        # data field, since a `None` filename suppresses the
        # `filename=`/`Content-Type:` parts a real file upload would add.
        files: list[tuple[str, tuple[None, str]]] = [
            (name, (None, value)) for name, value in fields
        ]
        self._dump_raw_request(path, json.dumps(dict(fields), ensure_ascii=False))
        started = time.monotonic()
        try:
            response = await self._client.post(
                path, params=params, files=files, headers={"Cookie": cookie_header}
            )
        except (httpx.ConnectTimeout, httpx.ConnectError, httpx.PoolTimeout) as exc:
            transport_error = WeComTransportFailed("无法连接企业微信服务")
            self._log(path, started, error=transport_error)
            raise transport_error from exc
        except (httpx.WriteTimeout, httpx.ReadTimeout) as exc:
            uncertain_error = WeComOutcomeUncertain("请求超时,结果不确定")
            self._log(path, started, error=uncertain_error)
            raise uncertain_error from exc
        except httpx.HTTPError as exc:
            http_error = WeComTransportFailed("网络请求失败")
            self._log(path, started, error=http_error)
            raise http_error from exc
        self._dump_raw_response(path, response)

        # See `_send_json`'s matching comment: folding `parse` in here makes
        # `submit_daily`'s post-200 business rejection (`WeComBusinessRejected`
        # from `_parse_submission_result`) logged the same way a transport
        # failure is, instead of escaping unlogged.
        try:
            payload = _parse_json_response(response, on_send=True)
            result = parse(payload)
        except WeComClientError as exc:
            self._log(path, started, http_status=response.status_code, error=exc)
            raise
        self._log(path, started, http_status=response.status_code)
        return result

    def _dump_raw_request(self, path: str, body: str) -> None:
        # `body` here is a JSON/form-field serialization built by this
        # Client's own callers — it never includes `cookie_header` or any
        # other header, regardless of `self._debug_raw_body`.
        if self._debug_raw_body:
            log_wecom_raw_body(_raw_logger, direction="request", path_template=path, body=body)

    def _dump_raw_response(self, path: str, response: httpx.Response) -> None:
        if self._debug_raw_body:
            log_wecom_raw_body(
                _raw_logger, direction="response", path_template=path, body=response.text
            )

    def _log(
        self,
        path: str,
        started: float,
        *,
        http_status: int | None = None,
        error: WeComClientError | None = None,
    ) -> None:
        diagnostics: dict[str, str | int | bool | None] = {}
        if http_status is not None:
            diagnostics["http_status"] = http_status
        if error is not None:
            diagnostics["error_type"] = type(error).__name__
            diagnostics["error_message"] = error.message
            if error.detail is not None:
                diagnostics["schema_paths"] = error.detail
            if isinstance(error, WeComBusinessRejected):
                diagnostics["business_code"] = error.biz_code
                if error.biz_message is not None:
                    diagnostics["business_message"] = error.biz_message
        log_wecom_event(
            logger,
            event="request",
            path_template=path,
            outcome=_outcome_for_error(error) if error is not None else "ok",
            duration_ms=int((time.monotonic() - started) * 1000),
            diagnostics=diagnostics,
        )

    # -- response parsing -----------------------------------------------------

    def _parse_template_info(self, payload: dict[str, Any]) -> WeComTemplateInfo:
        head = payload.get("head")
        if not isinstance(head, dict) or "ret" not in head:
            raise WeComProtocolChanged("响应缺少 head.ret 节点")
        ret = head["ret"]
        if ret != 0:
            coerced_code = _coerce_biz_code(ret)
            raise WeComBusinessRejected(
                "获取模板信息被拒绝",
                biz_code=coerced_code,
                biz_message=_business_message_for_unparseable_code(
                    coerced_code=coerced_code,
                    explicit_message=_coerce_biz_message(head.get("msg")),
                    raw_code=ret,
                ),
                detail=_schema_paths(payload),
            )

        body = payload.get("body")
        if not isinstance(body, dict):
            raise WeComProtocolChanged("响应缺少 body 节点")

        template_id = body.get("template_id")
        entrys = body.get("entrys")
        form = body.get("form")
        if not isinstance(form, dict):
            # The live 2026-08 WeCom response moved the same form object from
            # `body.form` to `body.form_info`. Keep the synthetic legacy shape
            # supported because both shapes are read-only and unambiguous.
            form = body.get("form_info")
        form_id = body.get("form_id")
        if not isinstance(form_id, str | int) and isinstance(form, dict):
            form_id = form.get("form_id")
        if (
            not isinstance(template_id, str | int)
            or not isinstance(form_id, str | int)
            or not isinstance(entrys, list)
            or not isinstance(form, dict)
        ):
            raise WeComProtocolChanged(
                "响应 body 缺少 template_id/form_id/entrys/form/form_info 节点",
                detail=_schema_paths(payload),
            )

        try:
            entries = [
                WeComTemplateEntry.model_validate(_normalize_template_entry(entry))
                for entry in entrys
            ]
        except ValidationError as exc:
            raise WeComProtocolChanged(
                "body.entrys 元素结构与预期不符",
                detail=_schema_paths({"entrys": entrys}),
            ) from exc

        question = form.get("question")
        items = question.get("items") if isinstance(question, dict) else None
        if not isinstance(items, list):
            raise WeComSchemaChanged("表单题目结构(body.form.question.items)缺失")
        try:
            questions = [WeComQuestionItem.model_validate(item) for item in items]
        except ValidationError as exc:
            raise WeComSchemaChanged("表单题目结构与预期不符") from exc

        return WeComTemplateInfo(
            template_id=str(template_id),
            form_id=str(form_id),
            entries=entries,
            questions=questions,
            appro=_parse_approvers(body),
        )

    def _parse_form_detail(self, payload: dict[str, Any]) -> WeComFormDetail:
        head = payload.get("head")
        if not isinstance(head, dict) or "ret" not in head:
            raise WeComProtocolChanged("响应缺少 head.ret 节点")
        ret = head["ret"]
        if ret != 0:
            coerced_code = _coerce_biz_code(ret)
            raise WeComBusinessRejected(
                "获取表单结构被拒绝",
                biz_code=coerced_code,
                biz_message=_business_message_for_unparseable_code(
                    coerced_code=coerced_code,
                    explicit_message=_coerce_biz_message(head.get("msg")),
                    raw_code=ret,
                ),
                detail=_schema_paths(payload),
            )

        body = payload.get("body")
        stat_info = body.get("stat_info") if isinstance(body, dict) else None
        if not isinstance(stat_info, dict):
            raise WeComProtocolChanged(
                "响应缺少 body.stat_info 节点", detail=_schema_paths(payload)
            )

        form_id = stat_info.get("form_id")
        creater_vid = stat_info.get("creater_vid")
        creater_name = stat_info.get("creater_name")
        question_infos = stat_info.get("question_infos")
        fork_items_raw = stat_info.get("fork_items")
        if (
            not isinstance(form_id, str | int)
            or not isinstance(creater_vid, str | int)
            or not isinstance(creater_name, str)
            or not isinstance(question_infos, list)
            or not isinstance(fork_items_raw, list)
        ):
            raise WeComProtocolChanged(
                "响应 body.stat_info 缺少必需节点", detail=_schema_paths(payload)
            )
        if len(fork_items_raw) > _MAX_FORK_ITEMS:
            raise WeComProtocolChanged("fork_items 数量超出合理范围,判定为协议异常")

        try:
            questions = [
                WeComQuestionItem.model_validate(
                    {
                        "question_id": item.get("question_id") if isinstance(item, dict) else None,
                        "title": item.get("title") if isinstance(item, dict) else None,
                        "reply_type": item.get("type") if isinstance(item, dict) else None,
                        "must_reply": item.get("must_reply") if isinstance(item, dict) else None,
                    }
                )
                for item in question_infos
            ]
        except ValidationError as exc:
            raise WeComSchemaChanged("表单题目结构与预期不符") from exc

        # `fork_items` only feeds a best-effort duplicate check (`WECOM-06`);
        # a malformed individual entry is skipped rather than failing the
        # whole call, unlike the stricter all-or-nothing validation above for
        # the three target questions this integration cannot function
        # without.
        fork_items: list[WeComFormDetailForkItem] = []
        for raw_item in fork_items_raw:
            if not isinstance(raw_item, dict):
                continue
            try:
                fork_items.append(WeComFormDetailForkItem.model_validate(raw_item))
            except ValidationError:
                continue

        return WeComFormDetail(
            form_id=str(form_id),
            creater_vid=str(creater_vid),
            creater_name=creater_name,
            questions=questions,
            fork_items=fork_items,
        )

    def _parse_submission_result(self, payload: dict[str, Any]) -> WeComSubmissionResult:
        head = payload.get("head")
        if not isinstance(head, dict) or "ret" not in head:
            raise WeComOutcomeUncertain("响应缺少 head.ret 节点,无法确认是否受理")
        ret = head["ret"]
        if ret != 0:
            coerced_code = _coerce_biz_code(ret)
            raise WeComBusinessRejected(
                "提交日报被拒绝",
                biz_code=coerced_code,
                biz_message=_business_message_for_unparseable_code(
                    coerced_code=coerced_code,
                    explicit_message=_coerce_biz_message(head.get("msg")),
                    raw_code=ret,
                ),
                detail=_schema_paths(payload),
            )

        body = payload.get("body")
        if not isinstance(body, dict):
            raise WeComOutcomeUncertain("响应缺少 body 节点,无法确认是否受理")

        answer_replys = body.get("answer_replys")
        if not isinstance(answer_replys, list) or not answer_replys:
            raise WeComOutcomeUncertain("响应缺少 answer_replys,无法确认是否受理")
        first = answer_replys[0]
        if not isinstance(first, dict):
            raise WeComOutcomeUncertain("answer_replys[0] 结构与预期不符")

        answer_id = first.get("answer_id")
        reply_id = first.get("reply_id")
        journal_uuid = first.get("journaluuid")
        user_vid = body.get("user_vid")
        if answer_id is None or reply_id is None or journal_uuid is None or user_vid is None:
            raise WeComOutcomeUncertain("提交回执缺少必需标识字段")

        repeat_before_replys = body.get("repeat_before_replys")
        has_repeat = bool(
            isinstance(repeat_before_replys, dict) and repeat_before_replys.get("answer_replys")
        )

        return WeComSubmissionResult(
            answer_id=str(answer_id),
            reply_id=str(reply_id),
            journal_uuid=str(journal_uuid),
            user_vid=str(user_vid),
            has_repeat_before_replys=has_repeat,
        )
