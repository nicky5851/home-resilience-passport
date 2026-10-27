"""fastapi-users wiring: user store, user manager and JWT strategy (spec N10, CONTRACT §4).

The user store is our own five-method adapter over `app.db.models.User`, not
fastapi-users-db-sqlalchemy, which pins SQLAlchemy below 2.1.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import Request
from fastapi_users import BaseUserManager, InvalidPasswordException, UUIDIDMixin, schemas
from fastapi_users.authentication import JWTStrategy
from fastapi_users.db import BaseUserDatabase
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AUTH_COOKIE_LIFETIME, PASSWORD_MIN_LENGTH, RESET_PASSWORD_PATH, get_settings
from app.db.models import User

log = logging.getLogger(__name__)


class NewUser(schemas.BaseUserCreate):
    """What register stores: fastapi-users' fields plus the privacy acceptance."""

    privacy_accepted_at: datetime
    privacy_version: str


class UserStore(BaseUserDatabase[User, uuid.UUID]):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id: uuid.UUID) -> User | None:
        return await self.session.get(User, id)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(func.lower(User.email) == email.strip().lower())
        return await self.session.scalar(stmt)

    async def create(self, create_dict: dict[str, Any]) -> User:
        user = User(**create_dict)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update(self, user: User, update_dict: dict[str, Any]) -> User:
        for key, value in update_dict.items():
            setattr(user, key, value)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        """Homes and everything hanging off them go with it (ON DELETE CASCADE)."""
        await self.session.delete(user)
        await self.session.commit()


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    def __init__(self, store: UserStore) -> None:
        super().__init__(store)
        secret = get_settings().auth_secret
        self.reset_password_token_secret = secret
        self.verification_token_secret = secret

    async def validate_password(self, password: str, user: Any) -> None:
        """CONTRACT §4: at least 10 characters and not the email address."""
        if len(password) < PASSWORD_MIN_LENGTH:
            raise InvalidPasswordException(
                f"Your password needs at least {PASSWORD_MIN_LENGTH} characters."
            )
        if password.strip().lower() == user.email.strip().lower():
            raise InvalidPasswordException("Your password can't be your email address.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Request | None = None
    ) -> None:
        settings = get_settings()
        if settings.resend_api_key:
            log.warning("Password reset requested; email delivery arrives in M2, link not sent")
            return
        # M1 (CONTRACT §4): the link goes to the API log for N to pass on. No email or name.
        link = f"{settings.next_public_app_url.rstrip('/')}{RESET_PASSWORD_PATH}?token={token}"
        log.warning("Password reset link for user %s: %s", user.id, link)


def jwt_strategy() -> JWTStrategy[User, uuid.UUID]:
    return JWTStrategy(
        secret=get_settings().auth_secret,
        lifetime_seconds=int(AUTH_COOKIE_LIFETIME.total_seconds()),
    )
