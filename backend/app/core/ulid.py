"""Application-generated ULID primary keys (ADR-010).

Implemented against the stdlib only (no third-party dependency): a ULID is
a 128-bit value — a 48-bit millisecond timestamp followed by 80 bits of
randomness — rendered as 26 Crockford-Base32 characters, lexicographically
sortable by generation time.
"""

import os
import time

_CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_TIMESTAMP_CHARS = 10
_RANDOMNESS_CHARS = 16
_RANDOMNESS_BYTES = 10

ULID_LENGTH = _TIMESTAMP_CHARS + _RANDOMNESS_CHARS


def generate_ulid() -> str:
    timestamp_ms = int(time.time() * 1000)
    randomness = int.from_bytes(os.urandom(_RANDOMNESS_BYTES), "big")
    return _encode(timestamp_ms, _TIMESTAMP_CHARS) + _encode(randomness, _RANDOMNESS_CHARS)


def _encode(value: int, length: int) -> str:
    chars = [""] * length
    for index in range(length - 1, -1, -1):
        chars[index] = _CROCKFORD_ALPHABET[value & 0x1F]
        value >>= 5
    return "".join(chars)
