"""Fixed Asia/Shanghai (UTC+8, no DST) formatting for generated files.

`user_settings.timezone` is fixed to `Asia/Shanghai` for V1 (database.md
3.2) and China has not observed DST since 1991, so a constant offset is
correct and avoids depending on the IANA tz database (`zoneinfo` needs the
optional `tzdata` package to resolve real zone names on Windows).
"""

from datetime import UTC, datetime, timedelta

SHANGHAI_OFFSET = timedelta(hours=8)


def to_shanghai(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC) + SHANGHAI_OFFSET


def format_shanghai(value: datetime) -> str:
    return to_shanghai(value).strftime("%Y-%m-%d %H:%M:%S")
