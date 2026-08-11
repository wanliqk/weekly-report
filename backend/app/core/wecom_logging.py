from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Final

from app.core.config import Settings

WECOM_LOGGER_NAME: Final = "app.integrations.wecom"
WECOM_LOG_FILE_NAME: Final = "wecom.log"
WECOM_LOG_MAX_BYTES: Final = 2 * 1024 * 1024
WECOM_LOG_BACKUP_COUNT: Final = 5

# A deliberately separate logger/file from `WECOM_LOGGER_NAME`/`wecom.log`:
# `Settings.wecom_debug_raw_body` is an explicit, user-authorized,
# off-by-default troubleshooting exception (see `config.py`'s comment) that
# writes raw request/response *bodies* here — never headers, never Cookie
# values, that boundary holds regardless of this switch. Kept in its own
# file so `wecom.log`'s "safe to share" guarantee never depends on whether
# this switch happened to be on at some point.
WECOM_RAW_LOGGER_NAME: Final = "app.integrations.wecom.raw"
WECOM_RAW_LOG_FILE_NAME: Final = "wecom-raw-debug.log"
WECOM_RAW_LOG_MAX_BYTES: Final = 2 * 1024 * 1024
WECOM_RAW_LOG_BACKUP_COUNT: Final = 2
_MAX_RAW_BODY_LENGTH: Final = 20_000
_ALLOWED_RAW_DIRECTIONS: Final = frozenset({"request", "response"})

_DIAGNOSTICS_ATTRIBUTE: Final = "wecom_diagnostics"
_ALLOWED_PATH_TEMPLATES: Final = frozenset(
    {
        "/journal/get_template_combine_info",
        # Serves both `get_form_detail()` (GET, `?_prefetch=1`) and
        # `submit_daily()` (POST) — see `_ANSWER_PAGE_PATH` in
        # `app/integrations/wecom/client.py` (`ai-docs/issues.md` `ISS-056`
        # retired the separate `/formcol/detail` path this set used to also
        # allow).
        "/formcol/answer_page",
    }
)
_ALLOWED_DIAGNOSTIC_KEYS: Final = frozenset(
    {
        "business_code",
        "business_message",
        "date_candidate_count",
        "date_reply_type",
        "error_message",
        "error_type",
        "http_status",
        "question_count",
        "recognized_question_count",
        "schema_paths",
        "today_candidate_count",
        "today_reply_type",
        "tomorrow_candidate_count",
        "tomorrow_reply_type",
        "unique_submit_order_count",
    }
)
_SAFE_LABEL_PATTERN: Final = re.compile(r"^[a-z0-9_.-]{1,64}$")
_SAFE_SCHEMA_PATHS_PATTERN: Final = re.compile(r"^[A-Za-z0-9_.\[\],]{1,4096}$")
_AUTHORIZATION_PATTERN: Final = re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+")
_COOKIE_PATTERN: Final = re.compile(r"(?i)((?:set-cookie|cookie)\s*[:=]\s*)[^\r\n]+")
_SECRET_ASSIGNMENT_PATTERN: Final = re.compile(
    r"(?i)((?:wedoc_sid|runtime_secret|main_bridge_secret|x-runtime-secret|"
    r"x-main-bridge-secret)\s*[:=]\s*)[^\s,;]+"
)
_JWT_PATTERN: Final = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")


class _WeComRotatingFileHandler(RotatingFileHandler):
    pass


class _WeComRawDebugFileHandler(RotatingFileHandler):
    pass


def _scrub_protected_text(value: str) -> str:
    scrubbed = _AUTHORIZATION_PATTERN.sub(r"\1[REDACTED]", value)
    scrubbed = _COOKIE_PATTERN.sub(r"\1[REDACTED]", scrubbed)
    scrubbed = _SECRET_ASSIGNMENT_PATTERN.sub(r"\1[REDACTED]", scrubbed)
    return _JWT_PATTERN.sub("[REDACTED]", scrubbed)


