"""Open-Meteo Air Quality + Forecast adapters (docs/studio/N_20_function.md §S12), each with a
seeded synthetic fallback."""

import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.studio.common.cache import Cache, studio_key
from app.studio.common.http import get_json
from app.studio.features.s12_breathe_easy.config import (
    AIR_QUALITY_URL,
    AQ_SOURCE,
    CACHE_HOURS,
    FORECAST_DAYS,
    FORECAST_URL,
    WEATHER_SOURCE,
)


@dataclass
class AirQualityHour:
    at: datetime
    pm2_5: float | None
    pm10: float | None
    no2: float | None
    o3: float | None
    grass_pollen: float | None
    birch_pollen: float | None
    alder_pollen: float | None


@dataclass
class WeatherHour:
    at: datetime
    temp_c: float | None
    rh_pct: float | None
    dew_point_c: float | None
    wind_kmh: float | None


async def fetch_air_quality(lat: float, lon: float, cache: Cache) -> list[AirQualityHour]:
    key = studio_key("s12", "aq", f"{round(lat, 2)}", f"{round(lon, 2)}")
    hit = await cache.get(key)
    if hit is not None:
        return [AirQualityHour(datetime.fromisoformat(r[0]), *r[1:]) for r in hit["rows"]]

    body = await get_json(
        AIR_QUALITY_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": "pm2_5,pm10,nitrogen_dioxide,ozone,grass_pollen,birch_pollen,alder_pollen",
            "forecast_days": FORECAST_DAYS,
            "timezone": "Europe/London",
        },
        source=AQ_SOURCE,
    )
    hourly = body.get("hourly") or {}
    times = hourly.get("time") or []
    aq_fields = (
        "pm2_5", "pm10", "nitrogen_dioxide", "ozone",
        "grass_pollen", "birch_pollen", "alder_pollen",
    )  # fmt: skip
    cols = [hourly.get(k) or [None] * len(times) for k in aq_fields]
    rows = list(zip(times, *cols, strict=False))
    await cache.put(key, "open_meteo_aq", {"rows": rows}, timedelta(hours=CACHE_HOURS))
    return [AirQualityHour(datetime.fromisoformat(r[0]), *r[1:]) for r in rows]


async def fetch_weather(lat: float, lon: float, cache: Cache) -> list[WeatherHour]:
    key = studio_key("s12", "wx", f"{round(lat, 2)}", f"{round(lon, 2)}")
    hit = await cache.get(key)
    if hit is not None:
        return [WeatherHour(datetime.fromisoformat(r[0]), *r[1:]) for r in hit["rows"]]

    body = await get_json(
        FORECAST_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relative_humidity_2m,dew_point_2m,wind_speed_10m",
            "forecast_days": FORECAST_DAYS,
            "timezone": "Europe/London",
        },
        source=WEATHER_SOURCE,
    )
    hourly = body.get("hourly") or {}
    times = hourly.get("time") or []
    cols = [
        hourly.get(k) or [None] * len(times)
        for k in ("temperature_2m", "relative_humidity_2m", "dew_point_2m", "wind_speed_10m")
    ]
    rows = list(zip(times, *cols, strict=False))
    await cache.put(key, "open_meteo_wx", {"rows": rows}, timedelta(hours=CACHE_HOURS))
    return [WeatherHour(datetime.fromisoformat(r[0]), *r[1:]) for r in rows]


def synthetic_air_quality(lat: float, now: datetime) -> list[AirQualityHour]:
    rng = random.Random(round(lat * 10) + now.toordinal())
    start = now.replace(minute=0, second=0, microsecond=0)
    out = []
    for h in range(FORECAST_DAYS * 24):
        at = start + timedelta(hours=h)
        rush = 1.3 if at.hour in (7, 8, 17, 18) else 1.0
        out.append(
            AirQualityHour(
                at=at,
                pm2_5=round(8 + rng.uniform(0, 6) * rush, 1),
                pm10=round(14 + rng.uniform(0, 8) * rush, 1),
                no2=round(20 + rng.uniform(0, 15) * rush, 1),
                o3=round(40 + 20 * math.sin(math.pi * at.hour / 24), 1),
                grass_pollen=None,
                birch_pollen=None,
                alder_pollen=None,
            )
        )
    return out


def synthetic_weather(lat: float, now: datetime) -> list[WeatherHour]:
    rng = random.Random(round(lat * 10) + now.toordinal() + 1)
    start = now.replace(minute=0, second=0, microsecond=0)
    out = []
    for h in range(FORECAST_DAYS * 24):
        at = start + timedelta(hours=h)
        diurnal = math.sin(math.pi * (at.hour - 6) / 12)
        temp = 12.0 + 5.0 * diurnal + rng.uniform(-1, 1)
        rh = min(100.0, max(40.0, 70 - 15 * diurnal + rng.uniform(-5, 5)))
        dew = temp - (100 - rh) / 5
        out.append(
            WeatherHour(
                at=at,
                temp_c=round(temp, 1),
                rh_pct=round(rh, 1),
                dew_point_c=round(dew, 1),
                wind_kmh=round(10 + rng.uniform(0, 10), 1),
            )
        )
    return out
