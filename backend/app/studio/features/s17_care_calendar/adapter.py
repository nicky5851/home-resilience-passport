"""Open-Meteo Historical Weather fetch, with a seeded synthetic fallback (§S17 Data sources)."""

import hashlib
import random
from datetime import date, timedelta

from app.studio.common.cache import Cache, studio_key
from app.studio.common.http import get_json
from app.studio.features.s17_care_calendar.climatology import ClimateDay
from app.studio.features.s17_care_calendar.config import (
    ARCHIVE_END,
    ARCHIVE_SOURCE,
    ARCHIVE_START,
    ARCHIVE_URL,
    CACHE_DAYS,
)


async def fetch_climatology(lat: float, lon: float, cache: Cache) -> list[ClimateDay]:
    key = studio_key("s17", "climate", f"{round(lat, 2)}", f"{round(lon, 2)}")
    hit = await cache.get(key)
    if hit is not None:
        return [
            ClimateDay(
                at=date.fromisoformat(row["at"]),
                t_min_c=row["t_min_c"],
                rain_mm=row["rain_mm"],
                gust_kmh=row["gust_kmh"],
            )
            for row in hit["days"]
        ]

    body = await get_json(
        ARCHIVE_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": ARCHIVE_START,
            "end_date": ARCHIVE_END,
            "daily": "temperature_2m_min,precipitation_sum,wind_gusts_10m_max",
            "timezone": "Europe/London",
        },
        source=ARCHIVE_SOURCE,
    )
    daily = body.get("daily", {})
    dates = daily.get("time", [])
    t_mins = daily.get("temperature_2m_min", [])
    rains = daily.get("precipitation_sum", [])
    gusts = daily.get("wind_gusts_10m_max", [])

    days = [
        ClimateDay(
            at=date.fromisoformat(d),
            t_min_c=t_mins[i] if i < len(t_mins) else None,
            rain_mm=rains[i] if i < len(rains) else None,
            gust_kmh=gusts[i] if i < len(gusts) else None,
        )
        for i, d in enumerate(dates)
    ]

    await cache.put(
        key,
        ARCHIVE_SOURCE,
        {
            "days": [
                {
                    "at": day.at.isoformat(),
                    "t_min_c": day.t_min_c,
                    "rain_mm": day.rain_mm,
                    "gust_kmh": day.gust_kmh,
                }
                for day in days
            ]
        },
        timedelta(days=CACHE_DAYS),
    )
    return days


def synthetic_climatology(ref: str) -> list[ClimateDay]:
    """Deterministic 30-year series shaped like a mild, damp, moderately windy UK climate, with
    a clear frost season each winter so climatology maths always has something to compute."""
    seed = int(hashlib.sha256(ref.encode()).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)
    days: list[ClimateDay] = []
    start = date(1991, 1, 1)
    end = date(2020, 12, 31)
    at = start
    while at <= end:
        in_winter = at.month in (11, 12, 1, 2)
        t_min = rng.uniform(-4, 4) if in_winter else rng.uniform(4, 16)
        days.append(
            ClimateDay(
                at=at,
                t_min_c=round(t_min, 1),
                rain_mm=round(max(0.0, rng.gauss(2.5, 4)), 1),
                gust_kmh=round(rng.uniform(15, 50), 1),
            )
        )
        at += timedelta(days=1)
    return days
