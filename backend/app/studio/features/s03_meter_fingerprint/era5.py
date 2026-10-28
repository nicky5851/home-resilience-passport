"""Daily mean temperature for the meter-reading period, from Open-Meteo's ERA5 archive
(docs/studio/N_20_function.md §S03; https://open-meteo.com/en/docs/historical-weather-api,
CC BY 4.0). Cached 365 days by lat/lon (rounded) + date range."""

from datetime import date, timedelta

from app.studio.common.cache import Cache, studio_key
from app.studio.common.http import get_json

ERA5_URL = "https://archive-api.open-meteo.com/v1/archive"
SOURCE = "Open-Meteo ERA5"
CACHE_TTL_DAYS = 365


async def daily_mean_temps(
    lat: float, lon: float, start: date, end: date, cache: Cache
) -> dict[date, float]:
    key = studio_key(
        "s03", f"{round(lat, 1)}", f"{round(lon, 1)}", start.isoformat(), end.isoformat()
    )
    hit = await cache.get(key)
    if hit is not None:
        return {date.fromisoformat(d): t for d, t in hit["temps"].items()}

    body = await get_json(
        ERA5_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": "temperature_2m_mean",
            "timezone": "Europe/London",
        },
        source=SOURCE,
    )
    daily = body.get("daily") or {}
    dates, temps = daily.get("time") or [], daily.get("temperature_2m_mean") or []
    result = {date.fromisoformat(d): t for d, t in zip(dates, temps, strict=False) if t is not None}
    await cache.put(
        key,
        "era5",
        {"temps": {d.isoformat(): t for d, t in result.items()}},
        timedelta(days=CACHE_TTL_DAYS),
    )
    return result
