"""Regression guard for WECOM-00 (ISS-028): synthetic WeCom fixtures must never
contain real captured values.

The user-provided real protocol sample (`backend/wx-ribao/`) is precisely
`.gitignore`d and never committed. When that directory happens to exist locally
(only on the machine that originally received it from the user), this test
dynamically extracts the sensitive *values* it carries — cookie values,
account/document identifiers, person names, work content — and asserts none of
them leak into the committed synthetic fixtures under
`backend/tests/fixtures/wecom/`. On every other machine/CI run the directory is
absent and this test is skipped: it has nothing local to compare against, and
the fixtures themselves never contain real data in the first place.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_RAW_SAMPLE_DIR = _BACKEND_ROOT / "wx-ribao"
_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "wecom"

# JSON keys known (from the real captured `answer_page` request/response) to carry
# identifying or secret *values* — as opposed to generic/reusable protocol field
# names (e.g. "title", "question_id", "reply_type") that the synthetic fixtures
# intentionally reuse to preserve protocol shape.
_SENSITIVE_JSON_KEYS = {
    "create_name",
    "reply_name",
    "user_name",
    "avatar",
    "text_reply",
    "form_id",
    "base_form_id",
    "template_id",
    "templateid",
    "journaluuid",
    "create_vid",
    "reply_id",
    "user_vid",
    "vid",
    "receive_vid",
    "sid",
}

_MIN_TOKEN_LENGTH = 6
# Chinese given names are typically 2-4 characters — far shorter than the
# generic 6-char threshold used for cookie values/identifiers, which exists to
# avoid false positives on short generic strings.
_MIN_NAME_LENGTH = 2
_NAME_KEYS = {"create_name", "reply_name", "user_name"}
_COOKIE_LINE = re.compile(r"^cookie:\s*[A-Za-z0-9_]+=(\S+)", re.MULTILINE)
_REFERER_LINE = re.compile(r"^referer:\s*(\S+)", re.MULTILINE)
_MULTIPART_FIELD_NAME = re.compile(r'name="([^"]+)"')
_SCRIPT_URL = re.compile(r'url = "(https://[^"]+)"')
_SCRIPT_FIXED_VALUE = re.compile(r"'[a-zA-Z_]+':\s*'([^']+)'")


def _collect_leaf(value: object, tokens: set[str], min_length: int) -> None:
    if isinstance(value, str) and len(value.strip()) >= min_length:
        tokens.add(value)
    elif isinstance(value, int) and not isinstance(value, bool) and len(str(value)) >= min_length:
        tokens.add(str(value))


def _collect_json_values(node: object, tokens: set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _SENSITIVE_JSON_KEYS:
                min_length = _MIN_NAME_LENGTH if key in _NAME_KEYS else _MIN_TOKEN_LENGTH
                _collect_leaf(value, tokens, min_length)
            _collect_json_values(value, tokens)
    elif isinstance(node, list):
        for item in node:
            _collect_json_values(item, tokens)


def _extract_from_raw_request(tokens: set[str]) -> None:
    path = _RAW_SAMPLE_DIR / "http_raw_request.txt"
    if not path.exists():
        return
    raw_request = path.read_text(encoding="utf-8")

    for value in _COOKIE_LINE.findall(raw_request):
        if len(value) >= _MIN_TOKEN_LENGTH:
            tokens.add(value)

    referer_match = _REFERER_LINE.search(raw_request)
    if referer_match:
        referer = referer_match.group(1)
        for param in ("journaluuid", "template_id"):
            value_match = re.search(rf"[?&]{param}=([^&\s#]+)", referer)
            if value_match and len(value_match.group(1)) >= _MIN_TOKEN_LENGTH:
                tokens.add(value_match.group(1))

    for part in raw_request.split("------")[1:]:
        header_body = part.split("\n\n", 1)
        if len(header_body) != 2:
            continue
        header, body = header_body
        name_match = _MULTIPART_FIELD_NAME.search(header)
        if not name_match:
            continue
        field_name = name_match.group(1)
        value = body.strip()
        if field_name == "form_id":
            if len(value) >= _MIN_TOKEN_LENGTH:
                tokens.add(value)
        elif field_name in {"form_reply", "wwjournal_data"} and value.startswith("{"):
            try:
                parsed: object = json.loads(value)
            except ValueError:
                continue
            _collect_json_values(parsed, tokens)


def _extract_from_raw_response(tokens: set[str]) -> None:
    path = _RAW_SAMPLE_DIR / "http_raw_response.txt"
    if not path.exists():
        return
    raw_response = path.read_text(encoding="utf-8")
    separator = "\r\n\r\n" if "\r\n\r\n" in raw_response else "\n\n"
    if separator not in raw_response:
        return
    _headers, _, body = raw_response.partition(separator)
    body = body.strip()
    if not body:
        return
    try:
        parsed: object = json.loads(body)
    except ValueError:
        return
    _collect_json_values(parsed, tokens)


def _extract_from_reference_script(tokens: set[str]) -> None:
    path = _RAW_SAMPLE_DIR / "wx-ribao.py"
    if not path.exists():
        return
    script_text = path.read_text(encoding="utf-8")

    url_match = _SCRIPT_URL.search(script_text)
    if url_match:
        url = url_match.group(1)
        form_id_match = re.search(r"/forms/j/([^/?#]+)", url)
        if form_id_match and len(form_id_match.group(1)) >= _MIN_TOKEN_LENGTH:
            tokens.add(form_id_match.group(1))
        for value_match in re.finditer(r"[?&]journaluuid=([^&\s#]+)", url):
            if len(value_match.group(1)) >= _MIN_TOKEN_LENGTH:
                tokens.add(value_match.group(1))

    for value in _SCRIPT_FIXED_VALUE.findall(script_text):
        if len(value) >= _MIN_TOKEN_LENGTH:
            tokens.add(value)


def _extract_sensitive_tokens() -> set[str]:
    tokens: set[str] = set()
    _extract_from_raw_request(tokens)
    _extract_from_raw_response(tokens)
    _extract_from_reference_script(tokens)
    return tokens


def _read_fixture_text() -> str:
    contents: list[str] = []
    for path in sorted(_FIXTURE_DIR.glob("*")):
        if path.is_file():
            contents.append(path.read_text(encoding="utf-8"))
    return "\n".join(contents)


def test_synthetic_fixtures_contain_no_real_captured_values() -> None:
    if not _RAW_SAMPLE_DIR.exists():
        pytest.skip("backend/wx-ribao/ 本地真实样例不存在(已被 gitignore 精确排除), 无可比对内容")

    sensitive_tokens = _extract_sensitive_tokens()
    assert sensitive_tokens, "未能从本地真实样例中提取到任何比对 token, 扫描规则可能已经失效"

    fixture_text = _read_fixture_text()
    leaked = {token for token in sensitive_tokens if token in fixture_text}

    assert not leaked, f"合成 fixture 中检测到真实样例的敏感取值, 禁止提交: {sorted(leaked)!r}"
