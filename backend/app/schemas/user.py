from uuid import UUID

from app.schemas.base import Contract


class UserRead(Contract):
    """fastapi-users' default user shape (CONTRACT §4)."""

    id: UUID
    email: str
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False


class UserCreate(Contract):
    email: str
    password: str
    accept_privacy: bool  # must be true; checked by the register route
