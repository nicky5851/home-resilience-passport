"""Seam 4: login and cookies (CONTRACT §4), with real accounts (spec N10)."""

import asyncio
import logging
import re
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.config import (
    AUTH_COOKIE_NAME,
    DEV_AUTH_SECRET,
    PRIVACY_VERSION,
    RESET_PASSWORD_PATH,
    Settings,
)
from app.db.models import User
from tests.conftest import PASSWORD, USER_TABLES, load_fixture, log_in

API = "/api/v1"
USER_KEYS = {"id", "email", "is_active", "is_superuser", "is_verified"}


def _register(client, email: str = "a@example.com", password: str = PASSWORD, **extra):
    body = {"email": email, "password": password, "accept_privacy": True} | extra
    return client.post(f"{API}/auth/register", json=body)


def _login(client, email: str = "a@example.com", password: str = PASSWORD):
    return client.post(f"{API}/auth/login", data={"username": email, "password": password})


def _db(db_url: str, stmt):
    """Run one statement against the test database from a sync test."""

    async def run():
        eng = create_async_engine(db_url, poolclass=NullPool)
        try:
            async with eng.begin() as conn:
                result = await conn.execute(stmt)
                return result.all() if result.returns_rows else None
        finally:
            await eng.dispose()

    return asyncio.run(run())


# --- Register, login, me, logout ---------------------------------------------------------------


def test_register_login_me_logout(client, db_url) -> None:
    res = _register(client)
    assert res.status_code == 201
    assert set(res.json()) == USER_KEYS
    user_id = res.json()["id"]

    res = _login(client)
    assert res.status_code == 204
    cookie = res.headers["set-cookie"]
    assert cookie.startswith(f"{AUTH_COOKIE_NAME}=")
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie
    assert "Max-Age=604800" in cookie
    assert "Secure" not in cookie  # only when ENV=production

    res = client.get(f"{API}/users/me")
    assert res.status_code == 200
    assert res.json() == {
        "id": user_id,
        "email": "a@example.com",
        "is_active": True,
        "is_superuser": False,
        "is_verified": False,
    }

    assert client.post(f"{API}/auth/logout").status_code == 204
    res = client.get(f"{API}/users/me")
    assert res.status_code == 401
    assert res.json() == {"detail": "Please log in to continue.", "code": "unauthorised"}


def test_privacy_acceptance_is_stored(client, db_url) -> None:
    _register(client)
    ((accepted, version, hashed),) = _db(
        db_url, select(User.privacy_accepted_at, User.privacy_version, User.hashed_password)
    )
    assert accepted is not None and version == PRIVACY_VERSION
    assert PASSWORD not in hashed  # hashed, never stored as typed


def test_register_requires_privacy(client) -> None:
    res = _register(client, accept_privacy=False)
    assert res.status_code == 400
    assert res.json()["code"] == "validation"


@pytest.mark.parametrize(
    ("email", "password", "detail"),
    [
        ("a@example.com", "short", "Your password needs at least 10 characters."),
        ("longer@example.com", "LONGER@example.com", "Your password can't be your email address."),
        ("not-an-email", PASSWORD, "Please enter a valid email address."),
    ],
)
def test_register_rejects(client, email, password, detail) -> None:
    res = _register(client, email, password)
    assert (res.status_code, res.json()) == (400, {"detail": detail, "code": "validation"})


def test_duplicate_email_is_conflict(client) -> None:
    _register(client)
    res = _register(client, "A@Example.com")
    assert res.status_code == 409
    assert res.json()["code"] == "conflict"


@pytest.mark.parametrize(
    ("email", "password"), [("a@example.com", "wrong-password"), ("nobody@example.com", PASSWORD)]
)
def test_bad_login_is_one_message(client, email, password) -> None:
    _register(client)
    res = _login(client, email, password)
    assert res.status_code == 400
    assert res.json() == {"detail": "Email or password is incorrect", "code": "validation"}


