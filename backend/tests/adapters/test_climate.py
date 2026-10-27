"""N8: climate projections via Open-Meteo, offline.

recorded/climate/ holds Open-Meteo Climate API responses for London (51.5, -0.1), model
EC_Earth3P_HR, recorded on 2026-10-27. The 2041–2050 response has no data for 2050.
"""

import json

import httpx
import pytest

from app.adapters import climate
from app.adapters.climate_defaults import REGIONAL_DEFAULTS
from app.config import CLIMATE_BASELINE_YEARS, CLIMATE_FUTURE_YEARS, HOT_DAY_THRESHOLD_C
from app.schemas import HAZARD_INPUT_RANGES
from tests.conftest import RECORDED_DIR

pytestmark = pytest.mark.anyio
CLIMATE_DIR = RECORDED_DIR / "climate"
LONDON = (51.5, -0.1)


def _daily(name: str) -> dict:
    return json.loads((CLIMATE_DIR / f"{name}.json").read_text())["daily"]


def _recorded(request: httpx.Request) -> httpx.Response:
    start = request.url.params["start_date"][:4]
    name = "london_1991_2020" if start == "1991" else "london_2041_2050"
    return httpx.Response(200, json=json.loads((CLIMATE_DIR / f"{name}.json").read_text()))


@pytest.fixture
def open_meteo(mock_http):
    return mock_http.get(url__startswith=climate.CLIMATE_URL).mock(side_effect=_recorded)


# --- Statistics (CONTRACT §2) ---------------------------------------------------------------


def test_london_statistics() -> None:
    assert climate.period_stats(_daily("london_1991_2020")).model_dump() == {
        "hot_days": 2.6,
        "heavy_rain_days": 1.4,
        "max_wind_kmh": 49.7,
    }
    assert climate.period_stats(_daily("london_2041_2050"), future=True).model_dump() == {
        "hot_days": 8.6,
        "heavy_rain_days": 2.2,
        "max_wind_kmh": 50.9,
    }


def _synthetic(years: dict[int, list[tuple]]) -> dict:
    daily = {"time": [], **{k: [] for k in climate.DAILY}}
    for year, days in years.items():
        for i, (t, r, w) in enumerate(days):
            daily["time"].append(f"{year}-{1 + i // 31:02d}-{1 + i % 31:02d}")
            for k, v in zip(climate.DAILY, (t, r, w), strict=True):
                daily[k].append(v)
    return daily


def test_statistics_follow_the_contract_definitions() -> None:
    """Hot day: max ≥ 28 °C; heavy rain: ≥ 20 mm; wind: mean of each year's highest day."""
    cool = [(15.0, 1.0, 30.0)] * 365
    y1 = cool[:]
    y1[0] = (HOT_DAY_THRESHOLD_C, 20.0, 80.0)  # exactly on both thresholds
    y1[1] = (HOT_DAY_THRESHOLD_C - 0.1, 19.9, 30.0)  # just under
    y2 = cool[:]
    y2[5] = (31.0, 0.0, 60.0)
    y2[6] = (29.0, 25.0, 40.0)
    stats = climate.period_stats(_synthetic({2001: y1, 2002: y2}))
    assert (stats.hot_days, stats.heavy_rain_days, stats.max_wind_kmh) == (1.5, 1.0, 70.0)


def test_years_without_data_are_left_out() -> None:
    """EC_Earth3P_HR has no 2050: average over the years that have data, not over all ten."""
    year = [(15.0, 0.0, 40.0)] * 362 + [(30.0, 0.0, 40.0)] * 3  # 3 hot days
    empty = [(None, None, None)] * 365
    stats = climate.period_stats(_synthetic({2048: year, 2049: year, 2050: empty}), future=True)
    assert stats.hot_days == 3.0  # not 2.0 (6 hot days over 3 years)


def test_out_of_range_period_is_refused() -> None:
    hot = [(30.0, 0.0, 40.0)] * 365
    with pytest.raises(ValueError, match="outside CONTRACT"):
        climate.period_stats(_synthetic({2048: hot, 2049: hot}), future=True)


def test_partial_and_missing_years_do_not_count() -> None:
    full = [(15.0, 0.0, 40.0)] * 364 + [(30.0, 0.0, 40.0)]
    partial = [(30.0, 0.0, 40.0)] * 100
    empty = [(None, None, None)] * 365
    stats = climate.period_stats(_synthetic({2041: full, 2042: full, 2043: partial, 2050: empty}))
    assert stats.hot_days == 1.0  # 2 complete years, one hot day each


# --- Adapter ----------------------------------------------------------------------------------


async def test_london_has_more_hot_days_in_2050(open_meteo, memory_cache) -> None:
    stats = await climate.climate_stats(*LONDON, memory_cache)
    assert stats.hot_days_2050 > stats.hot_days_baseline
    assert stats.model_dump() == {
        "hot_days_baseline": 2.6,
        "hot_days_2050": 8.6,
        "heavy_rain_days_baseline": 1.4,
        "heavy_rain_days_2050": 2.2,
        "max_wind_baseline_kmh": 49.7,
        "max_wind_2050_kmh": 50.9,
        "from_defaults": False,
    }


