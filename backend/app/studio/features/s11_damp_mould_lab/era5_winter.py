"""Last winter's hourly temperature and relative humidity, from Open-Meteo's ERA5 archive
(docs/studio/N_20_function.md §S11). Cached forever: past weather never changes."""

import math
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.studio.common.cache import Cache, studio_key
from app.studio.common.http import get_json
from app.studio.features.s11_damp_mould_lab.config import CACHE_DAYS

ERA5_URL = "https://archive-api.open-meteo.com/v1/archive"
SOURCE = "Open-Meteo ERA5"


@dataclass
class HourlyWeather:
    at: datetime
    temp_c: float
    rh: float  # 0-1


def last_winter_window(today: date) -> tuple[date, date, str]:
    """1 Nov - 31 Mar most recently completed; label like "2025-26"."""
    if today.month >= 4:
        start_year = today.year - 1
    else:
        start_year = today.year - 2
    start = date(start_year, 11, 1)
    end = date(start_year + 1, 3, 31)
    label = f"{start_year}-{str(start_year + 1)[-2:]}"
    return start, end, label


async def fetch_winter(
    lat: float, lon: float, start: date, end: date, cache: Cache
) -> list[HourlyWeather]:
    key = studio_key(
        "s11", f"{round(lat, 1)}", f"{round(lon, 1)}", start.isoformat(), end.isoformat()
    )
    hit = await cache.get(key)
    if hit is not None:
        return [HourlyWeather(datetime.fromisoformat(r[0]), r[1], r[2]) for r in hit["rows"]]

    body = await get_json(
        ERA5_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "hourly": "temperature_2m,relative_humidity_2m",
            "timezone": "Europe/London",
        },
        source=SOURCE,
    )
    hourly = body.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    rhs = hourly.get("relative_humidity_2m") or []
    rows = list(zip(times, temps, rhs, strict=False))
    await cache.put(key, "era5", {"rows": rows}, timedelta(days=CACHE_DAYS))
    return [HourlyWeather(datetime.fromisoformat(t), temp, rh / 100) for t, temp, rh in rows]


def synthetic_winter(lat: float, start: date, end: date) -> list[HourlyWeather]:
    """A deterministic stand-in for a winter's hourly weather, used only when ERA5 is
    unreachable: a seasonal sine curve for temperature with damp, high-RH UK winter air."""
    rng = random.Random(round(lat * 10) + start.year)
    hours = int((end - start).total_seconds() // 86400) * 24
    rows = []
    for h in range(hours):
        at = datetime.combine(start, datetime.min.time()) + timedelta(hours=h)
        day_of_winter = h / 24
        seasonal = math.cos(math.pi * (day_of_winter / 151 - 0.5)) if day_of_winter <= 151 else 0
        diurnal = math.sin(math.pi * (at.hour - 6) / 12)
        temp = 6.0 - 4.0 * seasonal + 2.5 * diurnal + rng.uniform(-1.5, 1.5)
        rh = min(1.0, max(0.55, 0.85 - 0.1 * diurnal + rng.uniform(-0.05, 0.05)))
        rows.append((at, round(temp, 1), round(rh, 3)))
    return [HourlyWeather(*r) for r in rows]
