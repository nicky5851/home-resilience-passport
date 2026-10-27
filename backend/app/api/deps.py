from typing import Annotated

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.cache import Cache, DbCache
from app.api.errors import ApiError
from app.api.stub_store import STUB_USER_ID
from app.config import AUTH_COOKIE_LIFETIME, AUTH_COOKIE_NAME, get_settings
from app.db.session import get_session
from app.schemas import UserRead

STUB_COOKIE_PREFIX = "stub-"


def get_api_cache(session: Annotated[AsyncSession, Depends(get_session)]) -> Cache:
    return DbCache(session)


ApiCacheDep = Annotated[Cache, Depends(get_api_cache)]


def current_user(request: Request) -> UserRead:
    """Foundation stub: the cookie is `stub-<email>` (CONTRACT §4). Replaced in N10."""
    cookie = request.cookies.get(AUTH_COOKIE_NAME, "")
    if not cookie.startswith(STUB_COOKIE_PREFIX) or len(cookie) == len(STUB_COOKIE_PREFIX):
        raise ApiError(401, "unauthorised")
    return UserRead(id=STUB_USER_ID, email=cookie.removeprefix(STUB_COOKIE_PREFIX))


CurrentUser = Annotated[UserRead, Depends(current_user)]


def set_auth_cookie(response: Response, value: str) -> None:
    response.set_cookie(
        AUTH_COOKIE_NAME,
        value,
        max_age=int(AUTH_COOKIE_LIFETIME.total_seconds()),
        path="/",
        httponly=True,
        samesite="lax",
        secure=get_settings().is_production,
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        AUTH_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=get_settings().is_production,
    )
