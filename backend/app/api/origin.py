"""Origin check: our CSRF protection together with SameSite=Lax (CONTRACT §4)."""

from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import Request, Response

from app.api.errors import error_response
from app.config import get_settings

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _origin_of(url: str) -> str | None:
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return None
    return f"{parts.scheme}://{parts.netloc}".lower()


async def origin_check(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    if request.method in UNSAFE_METHODS:
        header = request.headers.get("origin") or request.headers.get("referer") or ""
        origin = _origin_of(header)
        allowed = {o.lower() for o in get_settings().allowed_origin_list}
        if origin not in allowed:
            return error_response(
                403, "forbidden", "This request did not come from an allowed site."
            )
    return await call_next(request)
