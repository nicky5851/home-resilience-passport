"""NCERM adapter (docs/studio/N_20_function.md §S09; live endpoint details in config.py's
docstring). Geometry coordinates are 3D (lon, lat, z=0) - z is dropped on parsing."""

import math
from datetime import timedelta

from app.studio.common.cache import Cache, studio_key
from app.studio.common.geo import Point, point_in_polygon, point_to_polygon_distance_m
from app.studio.common.http import get_json
from app.studio.features.s09_shoreline_watch.config import CACHE_DAYS, ITEMS_LIMIT, NCERM_BASE

SOURCE = "EA NCERM 2024"


def _bbox_from_radius(center: Point, radius_m: float) -> tuple[float, float, float, float]:
    lat, lon = center
    dlat = radius_m / 111_320
    dlon = radius_m / (111_320 * math.cos(math.radians(lat)) or 1)
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)


async def fetch_collection(collection: str, center: Point, radius_m: float, cache: Cache) -> list[dict]:
    min_lon, min_lat, max_lon, max_lat = _bbox_from_radius(center, radius_m)
    key = studio_key(
        "s09", collection, f"{round(center[0], 3)}", f"{round(center[1], 3)}", str(round(radius_m))
    )
    hit = await cache.get(key)
    if hit is not None:
        return hit["features"]

    body = await get_json(
        f"{NCERM_BASE}/collections/{collection}/items",
        params={"bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}", "limit": ITEMS_LIMIT},
        source=SOURCE,
    )
    features = body.get("features") or []
    await cache.put(key, "ncerm", {"features": features}, timedelta(days=CACHE_DAYS))
    return features


def polygon_rings(geometry: dict) -> list[list[Point]]:
    """(lat, lon) rings, dropping any z coordinate, across a Polygon or MultiPolygon."""
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    polygons = coords if gtype == "MultiPolygon" else [coords]
    rings = []
    for polygon in polygons:
        for ring in polygon:
            rings.append([(c[1], c[0]) for c in ring])
    return rings


def contains_point(geometry: dict, point: Point) -> bool:
    rings = polygon_rings(geometry)
    return any(point_in_polygon(point, ring) for ring in rings)


def distance_to_geometry_m(geometry: dict, point: Point) -> float:
    rings = polygon_rings(geometry)
    if not rings:
        return float("inf")
    return min(point_to_polygon_distance_m(point, ring) for ring in rings)
