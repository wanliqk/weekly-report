from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.access_token import (
    ACCESS_TOKEN_TTL,
    ALGORITHM,
    InvalidAccessTokenError,
    decode_access_token,
    encode_access_token,
)

SECRET = "s" * 64


def test_access_token_round_trip_contains_the_required_claims() -> None:
    issued_at = datetime.now(UTC)

    encoded = encode_access_token(
        user_id="01K000000000000000000000",
        role="admin",
        token_version=3,
        secret=SECRET,
        clock=lambda: issued_at,
    )
    claims = decode_access_token(encoded.token, secret=SECRET)

    assert claims.user_id == "01K000000000000000000000"
    assert claims.role == "admin"
    assert claims.token_version == 3
    assert claims.jti
    assert encoded.expires_at - issued_at == ACCESS_TOKEN_TTL


def test_expired_access_token_is_rejected() -> None:
    encoded = encode_access_token(
        user_id="01K000000000000000000000",
        role="user",
        token_version=1,
        secret=SECRET,
        clock=lambda: datetime.now(UTC) - timedelta(days=2),
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(encoded.token, secret=SECRET)


def test_tampered_access_token_is_rejected() -> None:
    encoded = encode_access_token(
        user_id="01K000000000000000000000",
        role="user",
        token_version=1,
        secret=SECRET,
    )
    replacement = "a" if encoded.token[-1] != "a" else "b"

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(encoded.token[:-1] + replacement, secret=SECRET)


@pytest.mark.parametrize(
    ("claim", "value"),
    [("sub", ""), ("role", "owner"), ("ver", 0), ("ver", True), ("jti", "")],
)
def test_invalid_required_claim_types_or_values_are_rejected(claim: str, value: object) -> None:
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": "01K000000000000000000000",
        "role": "user",
        "ver": 1,
        "iat": now,
        "exp": now + timedelta(hours=1),
        "jti": "01K000000000000000000001",
    }
    payload[claim] = value
    token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token, secret=SECRET)


def test_missing_required_claim_is_rejected() -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "01K000000000000000000000",
            "role": "user",
            "ver": 1,
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        SECRET,
        algorithm=ALGORITHM,
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token, secret=SECRET)