def _safe_label(value: str) -> str:
    return value if _SAFE_LABEL_PATTERN.fullmatch(value) else "invalid"


def _safe_diagnostics(
    diagnostics: Mapping[str, str | int | bool | None] | None,
) -> dict[str, str | int | bool | None]:
    if diagnostics is None:
        return {}
    safe: dict[str, str | int | bool | None] = {}
    for key, value in diagnostics.items():
        if key not in _ALLOWED_DIAGNOSTIC_KEYS or not (
            value is None or isinstance(value, str | int | bool)
        ):
            continue
        if key == "schema_paths" and (
            not isinstance(value, str) or _SAFE_SCHEMA_PATHS_PATTERN.fullmatch(value) is None
        ):
            continue
        safe[key] = value
    return safe


def _format_diagnostic_value(value: str | int | bool | None) -> str:
    safe_value = _scrub_protected_text(value) if isinstance(value, str) else value
    return json.dumps(safe_value, ensure_ascii=False, separators=(",", ":"))


class _WeComLogFormatter(logging.Formatter):
    def __init__(self, *, redact: bool) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        self._redact = redact

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        diagnostics = getattr(record, _DIAGNOSTICS_ATTRIBUTE, None)
        if not self._redact and isinstance(diagnostics, dict):
            detail_text = " ".join(
                f"{key}={_format_diagnostic_value(value)}"
                for key, value in sorted(diagnostics.items())
            )
            if detail_text:
                rendered = f"{rendered} {detail_text}"
        # This protection is unconditional. The redaction switch only controls
        # whitelisted diagnostics; it can never enable credential logging.
        return _scrub_protected_text(rendered)


