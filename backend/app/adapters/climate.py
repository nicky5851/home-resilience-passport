"""Today vs 2050 heat, heavy rain and wind from the Open-Meteo Climate API (spec §5, step N8).

Free for non-commercial use, no key; credit "Open-Meteo, CMIP6". One model (`EC_Earth3P_HR`),
two requests in parallel: baseline 1991–2020 and future 2041–2050. Statistics exactly as
CONTRACT §2 defines them, averaged over the years that have data (the model has no 2050, so the
future window is 2041–2049 in practice). Each period is cached for 90 days by lat/lon rounded to
0.1°. Fallback per period: the home's row of the regional defaults table (`climate_defaults.py`),
found by region name (from postcodes.io), else by the nearest reference point.
"""

import asyncio
import logging
from collections import defaultdict
from math import cos, radians
from typing import Any

import httpx
from pydantic import BaseModel

from app.adapters.cache import Cache
from app.adapters.climate_defaults import REGIONAL_DEFAULTS, RegionDefault
from app.adapters.http import UpstreamUnavailable, new_client
from app.config import (
    CLIMATE_BASELINE_YEARS,
    CLIMATE_CACHE_ROUND_DEGREES,
    CLIMATE_CACHE_TTL,
    CLIMATE_FUTURE_YEARS,
    CLIMATE_MODEL,
    HEAVY_RAIN_THRESHOLD_MM,
    HOT_DAY_THRESHOLD_C,
)
from app.schemas import HAZARD_INPUT_RANGES

log = logging.getLogger(__name__)

SOURCE = "Open-Meteo"
CLIMATE_URL = "https://climate-api.open-meteo.com/v1/climate"
DAILY = ("temperature_2m_max", "precipitation_sum", "wind_speed_10m_max")
MIN_DAYS_PER_YEAR = 360  # a year counts only if (almost) every day has data


class PeriodStats(BaseModel):
    hot_days: float
    heavy_rain_days: float
    max_wind_kmh: float


class ClimateStats(BaseModel):
    """The six climate fields of `HazardInputs` (CONTRACT §2)."""

    hot_days_baseline: float
    hot_days_2050: float
    heavy_rain_days_baseline: float
    heavy_rain_days_2050: float
    max_wind_baseline_kmh: float
    max_wind_2050_kmh: float
    from_defaults: bool = False  # True if either period used the regional defaults


async def climate_stats(
    lat: float, lon: float, cache: Cache, region: str | None = None
) -> ClimateStats:
    """Never raises: a period the API cannot answer comes from the regional defaults.

    `region` is `PostcodeInfo.region` ("South West", "Wales"); without it the nearest
    reference point is used, which can pick the wrong region near a border.
    """
    baseline, future = await asyncio.gather(
        _period(lat, lon, CLIMATE_BASELINE_YEARS, cache),
        _period(lat, lon, CLIMATE_FUTURE_YEARS, cache),
    )
    fallback = baseline is None or future is None
    region = default_region(lat, lon, region) if fallback else None
    if region is not None:
        log.warning("Open-Meteo unavailable; using climate defaults for %s", region.name)
    baseline = baseline or region.baseline
    future = future or region.future
    return ClimateStats(
        hot_days_baseline=baseline.hot_days,
        hot_days_2050=future.hot_days,
        heavy_rain_days_baseline=baseline.heavy_rain_days,
        heavy_rain_days_2050=future.heavy_rain_days,
        max_wind_baseline_kmh=baseline.max_wind_kmh,
        max_wind_2050_kmh=future.max_wind_kmh,
        from_defaults=region is not None,
    )


async def _period(
    lat: float, lon: float, years: tuple[int, int], cache: Cache
) -> PeriodStats | None:
    key = period_key(lat, lon, years)
    if (hit := await cache.get(key)) is not None:
        return PeriodStats.model_validate(hit)
    lat_r = round(lat, CLIMATE_CACHE_ROUND_DEGREES)
    lon_r = round(lon, CLIMATE_CACHE_ROUND_DEGREES)
    try:
        stats = await fetch_period(lat_r, lon_r, years)
    except UpstreamUnavailable:
        return None
    await cache.put(key, "open-meteo", stats.model_dump(), CLIMATE_CACHE_TTL)
    return stats


def period_key(lat: float, lon: float, years: tuple[int, int]) -> str:
    lat_r = round(lat, CLIMATE_CACHE_ROUND_DEGREES)
    lon_r = round(lon, CLIMATE_CACHE_ROUND_DEGREES)
    return f"open-meteo:{CLIMATE_MODEL}:{lat_r:.1f},{lon_r:.1f}:{years[0]}-{years[1]}"


async def fetch_period(lat: float, lon: float, years: tuple[int, int]) -> PeriodStats:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": f"{years[0]}-01-01",
        "end_date": f"{years[1]}-12-31",
        "models": CLIMATE_MODEL,
        "daily": ",".join(DAILY),
    }
    try:
        async with new_client() as client:
            res = await client.get(CLIMATE_URL, params=params)
    except httpx.HTTPError as e:
        raise UpstreamUnavailable(SOURCE) from e
    if res.status_code != 200:
        raise UpstreamUnavailable(SOURCE)
    try:
        return period_stats(res.json()["daily"], future=years == CLIMATE_FUTURE_YEARS)
    except (ValueError, KeyError, TypeError) as e:
        raise UpstreamUnavailable(SOURCE) from e


def period_stats(daily: dict[str, Any], future: bool = False) -> PeriodStats:
    """CONTRACT §2 statistics from Open-Meteo's `daily` block. Raises ValueError if unusable."""
    by_year: dict[str, list[tuple[float, float, float]]] = defaultdict(list)
    for day, tmax, rain, wind in zip(daily["time"], *(daily[k] for k in DAILY), strict=True):
        if None not in (tmax, rain, wind):
            by_year[day[:4]].append((tmax, rain, wind))
    years = [days for days in by_year.values() if len(days) >= MIN_DAYS_PER_YEAR]
    if not years:
        raise ValueError("no complete year")
    n = len(years)
    stats = PeriodStats(
        hot_days=round(sum(t >= HOT_DAY_THRESHOLD_C for d in years for t, _, _ in d) / n, 1),
        heavy_rain_days=round(
            sum(r >= HEAVY_RAIN_THRESHOLD_MM for d in years for _, r, _ in d) / n, 1
        ),
        max_wind_kmh=round(sum(max(w for _, _, w in d) for d in years) / n, 1),
    )
    suffix = "2050" if future else "baseline"
    for field, value in (
        (f"hot_days_{suffix}", stats.hot_days),
        (f"heavy_rain_days_{suffix}", stats.heavy_rain_days),
        (f"max_wind_{suffix}_kmh", stats.max_wind_kmh),
    ):
        lo, hi = HAZARD_INPUT_RANGES[field]
        if not lo <= value <= hi:
            raise ValueError(f"{field}={value} outside CONTRACT §2 range")
    return stats


def default_region(lat: float, lon: float, name: str | None = None) -> RegionDefault:
    by_name = next((r for r in REGIONAL_DEFAULTS if name and r.name.lower() == name.lower()), None)
    return by_name or nearest_region(lat, lon)


def nearest_region(lat: float, lon: float) -> RegionDefault:
    """The defaults row whose reference point is closest (flat-earth distance is enough here)."""
    k = cos(radians(lat))
    return min(REGIONAL_DEFAULTS, key=lambda r: (r.lat - lat) ** 2 + ((r.lon - lon) * k) ** 2)
