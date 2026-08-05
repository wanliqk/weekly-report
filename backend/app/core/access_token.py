"""JWT access tokens (ADR-007: 24h JWT + token_version).

Named `access_token.py` rather than `jwt.py` so this module's own name
never shadows the third-party `jwt` package it imports.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.clock import Clock, utc_now
from app.core.ulid import generate_ulid

ALGORITHM = "HS256"
ACCESS_TOKEN_TTL = timedelta(hours=24)
_REQUIRED_CLAIMS = ["exp", "iat", "sub", "role", "ver", "jti"]


@dataclass(frozen=True)
class EncodedAccessToken:
    token: str
    expires_at: datetime


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: str
    role: str
    token_version: int
    jti: str


class InvalidAccessTokenError(Exception):
    """Raised for expired, tampered, malformed, or incomplete access tokens."""


def encode_access_token(
    *, user_id: str, role: str, token_version: int, secret: str, clock: Clock = utc_now
) -> EncodedAccessToken:
    issued_at = clock()
    if issued_at.tzinfo is None:
        issued_at = issued_at.replace(tzinfo=UTC)
    expires_at = issued_at + ACCESS_TOKEN_TTL
    payload = {
        "sub": user_id,
        "role": role,
        "ver": token_version,
        "iat": issued_at,
        "exp": expires_at,
        "jti": generate_ulid(),
    }
    token = jwt.encode(payload, secret, algorithm=ALGORITHM)
    return EncodedAccessToken(token=token, expires_at=expires_at)


def decode_access_token(token: str, *, secret: str) -> AccessTokenClaims:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            options={"require": _REQUIRED_CLAIMS},
        )
    except jwt.PyJWTError as error:
        raise InvalidAccessTokenError(str(error)) from error

    user_id = _required_string(payload, "sub")
    role = _required_string(payload, "role")
    token_version = payload.get("ver")
    jti = _required_string(payload, "jti")
    if role not in {"admin", "user"}:
        raise InvalidAccessTokenError("invalid role claim")
    if not isinstance(token_version, int) or isinstance(token_version, bool) or token_version < 1:
        raise InvalidAccessTokenError("invalid token version claim")

    return AccessTokenClaims(
        user_id=user_id,
        role=role,
        token_version=token_version,
        jti=jti,
    )


def _required_string(payload: dict[str, Any], claim: str) -> str:
    value = payload.get(claim)
    if not isinstance(value, str) or not value:
        raise InvalidAccessTokenError(f"invalid {claim} claim")
    return value
