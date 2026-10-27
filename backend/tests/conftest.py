import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "demo_homes"
DEMO_SLUGS = ("flood-terrace", "coastal-bungalow", "city-top-flat", "clay-semi", "rural-cottage")


def load_fixture(slug: str) -> dict:
    return json.loads((FIXTURES_DIR / f"{slug}.json").read_text())


@pytest.fixture(params=DEMO_SLUGS)
def demo_fixture(request: pytest.FixtureRequest) -> dict:
    return load_fixture(request.param)


@pytest.fixture
def origin() -> str:
    from app.config import get_settings

    return get_settings().allowed_origin_list[0]


@pytest.fixture
def client(origin: str):
    """A logged-out client that sends an allowed Origin on every request."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app, headers={"Origin": origin}) as c:
        yield c


@pytest.fixture
def user_client(client):
    """A client logged in through the auth stub."""
    res = client.post("/api/v1/auth/login", data={"username": "a@example.com", "password": "x"})
    assert res.status_code == 204
    return client
