"""PVGIS 5.3 PVcalc adapter (docs/studio/N_20_function.md §S05). Free, no key; aspect 0 =
south, 90 = west, -90 = east, matching this feature's `aspect_deg` convention directly."""

import math
from datetime import timedelta

from app.studio.common.cache import Cache, studio_key
from app.studio.common.http import get_json
from app.studio.features.s05_solar_roof_studio.config import (
    PVGIS_CACHE_DAYS,
    PVGIS_LOSS_PERCENT,
    PVGIS_URL,
)

SOURCE = "PVGIS 5.3"


async def pvcalc(
    lat: float, lon: float, kwp: float, pitch_deg: int, aspect_deg: int, cache: Cache
) -> dict:
    """Returns `{"annual_kwh": int, "monthly_kwh": list[int]}` for a 1 kWp system at this
    orientation, so callers can scale linearly - cached 365 days by rounded location + angles."""
    key = studio_key("s05", f"{round(lat, 2)}", f"{round(lon, 2)}", str(pitch_deg), str(aspect_deg))
    hit = await cache.get(key)
    if hit is None:
        body = await get_json(
            PVGIS_URL,
            params={
                "lat": lat,
                "lon": lon,
                "peakpower": 1.0,
                "loss": PVGIS_LOSS_PERCENT,
                "angle": pitch_deg,
                "aspect": aspect_deg,
                "outputformat": "json",
            },
            source=SOURCE,
        )
        monthly_rows = body["outputs"]["monthly"]["fixed"]
        per_kwp = {
            "annual_kwh": sum(row["E_m"] for row in monthly_rows),
            "monthly_kwh": [row["E_m"] for row in monthly_rows],
        }
        await cache.put(key, "pvgis", per_kwp, timedelta(days=PVGIS_CACHE_DAYS))
        hit = per_kwp

    scale = kwp
    return {
        "annual_kwh": round(hit["annual_kwh"] * scale),
        "monthly_kwh": [round(m * scale) for m in hit["monthly_kwh"]],
    }


# UK-typical monthly generation shape per kWp at a south-facing 35 degree roof, used only when
# PVGIS is unreachable so the feature still works offline (fallback_used: true).
_FALLBACK_MONTHLY_PER_KWP = [30, 40, 70, 95, 110, 110, 105, 95, 70, 45, 30, 25]


def synthetic_pvcalc(kwp: float, pitch_deg: int, aspect_deg: int) -> dict:
    pitch_factor = math.cos(math.radians(abs(pitch_deg - 35))) * 0.15 + 0.85
    aspect_factor = math.cos(math.radians(aspect_deg)) * 0.25 + 0.75
    monthly = [round(m * kwp * pitch_factor * aspect_factor) for m in _FALLBACK_MONTHLY_PER_KWP]
    return {"annual_kwh": sum(monthly), "monthly_kwh": monthly}
