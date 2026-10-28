"""NESO Carbon Intensity API adapter (docs/studio/N_20_function.md §S06). Free, no key,
CC BY 4.0: https://carbon-intensity.github.io/api-definitions/."""

import math
import random
from datetime import datetime, timedelta

from app.studio.common.cache import Cache, studio_key
from app.studio.common.http import get_json
from app.studio.features.s06_grid_carbon_clock.config import (
    CARBON_INTENSITY_BASE,
    FORECAST_CACHE_MINUTES,
)

SOURCE = "NESO Carbon Intensity API"


def outcode_from_postcode(postcode: str) -> str:
    """ "SW1A 1AA" -> "SW1A" (CONTRACT-normalised postcodes always have exactly one space)."""
    return postcode.split(" ")[0]


async def current_mix(outcode: str, cache: Cache) -> dict:
    key = studio_key("s06", "current", outcode)
    hit = await cache.get(key)
    if hit is not None:
        return hit
    body = await get_json(f"{CARBON_INTENSITY_BASE}/regional/postcode/{outcode}", source=SOURCE)
    region = body["data"][0]
    result = {"region_name": region["shortname"], "periods": region["data"]}
    await cache.put(key, "carbon_intensity", result, timedelta(minutes=FORECAST_CACHE_MINUTES))
    return result


def _index_for(intensity: int) -> str:
    if intensity < 50:
        return "very low"
    if intensity < 100:
        return "low"
    if intensity < 200:
        return "moderate"
    if intensity < 300:
        return "high"
    return "very high"


def synthetic_periods(outcode: str, from_at: datetime, half_hours: int) -> list[dict]:
    """A deterministic day/night carbon-intensity curve, used only when the live API is
    unreachable so the clock still works offline (fallback_used: true)."""
    rng = random.Random(sum(ord(c) for c in outcode))
    periods = []
    for i in range(half_hours):
        start = from_at + timedelta(minutes=30 * i)
        hour = start.hour + start.minute / 60
        base = 180 - 90 * math.sin(math.pi * (hour - 3) / 12) if 3 <= hour < 15 else 180 + 40
        intensity = max(20, round(base + rng.uniform(-15, 15)))
        periods.append(
            {
                "from": start.strftime("%Y-%m-%dT%H:%MZ"),
                "to": (start + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%MZ"),
                "intensity": {"forecast": intensity, "index": _index_for(intensity)},
                "generationmix": [
                    {"fuel": "gas", "perc": 45.0},
                    {"fuel": "wind", "perc": 25.0},
                    {"fuel": "nuclear", "perc": 15.0},
                    {"fuel": "biomass", "perc": 8.0},
                    {"fuel": "imports", "perc": 4.0},
                    {"fuel": "solar", "perc": 2.0},
                    {"fuel": "hydro", "perc": 0.6},
                    {"fuel": "coal", "perc": 0.3},
                    {"fuel": "other", "perc": 0.1},
                ],
            }
        )
    return periods


async def forecast_48h(outcode: str, from_iso: str, cache: Cache) -> dict:
    key = studio_key("s06", "forecast", outcode, from_iso[:16])
    hit = await cache.get(key)
    if hit is not None:
        return hit
    body = await get_json(
        f"{CARBON_INTENSITY_BASE}/regional/intensity/{from_iso}/fw48h/postcode/{outcode}",
        source=SOURCE,
    )
    region = body["data"]
    result = {"region_name": region["shortname"], "periods": region["data"]}
    await cache.put(key, "carbon_intensity", result, timedelta(minutes=FORECAST_CACHE_MINUTES))
    return result
