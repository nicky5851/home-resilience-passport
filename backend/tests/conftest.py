import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "demo_homes"
RECORDED_DIR = Path(__file__).parent / "adapters" / "recorded"
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


class MemoryCache:
    """Stands in for the `api_cache` table so API tests need no Postgres."""

    def __init__(self) -> None:
        self.rows: dict[str, tuple[dict, datetime]] = {}

    async def get(self, key: str) -> dict | None:
        value, expires_at = self.rows.get(key, (None, None))
        return value if expires_at and expires_at > datetime.now(UTC) else None

    async def put(self, key: str, source: str, value: dict, ttl: timedelta) -> None:
        self.rows[key] = (value, datetime.now(UTC) + ttl)


@pytest.fixture
def memory_cache() -> MemoryCache:
    return MemoryCache()


@pytest.fixture
def mock_http():
    """Every outbound request must match a mocked route, so tests never touch the network."""
    import respx

    with respx.mock(assert_all_called=False) as router:
        yield router


@pytest.fixture
def postcodes_io(mock_http):
    """postcodes.io answered from recorded responses (unrecorded postcodes get its 404)."""
    import httpx

    from app.adapters.postcodes import POSTCODES_IO_URL

    def answer(request: httpx.Request) -> httpx.Response:
        compact = request.url.path.rsplit("/", 1)[-1].upper()
        path = RECORDED_DIR / "postcodes" / f"{compact}.json"
        if not path.exists():
            path = RECORDED_DIR / "postcodes" / "ZZ999ZZ.json"
        body = json.loads(path.read_text())
        return httpx.Response(body["status"], json=body)

    return mock_http.get(url__startswith=POSTCODES_IO_URL).mock(side_effect=answer)


@pytest.fixture
def epc_api(mock_http, monkeypatch):
    """The EPC register with a test token; answers 404 (nothing registered) unless a test
    sets `side_effect` or `return_value`."""
    import httpx

    from app.config import EPC_API_LIVE_URL, get_settings

    monkeypatch.setattr(get_settings(), "epc_api_token", "test-token")
    monkeypatch.setattr(get_settings(), "epc_api_base_url", EPC_API_LIVE_URL)
    return mock_http.get(url__startswith=EPC_API_LIVE_URL).mock(
        return_value=httpx.Response(404, json={"error": "No certificates found"})
    )


@pytest.fixture
def offline_hazards(mock_http):
    """Open-Meteo and the EA warnings feed unreachable: the pipeline's own fallbacks answer."""
    import httpx

    from app.adapters.climate import CLIMATE_URL
    from app.adapters.flood import FLOOD_WARNINGS_URL

    for url in (CLIMATE_URL, FLOOD_WARNINGS_URL):
        mock_http.get(url__startswith=url).mock(side_effect=httpx.ConnectError("offline"))


PASSWORD = "long-enough-pw"


def log_in(client, email: str, password: str = PASSWORD) -> None:
    """Register (if needed) and log in, so `client` carries that user's cookie."""
    body = {"email": email, "password": password, "accept_privacy": True}
    assert client.post("/api/v1/auth/register", json=body).status_code in (201, 409)
    res = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert res.status_code == 204, res.text


USER_TABLES = ("users", "homes", "households", "assessments", "plans", "passport_events",
               "work_files", "share_links")  # fmt: skip


@pytest.fixture(scope="session")
def seeded(db_url: str) -> str:
    """The test database with A's reference CSVs loaded (`make seed`), once per session."""
    import asyncio

    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    from app.db.seed import seed

    async def run() -> None:
        eng = create_async_engine(db_url, poolclass=NullPool)
        try:
            await seed(eng)
        finally:
            await eng.dispose()

    asyncio.run(run())
    return db_url


@pytest.fixture
def client(
    origin: str,
    seeded: str,
    db_url: str,
    memory_cache: MemoryCache,
    postcodes_io,
    epc_api,
    offline_hazards,
):
    """A logged-out client that sends an allowed Origin on every request.

    Accounts and homes live in the `_test` database, emptied before each test; the API cache is
    in memory. Reference data is seeded; `flood_postcodes` is empty, so flood bands are unknown."""
    import asyncio

    from fastapi.testclient import TestClient
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    from app.api.deps import get_api_cache
    from app.core.ratelimit import limiter
    from app.db.session import get_session, make_sessionmaker
    from app.main import app

    eng = create_async_engine(db_url, poolclass=NullPool)

    async def empty() -> None:
        async with eng.begin() as conn:
            await conn.execute(text(f"TRUNCATE {', '.join(USER_TABLES)}, llm_cache CASCADE"))

    async def test_session():
        async with make_sessionmaker(eng)() as s:
            yield s

    asyncio.run(empty())
    limiter.reset()
    app.dependency_overrides[get_api_cache] = lambda: memory_cache
    app.dependency_overrides[get_session] = test_session
    try:
        with TestClient(app, headers={"Origin": origin}) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_api_cache, None)
        app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def user_client(client):
    """A client logged in as a@example.com."""
    log_in(client, "a@example.com")
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


@pytest.fixture(autouse=True)
def upload_dir(tmp_path, monkeypatch) -> Path:
    """Certificates go to a temporary folder, never `backend/uploads/` (spec N14)."""
    from app.services import storage

    root = tmp_path / "uploads"
    monkeypatch.setattr(storage, "UPLOAD_DIR", root)
    storage.get_storage.cache_clear()
    yield root
    storage.get_storage.cache_clear()