class _WeComRawDebugFormatter(logging.Formatter):
    """Formats raw-body debug records. Unlike `_WeComLogFormatter`, the
    message itself carries the (potentially large, potentially real report
    content) body rather than an allowlisted-key diagnostics dict — but the
    same unconditional credential-pattern scrub still runs, as a defense-in-
    depth backstop in case a body ever happened to contain a Cookie/token-
    shaped substring."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )

    def format(self, record: logging.LogRecord) -> str:
        return _scrub_protected_text(super().format(record))


def configure_wecom_logging(
    settings: Settings,
    *,
    max_bytes: int = WECOM_LOG_MAX_BYTES,
    backup_count: int = WECOM_LOG_BACKUP_COUNT,
) -> Path:
    """Configure the isolated rotating WeCom diagnostic log after migrations.

    Alembic's logging setup disables existing loggers, so runtime startup calls
    this function only after migrations and this function explicitly re-enables
    the WeCom logger tree.
    """

    log_path = settings.log_dir / WECOM_LOG_FILE_NAME
    log_path.parent.mkdir(parents=True, exist_ok=True)
    target_logger = logging.getLogger(WECOM_LOGGER_NAME)
    for handler in list(target_logger.handlers):
        if isinstance(handler, _WeComRotatingFileHandler):
            target_logger.removeHandler(handler)
            handler.close()

    handler = _WeComRotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(_WeComLogFormatter(redact=settings.wecom_log_redact))
    target_logger.addHandler(handler)
    target_logger.setLevel(logging.DEBUG)
    target_logger.disabled = False
    target_logger.propagate = False

    for name, registered_logger in logging.root.manager.loggerDict.items():
        if isinstance(registered_logger, logging.Logger) and name.startswith(
            f"{WECOM_LOGGER_NAME}."
        ):
            registered_logger.disabled = False

    return log_path


def shutdown_wecom_logging() -> None:
    """Close only handlers installed by :func:`configure_wecom_logging`."""

    target_logger = logging.getLogger(WECOM_LOGGER_NAME)
    for handler in list(target_logger.handlers):
        if isinstance(handler, _WeComRotatingFileHandler):
            target_logger.removeHandler(handler)
            handler.close()
    target_logger.setLevel(logging.NOTSET)
    target_logger.propagate = True


def configure_wecom_raw_debug_logging(
    settings: Settings,
    *,
    max_bytes: int = WECOM_RAW_LOG_MAX_BYTES,
    backup_count: int = WECOM_RAW_LOG_BACKUP_COUNT,
) -> Path | None:
    """Attach the raw-body debug file handler only when explicitly enabled.

    When `settings.wecom_debug_raw_body` is `False` (the default), this
    guarantees the raw logger has no handler and is disabled — a stray
    `log_wecom_raw_body` call from anywhere goes nowhere, on top of call
    sites already gating on the same flag. Returns the log path when
    enabled, `None` otherwise.
    """

    target_logger = logging.getLogger(WECOM_RAW_LOGGER_NAME)
    for handler in list(target_logger.handlers):
        if isinstance(handler, _WeComRawDebugFileHandler):
            target_logger.removeHandler(handler)
            handler.close()

    if not settings.wecom_debug_raw_body:
        target_logger.setLevel(logging.NOTSET)
        target_logger.disabled = True
        target_logger.propagate = False
        return None

    log_path = settings.log_dir / WECOM_RAW_LOG_FILE_NAME
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = _WeComRawDebugFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(_WeComRawDebugFormatter())
    target_logger.addHandler(handler)
    target_logger.setLevel(logging.DEBUG)
    target_logger.disabled = False
    target_logger.propagate = False

    logging.getLogger(WECOM_LOGGER_NAME).warning(
        "event=raw_debug_enabled outcome=warning "
        "detail=wecom-raw-debug.log 正在记录未脱敏的请求/响应正文(可能含真实日报内容);"
        "调试结束后请立即关闭 WEEKLY_REPORT_WECOM_DEBUG_RAW_BODY 并删除该文件"
    )
    return log_path


def shutdown_wecom_raw_debug_logging() -> None:
    """Close only handlers installed by :func:`configure_wecom_raw_debug_logging`."""

    target_logger = logging.getLogger(WECOM_RAW_LOGGER_NAME)
    for handler in list(target_logger.handlers):
        if isinstance(handler, _WeComRawDebugFileHandler):
            target_logger.removeHandler(handler)
            handler.close()
    target_logger.setLevel(logging.NOTSET)
    target_logger.propagate = True


def log_wecom_raw_body(
    logger: logging.Logger,
    *,
    direction: str,
    path_template: str,
    body: str,
) -> None:
    """Write one raw request/response *body* to `wecom-raw-debug.log`.

    No header/Cookie parameter exists on this function, by design — callers
    (`WeComInternalClient`) never have a way to pass one in, independent of
    whether the caller checked `settings.wecom_debug_raw_body` first. `body`
    is still passed through the same credential-pattern scrub as every other
    WeCom log line, and truncated defensively.
    """

    if direction not in _ALLOWED_RAW_DIRECTIONS or path_template not in _ALLOWED_PATH_TEMPLATES:
        return
    if len(body) > _MAX_RAW_BODY_LENGTH:
        body = f"{body[:_MAX_RAW_BODY_LENGTH]}...[TRUNCATED]"
    logger.debug("direction=%s path=%s body=%s", direction, path_template, body)


def log_wecom_event(
    logger: logging.Logger,
    *,
    event: str,
    path_template: str,
    outcome: str,
    duration_ms: int,
    diagnostics: Mapping[str, str | int | bool | None] | None = None,
) -> None:
    """Emit one event containing fixed request metadata and safe diagnostics.

    The API intentionally has no header/body/Cookie/form-id parameters. Callers
    can only add primitive values under a small diagnostic-key allowlist.
    """

    safe_path = path_template if path_template in _ALLOWED_PATH_TEMPLATES else "/rejected"
    logger.debug(
        "event=%s method=POST host=doc.weixin.qq.com path=%s outcome=%s duration_ms=%d",
        _safe_label(event),
        safe_path,
        _safe_label(outcome),
        max(0, duration_ms),
        extra={_DIAGNOSTICS_ATTRIBUTE: _safe_diagnostics(diagnostics)},
    )
