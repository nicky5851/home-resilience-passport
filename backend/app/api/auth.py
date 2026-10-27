"""Auth and account routes. Foundation stub until N10 (CONTRACT §4)."""

import json
from typing import Annotated

from fastapi import APIRouter, Form, Response, status

from app.api.deps import STUB_COOKIE_PREFIX, CurrentUser, clear_auth_cookie, set_auth_cookie
from app.api.errors import ApiError
from app.api.stub_store import STUB_USER_ID, store
from app.schemas import UserCreate, UserRead
from app.schemas.api import ForgotPassword, ResetPassword

auth = APIRouter(prefix="/auth", tags=["auth"])
users = APIRouter(prefix="/users", tags=["users"])


@auth.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: UserCreate) -> UserRead:
    if not body.accept_privacy:
        raise ApiError(400, "validation", "Please confirm you have read the privacy notice.")
    if not body.email.strip():
        raise ApiError(400, "validation", "Please enter your email address.")
    return UserRead(id=STUB_USER_ID, email=body.email.strip())


@auth.post("/login", status_code=status.HTTP_204_NO_CONTENT)
def login(
    username: Annotated[str, Form()], password: Annotated[str, Form()], response: Response
) -> None:
    if not username.strip() or not password:
        raise ApiError(400, "validation", "Email or password is incorrect")
    set_auth_cookie(response, f"{STUB_COOKIE_PREFIX}{username.strip()}")


@auth.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_auth_cookie(response)


@auth.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(body: ForgotPassword) -> None:
    # Always 202: never reveals whether the email exists.
    return None


@auth.post("/reset-password")
def reset_password(body: ResetPassword) -> None:
    if not body.token:
        raise ApiError(400, "validation", "This reset link is not valid. Please ask for a new one.")
    return None


@users.get("/me")
def me(user: CurrentUser) -> UserRead:
    return user


@users.get(
    "/me/export",
    responses={200: {"description": "JSON file with everything the user owns"}},
)
def export(user: CurrentUser) -> Response:
    homes = [store.passport(h).model_dump(mode="json") for h in store.owned_by(user.email)]
    body = {"user": user.model_dump(mode="json"), "homes": homes}
    return Response(
        content=json.dumps(body, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="hrp-export.json"'},
    )


@users.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(user: CurrentUser, response: Response) -> None:
    store.delete_user(user.email)
    clear_auth_cookie(response)
