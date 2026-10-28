"""Auth and account routes (spec N10, CONTRACT §4): fastapi-users behind our own routes.

The routes keep the foundation stub's paths, bodies and responses, so `docs/openapi.json` and
the front end do not change. fastapi-users errors become CONTRACT §3 errors here.
"""

import json
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users import exceptions
from pydantic import ValidationError
from sqlalchemy import select

from app.api.deps import (
    CurrentUserRow,
    SessionDep,
    UserManagerDep,
    clear_auth_cookie,
    limit_login,
    limit_register,
    set_auth_cookie,
    user_read,
)
from app.api.errors import ApiError
from app.api.stub_store import store
from app.auth.users import NewUser, jwt_strategy
from app.config import PRIVACY_VERSION
from app.db import models as db
from app.schemas import UserCreate, UserRead
from app.schemas.api import ForgotPassword, ResetPassword
from app.services import homes

auth = APIRouter(prefix="/auth", tags=["auth"])
users = APIRouter(prefix="/users", tags=["users"])

BAD_LOGIN = "Email or password is incorrect"  # CONTRACT §4, word for word
BAD_RESET = "This reset link is not valid. Please ask for a new one."


@auth.post("/register", status_code=status.HTTP_201_CREATED, dependencies=[Depends(limit_register)])
async def register(body: UserCreate, manager: UserManagerDep, request: Request) -> UserRead:
    if not body.accept_privacy:
        raise ApiError(400, "validation", "Please confirm you have read the privacy notice.")
    try:
        new = NewUser(
            email=body.email.strip(),
            password=body.password,
            privacy_accepted_at=datetime.now(UTC),
            privacy_version=PRIVACY_VERSION,
        )
    except ValidationError as e:
        raise ApiError(400, "validation", "Please enter a valid email address.") from e
    try:
        user = await manager.create(new, safe=True, request=request)
    except exceptions.UserAlreadyExists as e:
        raise ApiError(409, "conflict", "An account with this email already exists.") from e
    except exceptions.InvalidPasswordException as e:
        raise ApiError(400, "validation", str(e.reason)) from e
    return user_read(user)


@auth.post("/login", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(limit_login)])
async def login(
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    response: Response,
    manager: UserManagerDep,
) -> None:
    credentials = OAuth2PasswordRequestForm(username=username.strip(), password=password)
    user = await manager.authenticate(credentials)
    if user is None or not user.is_active:
        raise ApiError(400, "validation", BAD_LOGIN)
    set_auth_cookie(response, await jwt_strategy().write_token(user))


@auth.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_auth_cookie(response)


@auth.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(body: ForgotPassword, manager: UserManagerDep, request: Request) -> None:
    # Always 202: never reveals whether the email exists.
    try:
        user = await manager.get_by_email(body.email)
        await manager.forgot_password(user, request)
    except (exceptions.UserNotExists, exceptions.UserInactive):
        pass


@auth.post("/reset-password")
async def reset_password(body: ResetPassword, manager: UserManagerDep, request: Request) -> None:
    try:
        await manager.reset_password(body.token, body.password, request)
    except (
        exceptions.InvalidResetPasswordToken,
        exceptions.UserNotExists,
        exceptions.UserInactive,
    ) as e:
        raise ApiError(400, "validation", BAD_RESET) from e
    except exceptions.InvalidPasswordException as e:
        raise ApiError(400, "validation", str(e.reason)) from e


@users.get("/me")
def me(user: CurrentUserRow) -> UserRead:
    return user_read(user)


@users.get(
    "/me/export",
    responses={200: {"description": "JSON file with everything the user owns"}},
)
async def export(user: CurrentUserRow, session: SessionDep) -> Response:
    # Right of access (CONTRACT §4): every row the user owns. Certificates by name only.
    body = {
        "user": user_read(user).model_dump(mode="json")
        | {
            "created_at": _iso(user.created_at),
            "last_seen_at": _iso(user.last_seen_at),
            "privacy_accepted_at": _iso(user.privacy_accepted_at),
            "privacy_version": user.privacy_version,
        },
        "homes": [await _export_home(session, h) for h in await homes.owned_by(session, user.id)],
    }
    return Response(
        content=json.dumps(body, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="hrp-export.json"'},
    )


async def _export_home(session: SessionDep, home: Any) -> dict[str, Any]:
    assessments = await session.scalars(
        select(db.Assessment)
        .where(db.Assessment.home_id == home.home_id)
        .order_by(db.Assessment.created_at)
    )
    plans = await session.scalars(
        select(db.SavedPlan)
        .where(db.SavedPlan.home_id == home.home_id)
        .order_by(db.SavedPlan.created_at)
    )
    return {
        "passport": store.passport(home).model_dump(mode="json"),
        "assessments": [
            {
                "created_at": _iso(a.created_at),
                "scoring_version": a.scoring_version,
                "inputs": a.inputs,
                "risk": a.risk,
                "score": a.score,
            }
            for a in assessments.all()
        ],
        "plans": [
            {"created_at": _iso(p.created_at), "budget_gbp": p.budget_gbp, "plan": p.plan}
            for p in plans.all()
        ],
    }


def _iso(at: datetime | None) -> str | None:
    return None if at is None else at.astimezone(UTC).isoformat().replace("+00:00", "Z")


@users.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    user: CurrentUserRow, manager: UserManagerDep, session: SessionDep, response: Response
) -> None:
    # Right to erasure: the user row goes, and every home with everything hanging off it
    # (ON DELETE CASCADE). In-memory certificates are dropped first.
    for home in await homes.owned_by(session, user.id):
        homes.forget_certificates(home)
    await manager.delete(user)
    clear_auth_cookie(response)
