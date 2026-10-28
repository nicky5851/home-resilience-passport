"""Hourly weather for one event window, +/- 1 day, from Open-Meteo's ERA5 archive
(docs/studio/N_20_function.md §S07). Cached forever: past weather never changes."""

import math
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.studio.common.cache import Cache, studio_key
from app.studio.common.http import get_json
from app.studio.features.s07_storm_replay.config import ERA5_CACHE_FOREVER_DAYS, WINDOW_PAD_DAYS

ERA5_URL = "https://archive-api.open-meteo.com/v1/archive"
SOURCE = "Open-Meteo ERA5"


@dataclass
class HourlyWeather:
    at: datetime
    temp_c: float
    gust_kmh: float
    wind_kmh: float
    rain_mm: float


async def fetch_event_window(
    lat: float, lon: float, start: date, end: date, cache: Cache
) -> list[HourlyWeather]:
    padded_start = start - timedelta(days=WINDOW_PAD_DAYS)
    padded_end = end + timedelta(days=WINDOW_PAD_DAYS)
    key = studio_key(
        "s07",
        f"{round(lat, 1)}",
        f"{round(lon, 1)}",
        padded_start.isoformat(),
        padded_end.isoformat(),
    )
    hit = await cache.get(key)
    if hit is not None:
        return [
            HourlyWeather(datetime.fromisoformat(r[0]), r[1], r[2], r[3], r[4]) for r in hit["rows"]
        ]

    body = await get_json(
        ERA5_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": padded_start.isoformat(),
            "end_date": padded_end.isoformat(),
            "hourly": "temperature_2m,wind_gusts_10m,wind_speed_10m,precipitation",
            "timezone": "Europe/London",
        },
        source=SOURCE,
    )
    hourly = body.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    gusts = hourly.get("wind_gusts_10m") or []
    winds = hourly.get("wind_speed_10m") or []
    rains = hourly.get("precipitation") or []
    rows = list(zip(times, temps, gusts, winds, rains, strict=False))
    await cache.put(key, "era5", {"rows": rows}, timedelta(days=ERA5_CACHE_FOREVER_DAYS))
    return [
        HourlyWeather(datetime.fromisoformat(t), temp, gust, wind, rain)
        for t, temp, gust, wind, rain in rows
    ]


def synthetic_event_window(lat: float, start: date, end: date, kind: str) -> list[HourlyWeather]:
    """A deterministic stand-in for one event window, used only when ERA5 is unreachable."""
    rng = random.Random(round(lat * 10) + sum(ord(c) for c in kind))
    padded_start = start - timedelta(days=WINDOW_PAD_DAYS)
    padded_end = end + timedelta(days=WINDOW_PAD_DAYS)
    hours = int((padded_end - padded_start).total_seconds() // 3600) + 24
    rows = []
    for h in range(hours):
        at = datetime.combine(padded_start, datetime.min.time()) + timedelta(hours=h)
        shape = math.sin(math.pi * min(1.0, h / hours)) if hours else 0
        if kind == "wind":
            temp = 8.0
            gust = 60 + shape * 70 + rng.uniform(-5, 5)
            wind = 30 + shape * 40
            rain = shape * 2
        elif kind == "rain":
            temp = 10.0
            gust = 40 + shape * 20
            wind = 25 + shape * 15
            rain = shape * 8 + rng.uniform(0, 2)
        else:
            temp = 20 + shape * 18 + rng.uniform(-1, 1)
            gust, wind, rain = 15, 10, 0.0
        rows.append(
            (
                at,
                round(temp, 1),
                round(max(0, gust), 1),
                round(max(0, wind), 1),
                round(max(0, rain), 1),
            )
        )
    return [HourlyWeather(*r) for r in rows]
