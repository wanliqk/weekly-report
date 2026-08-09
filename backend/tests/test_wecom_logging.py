import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.wecom_logging import (
    WECOM_LOG_FILE_NAME,
    WECOM_RAW_LOG_FILE_NAME,
    WECOM_RAW_LOGGER_NAME,
    configure_wecom_logging,
    configure_wecom_raw_debug_logging,
    log_wecom_event,
    log_wecom_raw_body,
    shutdown_wecom_logging,
    shutdown_wecom_raw_debug_logging,
)


@pytest.fixture(autouse=True)
def _reset_wecom_logging() -> Iterator[None]:
    shutdown_wecom_logging()
    shutdown_wecom_raw_debug_logging()
    yield
    shutdown_wecom_logging()
    shutdown_wecom_raw_debug_logging()


def _settings(tmp_path: Path, *, redact: bool, debug_raw_body: bool = False) -> Settings:
    return Settings(
        environment="test",
        log_dir=tmp_path / "logs",
        wecom_log_redact=redact,
        wecom_debug_raw_body=debug_raw_body,
    )


def _emit_diagnostic_event() -> None:
    log_wecom_event(
        logging.getLogger("app.integrations.wecom.client"),
        event="request",
        path_template="/journal/get_template_combine_info",
        outcome="business_rejected",
        duration_ms=23,
        diagnostics={
            "http_status": 200,
            "error_type": "WeComBusinessRejected",
            "error_message": "获取模板信息被拒绝",
            "business_code": 41001,
            "business_message": "no permission",
        },
    )


def test_redacted_log_contains_only_minimum_request_metadata(tmp_path: Path) -> None:
    settings = _settings(tmp_path, redact=True)
    log_path = configure_wecom_logging(settings)

    _emit_diagnostic_event()
    shutdown_wecom_logging()

    assert log_path == settings.log_dir / WECOM_LOG_FILE_NAME
    text = log_path.read_text(encoding="utf-8")
    assert "event=request" in text
    assert "path=/journal/get_template_combine_info" in text
    assert "outcome=business_rejected" in text
    assert "duration_ms=23" in text
    assert "http_status" not in text
    assert "WeComBusinessRejected" not in text
    assert "41001" not in text
    assert "no permission" not in text


