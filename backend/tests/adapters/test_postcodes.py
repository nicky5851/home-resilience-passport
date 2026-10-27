"""N5: postcode lookup via postcodes.io, using recorded responses (no network)."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.adapters.cache import DbCache
from app.adapters.http import UpstreamUnavailable
from app.adapters.postcodes import PostcodeNotFound, lookup_postcode
from app.api.lookup import NOT_FOUND_DETAIL, UNSUPPORTED_REGION_DETAIL
from app.config import POSTCODE_CACHE_TTL
from app.db.session import make_sessionmaker
from app.schemas.api import PostcodeLookup
from tests.conftest import load_fixture

API = "/api/v1"
pytestmark = pytest.mark.anyio


# --- Adapter ------------------------------------------------------------------------------


async def test_england_postcode(postcodes_io, memory_cache) -> None:
    info = await lookup_postcode("SW1A 1AA", memory_cache)
    assert (info.lat, info.lon) == (51.50101, -0.141563)
    assert info.local_authority == "Westminster"
    assert (info.country, info.region) == ("england", "London")


async def test_wales_postcode(postcodes_io, memory_cache) -> None:
    info = await lookup_postcode("CF10 1EP", memory_cache)
    assert (info.local_authority, info.country, info.region) == ("Cardiff", "wales", "Wales")


async def test_unknown_postcode_not_found(postcodes_io, memory_cache) -> None:
    with pytest.raises(PostcodeNotFound):
        await lookup_postcode("ZZ99 9ZZ", memory_cache)
    assert memory_cache.rows == {}  # a miss is not cached


async def test_postcode_without_location_not_found(postcodes_io, memory_cache) -> None:
    postcodes_io.side_effect = None
    postcodes_io.return_value = httpx.Response(
        200, json={"status": 200, "result": {"latitude": None, "longitude": None}}
    )
    with pytest.raises(PostcodeNotFound):
        await lookup_postcode("SW1A 1AA", memory_cache)


@pytest.mark.parametrize(
    "failure",
    [httpx.ConnectTimeout("timed out"), httpx.ConnectError("offline"), httpx.Response(503)],
)
async def test_upstream_failure(postcodes_io, memory_cache, failure) -> None:
    postcodes_io.side_effect = None
    if isinstance(failure, Exception):
        postcodes_io.side_effect = failure
    else:
        postcodes_io.return_value = failure
    with pytest.raises(UpstreamUnavailable):
        await lookup_postcode("SW1A 1AA", memory_cache)


async def test_second_call_hits_the_cache(postcodes_io, memory_cache) -> None:
    first = await lookup_postcode("SW1A 1AA", memory_cache)
    second = await lookup_postcode("SW1A 1AA", memory_cache)
    assert first == second
    assert postcodes_io.call_count == 1


async def test_expired_cache_fetches_again(postcodes_io, memory_cache) -> None:
    await lookup_postcode("SW1A 1AA", memory_cache)
    value, _ = memory_cache.rows["postcodes.io:SW1A 1AA"]
    memory_cache.rows["postcodes.io:SW1A 1AA"] = (value, datetime.now(UTC) - timedelta(seconds=1))
    await lookup_postcode("SW1A 1AA", memory_cache)
    assert postcodes_io.call_count == 2


# --- Route ----------------------------------------------------------------------------------


def test_route_returns_real_location(client) -> None:
    res = client.get(f"{API}/lookup/postcode/sw1a1aa")
    assert res.status_code == 200
    body = PostcodeLookup.model_validate(res.json())
    assert body.postcode == "SW1A 1AA"
    assert (body.lat, body.lon, body.local_authority) == (51.50101, -0.141563, "Westminster")
    assert body.addresses == []


def test_route_english_border_postcode_is_supported(client) -> None:
    """TD15 (Berwick-upon-Tweed) is in England; the country comes from postcodes.io."""
    res = client.get(f"{API}/lookup/postcode/TD15 1AA")
    assert res.status_code == 200
    assert res.json()["local_authority"] == "Northumberland"


def test_route_wales_is_supported(client) -> None:
    assert client.get(f"{API}/lookup/postcode/CF10 1EP").status_code == 200


@pytest.mark.parametrize("pc", ["EH1 1YZ", "BT1 1AA"])
def test_route_scotland_ni_unsupported(client, pc: str) -> None:
    res = client.get(f"{API}/lookup/postcode/{pc}")
    assert res.status_code == 400
    assert res.json() == {"detail": UNSUPPORTED_REGION_DETAIL, "code": "unsupported_region"}


def test_route_unknown_postcode_is_validation(client) -> None:
    res = client.get(f"{API}/lookup/postcode/ZZ99 9ZZ")
    assert res.status_code == 400
    assert res.json() == {"detail": NOT_FOUND_DETAIL, "code": "validation"}


def test_route_offline_demo_postcode_uses_fixture(client, postcodes_io) -> None:
    postcodes_io.side_effect = httpx.ConnectError("offline")
    address = load_fixture("flood-terrace")["address"]
    res = client.get(f"{API}/lookup/postcode/{address['postcode']}")
    assert res.status_code == 200
    body = res.json()
    assert (body["lat"], body["lon"]) == (address["lat"], address["lon"])
    assert len(body["addresses"]) == 1


def test_route_offline_other_postcode_is_upstream_unavailable(client, postcodes_io) -> None:
    postcodes_io.side_effect = httpx.ConnectError("offline")
    res = client.get(f"{API}/lookup/postcode/SW1A 1AA")
    assert res.status_code == 502
    assert res.json()["code"] == "upstream_unavailable"


# --- The api_cache table ----------------------------------------------------------------------


async def test_db_cache_round_trip_and_expiry(engine) -> None:
    async with make_sessionmaker(engine)() as s:
        cache = DbCache(s)
        await cache.put("test:a", "test", {"x": 1}, POSTCODE_CACHE_TTL)
        await cache.put("test:a", "test", {"x": 2}, POSTCODE_CACHE_TTL)  # upsert
        assert await cache.get("test:a") == {"x": 2}
        await cache.put("test:b", "test", {"x": 3}, timedelta(seconds=-1))
        assert await cache.get("test:b") is None


async def test_db_cache_down_is_a_miss_not_an_error() -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine("postgresql+asyncpg://hrp:hrp@127.0.0.1:1/none")
    try:
        async with make_sessionmaker(engine)() as s:
            cache = DbCache(s)
            assert await cache.get("test:a") is None
            await cache.put("test:a", "test", {"x": 1}, POSTCODE_CACHE_TTL)
    finally:
        await engine.dispose()


async def test_db_cache_survives_parallel_use(engine, caplog) -> None:
    """Adapters share one request's cache under asyncio.gather (found in the N8 live check)."""
    import asyncio

    async with make_sessionmaker(engine)() as s:
        cache = DbCache(s)
        await asyncio.gather(
            *(cache.put(f"test:p{i}", "test", {"i": i}, POSTCODE_CACHE_TTL) for i in range(5))
        )
        got = await asyncio.gather(*(cache.get(f"test:p{i}") for i in range(5)))
    assert got == [{"i": i} for i in range(5)]
    assert "api_cache" not in caplog.text