def test_login_is_case_insensitive_on_email(client) -> None:
    _register(client)
    assert _login(client, " A@EXAMPLE.com ").status_code == 204


def test_login_is_form_encoded(client) -> None:
    res = client.post(f"{API}/auth/login", json={"username": "a@example.com", "password": "x"})
    assert res.status_code == 400
    assert res.json()["code"] == "validation"


@pytest.mark.parametrize("cookie", ["stub-a@example.com", "not.a.jwt", ""])
def test_old_or_forged_cookies_are_rejected(client, cookie) -> None:
    _register(client)
    client.cookies.set(AUTH_COOKIE_NAME, cookie)
    assert client.get(f"{API}/users/me").status_code == 401


def test_protected_routes_need_login(client) -> None:
    home = "00000000-0000-0000-0000-000000000000"
    for method, path in [
        ("GET", "/users/me"),
        ("GET", "/users/me/export"),
        ("DELETE", "/users/me"),
        ("GET", "/homes"),
        ("POST", f"/homes/{home}/assess"),
        ("GET", f"/homes/{home}/passport"),
    ]:
        res = client.request(method, f"{API}{path}")
        assert res.status_code == 401, path
        assert res.json()["code"] == "unauthorised"


def test_last_seen_is_updated_at_most_once_a_day(user_client, db_url) -> None:
    def last_seen():
        return _db(db_url, select(User.last_seen_at))[0][0]

    user_client.get(f"{API}/users/me")
    first = last_seen()
    assert first is not None
    user_client.get(f"{API}/users/me")
    assert last_seen() == first

    two_days_ago = datetime.now(UTC) - timedelta(days=2)
    _db(db_url, update(User).values(last_seen_at=two_days_ago))
    user_client.get(f"{API}/users/me")
    assert last_seen() > two_days_ago + timedelta(days=1)


# --- Forgot and reset password ---------------------------------------------------------------


def test_forgot_password_never_reveals_the_email(client) -> None:
    assert client.post(f"{API}/auth/forgot-password", json={"email": "x@y.z"}).status_code == 202


def test_forgot_and_reset(client, caplog) -> None:
    _register(client)
    with caplog.at_level(logging.WARNING, logger="app.auth.users"):
        res = client.post(f"{API}/auth/forgot-password", json={"email": "a@example.com"})
    assert res.status_code == 202
    assert "a@example.com" not in caplog.text  # nothing personal in logs (CONTRACT §6)
    token = re.search(rf"{RESET_PASSWORD_PATH}\?token=(\S+)", caplog.text).group(1)

    res = client.post(f"{API}/auth/reset-password", json={"token": token, "password": "short"})
    assert res.json()["detail"] == "Your password needs at least 10 characters."
    new = "a-brand-new-password"
    res = client.post(f"{API}/auth/reset-password", json={"token": token, "password": new})
    assert res.status_code == 200
    assert _login(client).status_code == 400
    assert _login(client, password=new).status_code == 204


def test_reset_with_a_bad_token(client) -> None:
    res = client.post(f"{API}/auth/reset-password", json={"token": "t", "password": "p" * 10})
    assert res.status_code == 400
    assert res.json() == {
        "detail": "This reset link is not valid. Please ask for a new one.",
        "code": "validation",
    }


# --- Rate limits (CONTRACT §3) ---------------------------------------------------------------


def test_sixth_login_in_a_minute_is_429(client) -> None:
    _register(client)
    for _ in range(5):
        assert _login(client, password="wrong-password").status_code == 400
    res = _login(client)
    assert res.status_code == 429
    assert res.json()["code"] == "rate_limited"
    assert 0 < int(res.headers["retry-after"]) <= 60


def test_eleventh_registration_in_an_hour_is_429(client) -> None:
    for i in range(10):
        assert _register(client, f"user{i}@example.com").status_code == 201
    res = _register(client, "user10@example.com")
    assert res.status_code == 429
    assert int(res.headers["retry-after"]) > 60 * 59


