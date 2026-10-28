"""EA Recorded Flood Outlines adapter, OGC API - Features (docs/studio/N_20_function.md §S08;
live endpoint read directly on 2026-10-28, see config.py's docstring)."""

import math
from datetime import timedelta

from app.studio.common.cache import Cache, studio_key
from app.studio.common.geo import Point
from app.studio.common.http import get_json
from app.studio.features.s08_flood_memory.config import CACHE_DAYS, EA_BASE, EA_COLLECTION, EA_ITEMS_LIMIT

SOURCE = "EA Recorded Flood Outlines"


def _bbox_from_radius(center: Point, radius_m: float) -> tuple[float, float, float, float]:
    lat, lon = center
    dlat = radius_m / 111_320
    dlon = radius_m / (111_320 * math.cos(math.radians(lat)) or 1)
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)


async def fetch_outlines(center: Point, radius_m: float, cache: Cache) -> list[dict]:
    """Raw GeoJSON features within the bbox, cached 30 days."""
    min_lon, min_lat, max_lon, max_lat = _bbox_from_radius(center, radius_m)
    key = studio_key(
        "s08", f"{round(center[0], 3)}", f"{round(center[1], 3)}", str(round(radius_m))
    )
    hit = await cache.get(key)
    if hit is not None:
        return hit["features"]

    body = await get_json(
        f"{EA_BASE}/collections/{EA_COLLECTION}/items",
        params={
            "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "limit": EA_ITEMS_LIMIT,
        },
        source=SOURCE,
    )
    features = body.get("features") or []
    await cache.put(key, "ea_flood", {"features": features}, timedelta(days=CACHE_DAYS))
    return features