async def test_two_requests_with_the_contract_windows(open_meteo, memory_cache) -> None:
    await climate.climate_stats(51.5072, -0.1276, memory_cache)
    assert open_meteo.call_count == 2
    windows = set()
    for call in open_meteo.calls:
        q = call.request.url.params
        assert (q["latitude"], q["longitude"]) == ("51.5", "-0.1")  # rounded to 0.1°
        assert q["models"] == "EC_Earth3P_HR"
        assert q["daily"] == "temperature_2m_max,precipitation_sum,wind_speed_10m_max"
        windows.add((q["start_date"], q["end_date"]))
    (b0, b1), (f0, f1) = CLIMATE_BASELINE_YEARS, CLIMATE_FUTURE_YEARS
    assert windows == {(f"{b0}-01-01", f"{b1}-12-31"), (f"{f0}-01-01", f"{f1}-12-31")}


async def test_second_call_hits_the_cache(open_meteo, memory_cache) -> None:
    first = await climate.climate_stats(*LONDON, memory_cache)
    second = await climate.climate_stats(51.52, -0.08, memory_cache)  # same 0.1° cell
    assert first == second
    assert open_meteo.call_count == 2


@pytest.mark.parametrize(
    "failure",
    [
        httpx.Response(429, json={"reason": "Minutely API request limit exceeded.", "error": True}),
        httpx.ConnectError("offline"),
        httpx.ConnectTimeout("timed out"),
        httpx.Response(200, json={"error": True}),
    ],
)
async def test_failure_uses_regional_defaults(open_meteo, memory_cache, failure) -> None:
    if isinstance(failure, Exception):
        open_meteo.side_effect = failure
    else:
        open_meteo.side_effect = None
        open_meteo.return_value = failure
    stats = await climate.climate_stats(53.96, -1.08, memory_cache)  # York
    leeds = next(r for r in REGIONAL_DEFAULTS if r.name == "Yorkshire and The Humber")
    assert stats.from_defaults
    assert (stats.hot_days_baseline, stats.hot_days_2050) == (
        leeds.baseline.hot_days,
        leeds.future.hot_days,
    )
    assert memory_cache.rows == {}  # defaults are never cached


async def test_one_period_failing_keeps_the_other(open_meteo, memory_cache) -> None:
    def future_fails(request: httpx.Request) -> httpx.Response:
        if request.url.params["start_date"].startswith("2041"):
            return httpx.Response(429)
        return _recorded(request)

    open_meteo.side_effect = future_fails
    stats = await climate.climate_stats(*LONDON, memory_cache)
    london = next(r for r in REGIONAL_DEFAULTS if r.name == "London")
    assert stats.from_defaults
    assert stats.hot_days_baseline == 2.6  # real
    assert stats.hot_days_2050 == london.future.hot_days  # default
    assert len(memory_cache.rows) == 1  # only the real period is cached


# --- Regional defaults -------------------------------------------------------------------------


def test_defaults_cover_every_english_region_and_wales() -> None:
    assert {r.name for r in REGIONAL_DEFAULTS} == {
        "North East", "North West", "Yorkshire and The Humber", "East Midlands",
        "West Midlands", "East of England", "London", "South East", "South West", "Wales",
    }  # fmt: skip


def test_defaults_are_inside_the_contract_ranges() -> None:
    for r in REGIONAL_DEFAULTS:
        for suffix, period in (("baseline", r.baseline), ("2050", r.future)):
            for field, value in (
                (f"hot_days_{suffix}", period.hot_days),
                (f"heavy_rain_days_{suffix}", period.heavy_rain_days),
                (f"max_wind_{suffix}_kmh", period.max_wind_kmh),
            ):
                lo, hi = HAZARD_INPUT_RANGES[field]
                assert lo <= value <= hi, f"{r.name}: {field}={value}"


@pytest.mark.parametrize(
    ("lat", "lon", "region"),
    [
        (53.96, -1.08, "Yorkshire and The Humber"),  # York
        (50.12, -5.54, "South West"),  # Penzance
        (51.48, -3.18, "Wales"),  # Cardiff
        (51.51, -0.07, "London"),  # Whitechapel
    ],
)
def test_nearest_region(lat, lon, region) -> None:
    assert climate.nearest_region(lat, lon).name == region


def test_region_name_beats_nearest_point() -> None:
    """GL54 (rural-cottage demo) is South West, but Birmingham is the nearest reference point."""
    assert climate.nearest_region(51.90, -1.75).name == "West Midlands"
    assert climate.default_region(51.90, -1.75, "South West").name == "South West"
    assert climate.default_region(51.90, -1.75, "Not a region").name == "West Midlands"


async def test_failure_uses_the_named_region(open_meteo, memory_cache) -> None:
    open_meteo.side_effect = httpx.ConnectError("offline")
    stats = await climate.climate_stats(51.90, -1.75, memory_cache, region="South West")
    exeter = next(r for r in REGIONAL_DEFAULTS if r.name == "South West")
    assert stats.hot_days_2050 == exeter.future.hot_days
