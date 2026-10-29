"""Open-Meteo UKV forecast fetch, with a seeded synthetic fallback (§S16 Data sources)."""

import hashlib
import random
from dataclasses import dataclass
from datetime import date, timedelta

from app.studio.common.cache import Cache, studio_key
from app.studio.common.http import get_json
from app.studio.features.s16_week_ahead.config import (
    CACHE_HOURS,
    DAILY_VARS,
    FALLBACK_MODEL,
    FORECAST_DAYS,
    FORECAST_URL,
    PRIMARY_MODEL,
)


@dataclass
class ForecastDay:
    at: date
    t_max_c: float | None
    t_min_c: float | None
    rain_mm: float | None
    gust_kmh: float | None
    uv_index: float | None


async def fetch_week(lat: float, lon: float, cache: Cache) -> list[ForecastDay]:
    key = studio_key("s16", "week", f"{round(lat, 2)}", f"{round(lon, 2)}")
    hit = await cache.get(key)
    if hit is not None:
        return [ForecastDay(at=date.fromisoformat(row.pop("at")), **row) for row in hit["days"]]

    body = await get_json(
        FORECAST_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": DAILY_VARS,
            "models": f"{PRIMARY_MODEL},{FALLBACK_MODEL}",
            "timezone": "Europe/London",
            "forecast_days": FORECAST_DAYS,
        },
        source="open_meteo_ukmo",
    )
    daily = body.get("daily", {})
    dates = daily.get("time", [])

    def field(name: str, i: int) -> float | None:
        primary = daily.get(f"{name}_{PRIMARY_MODEL}", [])
        value = primary[i] if i < len(primary) else None
        if value is not None:
            return value
        fallback = daily.get(f"{name}_{FALLBACK_MODEL}", [])
        return fallback[i] if i < len(fallback) else None

    days = [
        ForecastDay(
            at=date.fromisoformat(d),
            t_max_c=field("temperature_2m_max", i),
            t_min_c=field("temperature_2m_min", i),
            rain_mm=field("precipitation_sum", i),
            gust_kmh=field("wind_gusts_10m_max", i),
            uv_index=field("uv_index_max", i),
        )
        for i, d in enumerate(dates)
    ]

    await cache.put(
        key,
        "open_meteo_ukmo",
        {
            "days": [
                {
                    "at": day.at.isoformat(),
                    "t_max_c": day.t_max_c,
                    "t_min_c": day.t_min_c,
                    "rain_mm": day.rain_mm,
                    "gust_kmh": day.gust_kmh,
                    "uv_index": day.uv_index,
                }
                for day in days
            ]
        },
        timedelta(hours=CACHE_HOURS),
    )
    return days


def synthetic_week(ref: str, today: date) -> list[ForecastDay]:
    seed = int(hashlib.sha256(ref.encode()).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)
    return [
        ForecastDay(
            at=today + timedelta(days=i),
            t_max_c=round(rng.uniform(2, 22), 1),
            t_min_c=round(rng.uniform(-4, 14), 1),
            rain_mm=round(max(0.0, rng.gauss(3, 6)), 1),
            gust_kmh=round(rng.uniform(15, 55), 1),
            uv_index=round(rng.uniform(0, 4), 1),
        )
        for i in range(FORECAST_DAYS)
    ]
