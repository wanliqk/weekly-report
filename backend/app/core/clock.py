"""Injectable UTC clock (coding-rule.md 4.3: no direct local-time calls).

Services take a `Clock` with this default so tests can substitute a fixed
or controlled time source instead of monkeypatching `datetime`.
"""

from collections.abc import Callable
from datetime import UTC, datetime

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)
