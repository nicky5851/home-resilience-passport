"""Seam 4: login and cookies (CONTRACT §4), against the foundation stub."""

from app.config import AUTH_COOKIE_NAME

API = "/api/v1"
USER_KEYS = {"id", "email", "is_active", "is_superuser", "is_verified"}


def test_register_login_me_logout(client) -> None:
    res = client.post(
        f"{API}/auth/register",
        json={"email": "a@example.com", "password": "long-enough-pw", "accept_privacy": True},
    )
    assert res.status_code == 201
    assert set(res.json()) == USER_KEYS

    res = client.post(
        f"{API}/auth/login", data={"username": "a@example.com", "password": "long-enough-pw"}
    )
    assert res.status_code == 204
    cookie = res.headers["set-cookie"]
    assert cookie.startswith(f"{AUTH_COOKIE_NAME}=")
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie
    assert "Max-Age=604800" in cookie
    assert "Secure" not in cookie  # only when ENV=production

    res = client.get(f"{API}/users/me")
    assert res.status_code == 200
    assert res.json() == {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "a@example.com",
        "is_active": True,
        "is_superuser": False,
        "is_verified": False,
    }

    assert client.post(f"{API}/auth/logout").status_code == 204
    res = client.get(f"{API}/users/me")
    assert res.status_code == 401
    assert res.json() == {"detail": "Please log in to continue.", "code": "unauthorised"}


def test_register_requires_privacy(client) -> None:
    res = client.post(
        f"{API}/auth/register",
        json={"email": "a@example.com", "password": "long-enough-pw", "accept_privacy": False},
    )
    assert res.status_code == 400
    assert res.json()["code"] == "validation"


def test_login_is_form_encoded(client) -> None:
    res = client.post(f"{API}/auth/login", json={"username": "a@example.com", "password": "x"})
    assert res.status_code == 400
    assert res.json()["code"] == "validation"


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


def test_forgot_and_reset(client) -> None:
    assert client.post(f"{API}/auth/forgot-password", json={"email": "x@y.z"}).status_code == 202
    res = client.post(f"{API}/auth/reset-password", json={"token": "t", "password": "p" * 10})
    assert res.status_code == 200


def test_export_and_delete_account(user_client) -> None:
    res = user_client.get(f"{API}/users/me/export")
    assert res.status_code == 200
    assert res.headers["content-disposition"] == 'attachment; filename="hrp-export.json"'
    assert res.json()["user"]["email"] == "a@example.com"

    res = user_client.delete(f"{API}/users/me")
    assert res.status_code == 204
    assert f'{AUTH_COOKIE_NAME}=""' in res.headers["set-cookie"]
    assert user_client.get(f"{API}/users/me").status_code == 401
