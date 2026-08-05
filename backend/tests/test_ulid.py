import re
import time

from app.core.ulid import ULID_LENGTH, generate_ulid

_ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def test_generate_ulid_produces_the_expected_length_and_alphabet() -> None:
    value = generate_ulid()

    assert len(value) == ULID_LENGTH == 26
    assert _ULID_PATTERN.match(value)


def test_generate_ulid_returns_distinct_values() -> None:
    values = {generate_ulid() for _ in range(1000)}

    assert len(values) == 1000


def test_generate_ulid_is_lexicographically_sortable_by_time() -> None:
    first = generate_ulid()
    time.sleep(0.005)
    second = generate_ulid()

    assert first < second
