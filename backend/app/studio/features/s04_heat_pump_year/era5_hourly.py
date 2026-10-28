"""Hourly outdoor temperature for the last full calendar year, from Open-Meteo's ERA5 archive
(docs/studio/N_20_function.md §S04). Cached a year by rounded lat/lon + year, since past
weather never changes."""

import math
import random
from datetime import date, datetime, timedelta

from app.studio.common.cache import Cache, studio_key
from app.studio.common.http import get_json

ERA5_URL = "https://archive-api.open-meteo.com/v1/archive"
SOURCE = "Open-Meteo ERA5"
SYNTHETIC_SEED = 20261028


def last_full_year() -> int:
    return date.today().year - 1


async def hourly_temps(
    lat: float, lon: float, year: int, cache: Cache
) -> list[tuple[datetime, float]]:
    key = studio_key("s04", f"{round(lat, 1)}", f"{round(lon, 1)}", str(year))
    hit = await cache.get(key)
    if hit is not None:
        return [(datetime.fromisoformat(t), v) for t, v in hit["hourly"]]

    body = await get_json(
        ERA5_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": f"{year}-01-01",
            "end_date": f"{year}-12-31",
            "hourly": "temperature_2m",
            "timezone": "Europe/London",
        },
        source=SOURCE,
    )
    hourly = body.get("hourly") or {}
    times, temps = hourly.get("time") or [], hourly.get("temperature_2m") or []
    result = [
        (datetime.fromisoformat(t), v) for t, v in zip(times, temps, strict=False) if v is not None
    ]
    await cache.put(
        key,
        "era5",
        {"hourly": [(t.isoformat(), v) for t, v in result]},
        timedelta(days=365),
    )
    return result


def synthetic_hourly_temps(lat: float, year: int) -> list[tuple[datetime, float]]:
    """A deterministic, seasonally-shaped stand-in used only when ERA5 is unreachable, so the
    feature still works offline (fallback_used=True)."""
    rng = random.Random(SYNTHETIC_SEED + round(lat * 10))
    start = datetime(year, 1, 1)
    hours_in_year = 366 * 24 if year % 4 == 0 else 365 * 24
    out = []
    for h in range(hours_in_year):
        at = start + timedelta(hours=h)
        day_of_year = h / 24
        seasonal = 9.0 - 7.0 * math.cos(2 * math.pi * day_of_year / 365)
        diurnal = 3.0 * math.sin(2 * math.pi * (at.hour - 4) / 24)
        out.append((at, round(seasonal + diurnal + rng.uniform(-1.5, 1.5), 1)))
    return out