def test_assess_is_limited_per_user(user_client, monkeypatch) -> None:
    from app.api import homes

    monkeypatch.setattr(homes, "RATE_LIMIT_ASSESS", (2, timedelta(hours=1)))
    home = load_fixture("flood-terrace")["passport"]["home_id"]
    assert [user_client.post(f"{API}/homes/{home}/assess").status_code for _ in range(3)] == [
        200,
        200,
        429,
    ]
    log_in(user_client, "b@example.com")  # another user has their own allowance
    assert user_client.post(f"{API}/homes/{home}/assess").status_code == 200


def test_forwarded_ip_is_used_only_in_production(monkeypatch) -> None:
    from starlette.requests import Request

    from app.api.deps import client_ip
    from app.config import get_settings

    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"203.0.113.9, 10.0.0.1")],
        "client": ("10.0.0.1", 1234),
    }
    assert client_ip(Request(scope)) == "10.0.0.1"
    monkeypatch.setattr(get_settings(), "env", "production")
    assert client_ip(Request(scope)) == "203.0.113.9"


def test_production_refuses_the_dev_secret() -> None:
    # Pass the dev secret explicitly: an ambient AUTH_SECRET env var (e.g. CI's) would
    # otherwise override the field default and defeat this test.
    with pytest.raises(ValueError, match="AUTH_SECRET"):
        Settings(env="production", auth_secret=DEV_AUTH_SECRET, _env_file=None)
    Settings(env="production", auth_secret="x" * 40, _env_file=None)


# --- Export and delete (CONTRACT §4) -----------------------------------------------------------


def _new_home(client, slug: str = "flood-terrace") -> str:
    f = load_fixture(slug)
    body = {"address": f["address"], "household": f["household"], "property_override": None}
    res = client.post(f"{API}/homes", json=body)
    assert res.status_code == 201, res.text
    return res.json()["home_id"]


def _full_home(client) -> str:
    home_id = _new_home(client)
    assert client.post(f"{API}/homes/{home_id}/assess").status_code == 200
    assert client.post(f"{API}/homes/{home_id}/share").status_code == 200
    return home_id


def test_export_contains_the_users_homes(user_client) -> None:
    home_id = _full_home(user_client)
    res = user_client.get(f"{API}/users/me/export")
    assert res.status_code == 200
    assert res.headers["content-disposition"] == 'attachment; filename="hrp-export.json"'
    body = res.json()
    assert body["user"]["email"] == "a@example.com"
    assert body["user"]["privacy_version"] == PRIVACY_VERSION
    assert "hashed_password" not in body["user"]
    (home,) = body["homes"]
    assert home["passport"]["home_id"] == home_id
    assert home["passport"]["household"]["tenure"]
    assert home["passport"]["share_token"]
    assert [e["kind"] for e in home["passport"]["events"]] == ["assessed", "shared"]
    assert len(home["assessments"]) == 1


def _counts(db_url: str) -> dict[str, int]:
    return {t: _db(db_url, text(f"SELECT count(*) FROM {t}"))[0][0] for t in USER_TABLES}


def test_delete_account_removes_every_row(client, db_url) -> None:
    log_in(client, "keep@example.com")
    _full_home(client)
    others = _counts(db_url)

    log_in(client, "a@example.com")
    _full_home(client)
    _full_home(client)
    before = _counts(db_url)
    assert before["homes"] == others["homes"] + 2

    res = client.delete(f"{API}/users/me")
    assert res.status_code == 204
    assert f'{AUTH_COOKIE_NAME}=""' in res.headers["set-cookie"]
    assert _counts(db_url) == others  # every row of a@ gone, keep@ untouched
    assert _login(client).status_code == 400
    assert _db(db_url, select(func.count()).select_from(User))[0][0] == 1