def test_detailed_log_includes_only_whitelisted_diagnostics(tmp_path: Path) -> None:
    settings = _settings(tmp_path, redact=False)
    configure_wecom_logging(settings)

    _emit_diagnostic_event()
    shutdown_wecom_logging()

    text = (settings.log_dir / WECOM_LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "http_status=200" in text
    assert 'error_type="WeComBusinessRejected"' in text
    assert 'error_message="获取模板信息被拒绝"' in text
    assert "business_code=41001" in text
    assert 'business_message="no permission"' in text


def test_detailed_log_accepts_only_bounded_protocol_schema_paths(tmp_path: Path) -> None:
    settings = _settings(tmp_path, redact=False)
    configure_wecom_logging(settings)
    logger = logging.getLogger("app.integrations.wecom.client")
    log_wecom_event(
        logger,
        event="connection_validation",
        path_template="/journal/get_template_combine_info",
        outcome="client_error",
        duration_ms=1,
        diagnostics={"schema_paths": "body,body.combine_info,body.combine_info.form"},
    )
    log_wecom_event(
        logger,
        event="connection_validation",
        path_template="/journal/get_template_combine_info",
        outcome="client_error",
        duration_ms=1,
        diagnostics={"schema_paths": "body.form,Cookie=SECRET"},
    )
    shutdown_wecom_logging()

    text = (settings.log_dir / WECOM_LOG_FILE_NAME).read_text(encoding="utf-8")
    assert 'schema_paths="body,body.combine_info,body.combine_info.form"' in text
    assert "Cookie=SECRET" not in text


def test_detailed_mode_still_scrubs_credentials_and_ignores_unknown_fields(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path, redact=False)
    configure_wecom_logging(settings)
    logger = logging.getLogger("app.integrations.wecom.client")
    log_wecom_event(
        logger,
        event="request",
        path_template="/journal/get_template_combine_info",
        outcome="protocol_changed",
        duration_ms=1,
        diagnostics={
            "error_message": (
                "wedoc_sid=COOKIE-SECRET Authorization: Bearer eyJheader123.payload123.signature123"
            ),
            "ignored": "SHOULD-NOT-BE-WRITTEN",
        },
    )
    shutdown_wecom_logging()

    text = (settings.log_dir / WECOM_LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "COOKIE-SECRET" not in text
    assert "eyJheader123.payload123.signature123" not in text
    assert "SHOULD-NOT-BE-WRITTEN" not in text
    assert "[REDACTED]" in text


def test_wecom_log_rotates_and_respects_backup_limit(tmp_path: Path) -> None:
    settings = _settings(tmp_path, redact=False)
    configure_wecom_logging(settings, max_bytes=300, backup_count=2)
    logger = logging.getLogger("app.integrations.wecom.client")

    for index in range(20):
        log_wecom_event(
            logger,
            event="request",
            path_template="/journal/get_template_combine_info",
            outcome="protocol_changed",
            duration_ms=index,
            diagnostics={"error_message": "固定安全诊断" * 20},
        )
    shutdown_wecom_logging()

    assert (settings.log_dir / WECOM_LOG_FILE_NAME).exists()
    assert (settings.log_dir / f"{WECOM_LOG_FILE_NAME}.1").exists()
    assert len(list(settings.log_dir.glob(f"{WECOM_LOG_FILE_NAME}*"))) <= 3


# -- raw-body debug switch (explicit, off-by-default, user-authorized) ------


def test_raw_debug_logging_disabled_by_default_writes_no_file(tmp_path: Path) -> None:
    settings = _settings(tmp_path, redact=False, debug_raw_body=False)
    configure_wecom_logging(settings)
    log_path = configure_wecom_raw_debug_logging(settings)

    log_wecom_raw_body(
        logging.getLogger(WECOM_RAW_LOGGER_NAME),
        direction="request",
        path_template="/wework/journal/get_journal_list",
        body='{"template_id": "REAL-VALUE"}',
    )
    shutdown_wecom_logging()
    shutdown_wecom_raw_debug_logging()

    assert log_path is None
    assert not (settings.log_dir / WECOM_RAW_LOG_FILE_NAME).exists()


def test_raw_debug_logging_writes_full_body_when_enabled(tmp_path: Path) -> None:
    settings = _settings(tmp_path, redact=False, debug_raw_body=True)
    configure_wecom_logging(settings)
    log_path = configure_wecom_raw_debug_logging(settings)
    assert log_path == settings.log_dir / WECOM_RAW_LOG_FILE_NAME

    raw_logger = logging.getLogger(WECOM_RAW_LOGGER_NAME)
    log_wecom_raw_body(
        raw_logger,
        direction="request",
        path_template="/wework/journal/get_journal_list",
        body='{"template_id": "REAL-TEMPLATE-VALUE", "limit": 50}',
    )
    log_wecom_raw_body(
        raw_logger,
        direction="response",
        path_template="/wework/journal/get_journal_list",
        body='{"errcode": "", "entrys": []}',
    )
    shutdown_wecom_logging()
    shutdown_wecom_raw_debug_logging()

    text = log_path.read_text(encoding="utf-8")
    assert "direction=request" in text
    assert "REAL-TEMPLATE-VALUE" in text
    assert "direction=response" in text
    assert '"errcode": ""' in text
    # Content this unredacted must never land in the normal shareable log.
    main_text = (settings.log_dir / WECOM_LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "REAL-TEMPLATE-VALUE" not in main_text


def test_raw_debug_logging_still_scrubs_credential_patterns(tmp_path: Path) -> None:
    settings = _settings(tmp_path, redact=False, debug_raw_body=True)
    log_path = configure_wecom_raw_debug_logging(settings)
    assert log_path is not None

    log_wecom_raw_body(
        logging.getLogger(WECOM_RAW_LOGGER_NAME),
        direction="response",
        path_template="/wework/journal/get_journal_list",
        body="wedoc_sid=COOKIE-SECRET Authorization: Bearer eyJheader.payload.signature",
    )
    shutdown_wecom_raw_debug_logging()

    text = log_path.read_text(encoding="utf-8")
    assert "COOKIE-SECRET" not in text
    assert "eyJheader.payload.signature" not in text
    assert "[REDACTED]" in text


def test_raw_debug_logging_rejects_unknown_direction_or_path(tmp_path: Path) -> None:
    settings = _settings(tmp_path, redact=False, debug_raw_body=True)
    log_path = configure_wecom_raw_debug_logging(settings)
    assert log_path is not None
    raw_logger = logging.getLogger(WECOM_RAW_LOGGER_NAME)

    log_wecom_raw_body(
        raw_logger, direction="not-a-direction", path_template="/formcol/answer_page", body="x"
    )
    log_wecom_raw_body(
        raw_logger, direction="request", path_template="/not/an/allowed/path", body="y"
    )
    shutdown_wecom_raw_debug_logging()

    assert log_path.read_text(encoding="utf-8") == ""


def test_enabling_raw_debug_logging_warns_in_the_main_log(tmp_path: Path) -> None:
    settings = _settings(tmp_path, redact=False, debug_raw_body=True)
    configure_wecom_logging(settings)
    configure_wecom_raw_debug_logging(settings)
    shutdown_wecom_logging()
    shutdown_wecom_raw_debug_logging()

    main_text = (settings.log_dir / WECOM_LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "raw_debug_enabled" in main_text
