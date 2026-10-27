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


# --- Database (tests that need Postgres) --------------------------------------------------


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


def _test_database_url() -> str:
    from app.config import get_settings

    base, _, name = get_settings().database_url.rpartition("/")
    return f"{base}/{name}_test"


async def _recreate_database(url: str) -> None:
    import asyncpg

    base, _, name = url.replace("+asyncpg", "").rpartition("/")
    conn = await asyncpg.connect(f"{base}/postgres", timeout=3)
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{name}"')
    finally:
        await conn.close()


def alembic_config(url: str):
    from alembic.config import Config

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.attributes["url"] = url
    cfg.attributes["configure_logger"] = False
    return cfg


@pytest.fixture(scope="session")
def db_url() -> str:
    """A fresh `<name>_test` database migrated to head. Skips locally if Postgres is down."""
    import asyncio
    import os

    from alembic import command

    url = _test_database_url()
    try:
        asyncio.run(_recreate_database(url))
    except (OSError, TimeoutError) as e:
        if os.environ.get("CI"):
            raise
        pytest.skip(f"Postgres is not running ({type(e).__name__}); start it with `make db`")
    command.upgrade(alembic_config(url), "head")
    return url


@pytest.fixture
async def engine(db_url: str):
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    eng = create_async_engine(db_url, poolclass=NullPool)
    yield eng
    await eng.dispose()
