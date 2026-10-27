"""CSRF protection: unsafe methods need an allowed Origin or Referer (CONTRACT §4)."""

from fastapi.testclient import TestClient

from app.main import app

LOGOUT = "/api/v1/auth/logout"  # a POST that needs no database


def test_post_without_origin_is_forbidden() -> None:
    res = TestClient(app).post(LOGOUT)
    assert res.status_code == 403
    assert res.json()["code"] == "forbidden"
    assert isinstance(res.json()["detail"], str)


def test_post_with_wrong_origin_is_forbidden() -> None:
    res = TestClient(app).post(LOGOUT, headers={"Origin": "https://evil.example"})
    assert res.status_code == 403


def test_post_with_allowed_origin(origin: str) -> None:
    assert TestClient(app).post(LOGOUT, headers={"Origin": origin}).status_code == 204


def test_referer_used_when_origin_missing(origin: str) -> None:
    res = TestClient(app).post(LOGOUT, headers={"Referer": f"{origin}/login?next=/"})
    assert res.status_code == 204


def test_get_needs_no_origin() -> None:
    assert TestClient(app).get("/api/v1/health").status_code == 200


def test_no_cors_headers(origin: str) -> None:
    res = TestClient(app).get("/api/v1/health", headers={"Origin": origin})
    assert not any(h.lower().startswith("access-control-") for h in res.headers)
