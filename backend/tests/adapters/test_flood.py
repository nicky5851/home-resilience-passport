"""N7: RoFRS loader and band lookup, EA live warnings (offline).

recorded/flood/ holds EA flood-monitoring responses recorded on 2026-10-27: York (none in force)
and a slice of the England-wide feed with severity levels 2, 3 and 4.
"""

import csv
import io
import json
import zipfile

import httpx
import pytest

from app.adapters import flood
from app.db.load_rofrs import BAND_COLUMNS, RofrsError, load, read_bands
from app.db.session import make_sessionmaker
from tests.conftest import RECORDED_DIR

pytestmark = pytest.mark.anyio
FLOOD_DIR = RECORDED_DIR / "flood"
HEADER = ["PC", "cntpc", *(col for _, col in BAND_COLUMNS), "SORTOFF", "DISTRICT"]


def _zip(tmp_path, rows: list[list], header: list[str] = HEADER):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    path = tmp_path / "rofrs.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("RoFRS_Postcodes_in_Areas_at_Risk/DATA/postcodes.csv", "﻿" + buf.getvalue())
        z.writestr("RoFRS_Postcodes_in_Areas_at_Risk/SUPPORTING_DOCUMENTS/readme.pdf", b"%PDF")
    return path


# --- Loader ---------------------------------------------------------------------------------
# Band columns in HEADER order: High, Medium, Low, VeryLow.


def test_read_bands_takes_highest_band_with_properties(tmp_path) -> None:
    path = _zip(
        tmp_path,
        [
            ["YO1 9TJ", 50, 3, 46, 1, 0, "YO", 1],  # as in the real file → high
            ["DN14 6ST", 57, 0, 34, 0, 0, "DN", 14],
            ["NG23 7HA", 49, 0, 0, 42, 4, "NG", 23],
            ["SW1A 1AA", 1, 0, 0, 0, 1, "SW", 1],
            ["sw1a2aa", 1, 0, 0, 0, 1, "SW", 1],  # normalised
            ["VPO01148", 1, 0, 0, 0, 0, "", ""],  # pseudo-postcode, skipped
            ["VE03443", 1, 0, 0, 1, 0, "VE", "03"],  # pseudo-postcode with a band, skipped
            ["HD6 1AB", 7, 0, 0, 0, 0, "HD", 6],  # no band, skipped
        ],
    )
    assert read_bands(path) == {
        "YO1 9TJ": "high",
        "DN14 6ST": "medium",
        "NG23 7HA": "low",
        "SW1A 1AA": "very_low",
        "SW1A 2AA": "very_low",
    }


def test_read_bands_refuses_missing_columns(tmp_path) -> None:
    path = _zip(tmp_path, [["YO1 9TJ", 1]], header=["PC", "cntpc"])
    with pytest.raises(RofrsError, match="TOT_CNT_High"):
        read_bands(path)


# --- Band lookup (Postgres) -------------------------------------------------------------------


@pytest.fixture
async def loaded(engine):
    await load(engine, {"YO1 9TJ": "high", "DN14 6ST": "medium", "SW1A 1AA": "very_low"})
    yield engine
    await load(engine, {})


@pytest.mark.parametrize(
    ("postcode", "expected"),
    [("YO1 9TJ", "high"), ("DN14 6ST", "medium"), ("SW1A 1AA", "very_low"), ("SK17 0SN", "none")],
)
async def test_band_lookup(loaded, postcode, expected) -> None:
    async with make_sessionmaker(loaded)() as s:
        assert await flood.rofrs_band(postcode, "england", s) == expected


async def test_reload_replaces_the_table(loaded) -> None:
    assert await load(loaded, {"TR18 3JA": "low"}) == 1
    async with make_sessionmaker(loaded)() as s:
        assert await flood.rofrs_band("YO1 9TJ", "england", s) == "none"
        assert await flood.rofrs_band("TR18 3JA", "england", s) == "low"


async def test_wales_is_unknown(loaded) -> None:
    async with make_sessionmaker(loaded)() as s:
        assert await flood.rofrs_band("CF10 1EP", "wales", s) is None


async def test_empty_table_is_unknown_not_none(engine) -> None:
    """Never claim 'not at risk' because the data was not loaded."""
    await load(engine, {})
    async with make_sessionmaker(engine)() as s:
        assert await flood.rofrs_band("YO1 9TJ", "england", s) is None


async def test_database_down_is_unknown() -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine("postgresql+asyncpg://hrp:hrp@127.0.0.1:1/none")
    try:
        async with make_sessionmaker(engine)() as s:
            assert await flood.rofrs_band("YO1 9TJ", "england", s) is None
    finally:
        await engine.dispose()


# --- Live warnings ----------------------------------------------------------------------------


@pytest.fixture
def ea_floods(mock_http):
    return mock_http.get(url__startswith=flood.FLOOD_WARNINGS_URL)


def _recorded(name: str) -> httpx.Response:
    return httpx.Response(200, json=json.loads((FLOOD_DIR / f"{name}.json").read_text()))


async def test_no_warnings(ea_floods, memory_cache) -> None:
    ea_floods.mock(return_value=_recorded("floods_york"))
    assert await flood.active_flood_warnings(53.957, -1.077, memory_cache) == 0


async def test_counts_only_warnings_in_force(ea_floods, memory_cache) -> None:
    ea_floods.mock(return_value=_recorded("floods_mixed"))  # levels 2, 2, 3, 3, 4, 4
    assert await flood.active_flood_warnings(51.5, -0.14, memory_cache) == 4


async def test_request_uses_5_km_radius(ea_floods, memory_cache) -> None:
    ea_floods.mock(return_value=_recorded("floods_york"))
    await flood.active_flood_warnings(53.957, -1.077, memory_cache)
    params = ea_floods.calls.last.request.url.params
    assert (params["lat"], params["long"], params["dist"]) == ("53.957", "-1.077", "5")


async def test_count_is_capped_at_50(ea_floods, memory_cache) -> None:
    item = json.loads((FLOOD_DIR / "floods_mixed.json").read_text())["items"][0]
    ea_floods.mock(return_value=httpx.Response(200, json={"items": [item] * 80}))
    assert await flood.active_flood_warnings(51.5, -0.14, memory_cache) == 50


async def test_warnings_are_cached(ea_floods, memory_cache) -> None:
    ea_floods.mock(return_value=_recorded("floods_mixed"))
    await flood.active_flood_warnings(51.5, -0.14, memory_cache)
    await flood.active_flood_warnings(51.5, -0.14, memory_cache)
    assert ea_floods.call_count == 1


@pytest.mark.parametrize(
    "failure",
    [
        httpx.ConnectError("offline"),
        httpx.ConnectTimeout("timed out"),
        httpx.Response(503),  # seen live on 2026-10-27
        httpx.Response(200, text="not json"),
    ],
)
async def test_offline_degrades_to_zero(ea_floods, memory_cache, failure) -> None:
    if isinstance(failure, Exception):
        ea_floods.mock(side_effect=failure)
    else:
        ea_floods.mock(return_value=failure)
    assert await flood.active_flood_warnings(51.5, -0.14, memory_cache) == 0
    assert memory_cache.rows == {}  # a failure is not cached
