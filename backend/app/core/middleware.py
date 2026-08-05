from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

RequestHandler = Callable[[Request], Awaitable[Response]]


def _is_safe_request_id(value: str) -> bool:
    return 1 <= len(value) <= 64 and value.isascii() and all(
        character.isalnum() or character in "-_" for character in value
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
        return response
