"""Turn every error into `{"detail": "<plain English>", "code": "<code>"}` (CONTRACT §3)."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.api import ErrorBody, ErrorCode

log = logging.getLogger(__name__)

STATUS_CODES: dict[int, ErrorCode] = {
    400: "validation",
    401: "unauthorised",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "file_too_large",
    415: "unsupported_file",
    429: "rate_limited",
    502: "upstream_unavailable",
}

DEFAULT_DETAIL: dict[ErrorCode, str] = {
    "validation": "Please check the details you entered.",
    "unauthorised": "Please log in to continue.",
    "forbidden": "This request was blocked.",
    "not_found": "We couldn't find that.",
    "rate_limited": "Please wait a moment and try again.",
    "upstream_unavailable": "Some data is temporarily unavailable.",
    "internal": "Something went wrong on our side. Please try again.",
}

# Shown in OpenAPI on every route so the front end's generated types know the error shape.
ERROR_RESPONSES: dict[int | str, dict] = {
    status: {"model": ErrorBody} for status in (400, 401, 403, 404, 409, 413, 415, 429, 502, 500)
}


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        code: ErrorCode,
        detail: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self.code = code
        self.detail = detail or DEFAULT_DETAIL.get(code, "Something went wrong.")
        self.headers = headers


def error_response(
    status: int, code: ErrorCode, detail: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    body = ErrorBody(detail=detail, code=code).model_dump()
    return JSONResponse(body, status_code=status, headers=headers)


def _validation_detail(exc: RequestValidationError) -> str:
    """One readable sentence from Pydantic's error list."""
    errors = exc.errors()
    if not errors:
        return DEFAULT_DETAIL["validation"]
    first = errors[0]
    field = ".".join(str(p) for p in first.get("loc", ()) if p not in ("body", "query", "path"))
    msg = str(first.get("msg", "is not valid")).removeprefix("Value error, ")
    return f"{field}: {msg}" if field else msg


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status, exc.code, exc.detail, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(400, "validation", _validation_detail(exc))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = STATUS_CODES.get(
            exc.status_code, "validation" if exc.status_code < 500 else "internal"
        )
        detail = exc.detail if isinstance(exc.detail, str) else DEFAULT_DETAIL[code]
        if exc.status_code == 404:
            detail = DEFAULT_DETAIL["not_found"]
        return error_response(exc.status_code, code, detail, getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def _internal(_: Request, exc: Exception) -> JSONResponse:
        log.exception("Unhandled error: %s", type(exc).__name__)
        return error_response(500, "internal", DEFAULT_DETAIL["internal"])
