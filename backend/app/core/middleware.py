import secrets
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

RequestHandler = Callable[[Request], Awaitable[Response]]

RUNTIME_SECRET_HEADER = "X-Runtime-Secret"
RUNTIME_SECRET_EXEMPT_PATHS = frozenset({"/health", "/docs", "/openapi.json"})


def _is_safe_request_id(value: str) -> bool:
    return (
        1 <= len(value) <= 64
        and value.isascii()
        and all(character.isalnum() or character in "-_" for character in value)
    )


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestHandler) -> Response:
        supplied_request_id = request.headers.get("X-Request-Id", "")
        request_id = (
            supplied_request_id if _is_safe_request_id(supplied_request_id) else uuid4().hex
        )
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        if request.url.path.startswith("/api/v1/"):
            response.headers["Cache-Control"] = "no-store"
        return response


class RuntimeSecretMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, expected_secret: str | None) -> None:
        super().__init__(app)
        self._expected_secret = expected_secret

    async def dispatch(self, request: Request, call_next: RequestHandler) -> Response:
        if request.url.path in RUNTIME_SECRET_EXEMPT_PATHS:
            return await call_next(request)

        supplied_secret = request.headers.get(RUNTIME_SECRET_HEADER, "")
        expected_secret = self._expected_secret
        if expected_secret is None or not secrets.compare_digest(supplied_secret, expected_secret):
            return JSONResponse(
                status_code=401,
                content={"code": 40103, "msg": "运行期密钥缺失或无效", "data": {}},
            )

        return await call_next(request)
