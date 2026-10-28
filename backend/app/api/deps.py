import math
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.cache import Cache, DbCache
from app.api.errors import ApiError
from app.auth.users import UserManager, UserStore, jwt_strategy
from app.config import (
    AUTH_COOKIE_LIFETIME,
    AUTH_COOKIE_NAME,
    LAST_SEEN_INTERVAL,
    RATE_LIMIT_LOGIN,
    RATE_LIMIT_REGISTER,
    get_settings,
)
from app.core.ratelimit import limiter
from app.db.models import User
from app.db.session import get_session
from app.schemas import UserRead

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_api_cache(session: SessionDep) -> Cache:
    return DbCache(session)


ApiCacheDep = Annotated[Cache, Depends(get_api_cache)]


def get_user_manager(session: SessionDep) -> UserManager:
    return UserManager(UserStore(session))


UserManagerDep = Annotated[UserManager, Depends(get_user_manager)]


async def current_user_row(request: Request, manager: UserManagerDep) -> User:
    """The logged-in user from the `hrp_auth` JWT cookie (CONTRACT §4), or 401."""
    token = request.cookies.get(AUTH_COOKIE_NAME)
    user = await jwt_strategy().read_token(token, manager) if token else None
    if user is None or not user.is_active:
        raise ApiError(401, "unauthorised")
    now = datetime.now(UTC)
    if user.last_seen_at is None or now - user.last_seen_at >= LAST_SEEN_INTERVAL:
        await manager.user_db.update(user, {"last_seen_at": now})
    return user


CurrentUserRow = Annotated[User, Depends(current_user_row)]


def current_user(user: CurrentUserRow) -> UserRead:
    return user_read(user)


CurrentUser = Annotated[UserRead, Depends(current_user)]


def user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        is_verified=user.is_verified,
    )


# --- Rate limits (CONTRACT §3) --------------------------------------------------------------


def client_ip(request: Request) -> str:
    """In production every request comes through the Vercel proxy (CONTRACT §4)."""
    forwarded = request.headers.get("x-forwarded-for")
    if get_settings().is_production and forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(scope: str, key: str, rule: tuple[int, timedelta]) -> None:
    retry_after = limiter.hit(scope, key, *rule)
    if retry_after is not None:
        raise ApiError(429, "rate_limited", headers={"Retry-After": str(math.ceil(retry_after))})


def limit_login(request: Request) -> None:
    rate_limit("login", client_ip(request), RATE_LIMIT_LOGIN)


def limit_register(request: Request) -> None:
    rate_limit("register", client_ip(request), RATE_LIMIT_REGISTER)


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
